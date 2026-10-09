"""Researcher-side packaging. Keys are never registered or transmitted here."""
from __future__ import annotations

import base64
import re
import secrets

from . import crypto
from .manifest import MAX_CONFIG_BYTES, MAX_SOURCE_BYTES, ManifestError, canonical_json, sha256


class ClientError(ValueError):
    pass


def _text(value, maximum=128):
    if type(value) is not str or not 0 < len(value) <= maximum or any(ord(c) < 32 for c in value):
        raise ClientError('invalid submission metadata')


def _hash(value):
    if type(value) is not str or not re.fullmatch(r'[a-f0-9]{64}', value):
        raise ClientError('invalid submission digest')


def key_fingerprint(public):
    try:
        if type(public) is not str:
            raise ValueError()
        raw = base64.b64decode(public, validate=True)
        if len(raw) != 32 or base64.b64encode(raw).decode('ascii') != public:
            raise ValueError()
        return sha256(raw)
    except (ValueError, TypeError) as exc:
        raise ClientError('invalid public key') from exc


def pack_submission(*, source, config, subject, submission_id, dataset_id,
                    dataset_sha256, engine_sha256, seed, owner_key_id, owner_private,
                    broker_key_id, broker_public, recipient_key_id, recipient_public,
                    issued_at, expires_at):
    """Sign the full encrypted job and bind its authorized result recipient.

    Source and config remain encrypted. Metadata/digests can expose equality
    between submissions and are intentionally visible in this v1 protocol.
    Trust in the broker public key must be established out of band.
    """
    try:
        if type(source) is not str or not 0 < len(source.encode('utf-8')) <= MAX_SOURCE_BYTES:
            raise ClientError('invalid source size')
        if type(config) is not dict or len(canonical_json(config)) > MAX_CONFIG_BYTES:
            raise ClientError('invalid config')
        for text in (subject, dataset_id, owner_key_id, broker_key_id, recipient_key_id):
            _text(text, 1024 if text == subject else 128)
        submission_id = secrets.token_hex(16) if submission_id is None else submission_id
        if type(submission_id) is not str or not re.fullmatch(r'[a-f0-9]{32}', submission_id):
            raise ClientError('invalid submission identifier')
        for digest in (dataset_sha256, engine_sha256):
            _hash(digest)
        if type(seed) is not int or not 0 <= seed < 2**64:
            raise ClientError('invalid seed')
        if any(type(v) is not int or v < 0 for v in (issued_at, expires_at)) or expires_at <= issued_at:
            raise ClientError('invalid validity interval')
        key_fingerprint(broker_public)
        recipient = key_fingerprint(recipient_public)
        header = {'schema': 'straty-submission/1', 'subject': subject,
                  'submission_id': submission_id, 'owner_key_id': owner_key_id,
                  'broker_key_id': broker_key_id, 'recipient_key_id': recipient_key_id,
                  'recipient_fingerprint': recipient, 'dataset_id': dataset_id,
                  'dataset_sha256': dataset_sha256, 'engine_sha256': engine_sha256,
                  'config_sha256': sha256(canonical_json(config)), 'seed': seed,
                  'issued_at': issued_at, 'expires_at': expires_at}
        envelope = crypto.seal({'source': source, 'config': config}, broker_public, header)
        signed = {'header': header, 'envelope': envelope}
        return {**signed, 'signature': crypto.sign(signed, owner_private)}
    except (ManifestError, UnicodeError, crypto.CryptoError) as exc:
        raise ClientError('submission could not be packaged') from exc


def verify_receipt(bundle, broker_public, expected_request_hash, expected_subject,
                   expected_recipient_public, expected_broker_signing_key_id):
    """Verify trusted broker signature and every public result binding.

    A valid failed verification receipt is still authentic; this function never
    upgrades it to a passing research or deployment decision.
    """
    try:
        if type(bundle) is not dict or set(bundle) != {'binding', 'envelope', 'receipt', 'signature'}:
            raise ClientError('invalid result bundle')
        binding, receipt = bundle['binding'], bundle['receipt']
        fields = {'schema', 'job_id', 'subject', 'submission_id', 'request_hash',
                  'recipient_key_id', 'recipient_fingerprint'}
        receipt_fields = fields | {'broker_signing_key_id', 'result_envelope_hash', 'execution',
                                   'verification', 'delivery', 'started_at', 'finished_at', 'research_qualification'}
        if type(binding) is not dict or set(binding) != fields or type(receipt) is not dict or set(receipt) != receipt_fields:
            raise ClientError('invalid result fields')
        crypto.verify(receipt, bundle['signature'], broker_public)
        _hash(expected_request_hash)
        if binding['schema'] != 'straty-result/1' or receipt['schema'] != 'straty-receipt/1':
            raise ClientError('invalid result schema')
        if any(receipt[field] != binding[field] for field in fields - {'schema'}):
            raise ClientError('receipt binding mismatch')
        if (binding['subject'] != expected_subject or binding['request_hash'] != expected_request_hash
                or binding['recipient_fingerprint'] != key_fingerprint(expected_recipient_public)
                or receipt['broker_signing_key_id'] != expected_broker_signing_key_id
                or receipt['result_envelope_hash'] != sha256(canonical_json(bundle['envelope']))):
            raise ClientError('unexpected result binding')
        for field in ('job_id', 'submission_id'):
            if type(binding[field]) is not str or not re.fullmatch(r'[a-f0-9]{32}', binding[field]):
                raise ClientError('invalid result identifier')
        _text(binding['recipient_key_id'])
        if (receipt['execution'] != 'succeeded' or receipt['verification'] not in ('passed', 'failed')
                or receipt['delivery'] != 'available' or receipt['research_qualification'] != 'not_evaluated'):
            raise ClientError('invalid result state')
        if (any(type(receipt[key]) is not int or receipt[key] < 0 for key in ('started_at', 'finished_at'))
                or receipt['finished_at'] < receipt['started_at']):
            raise ClientError('invalid receipt timestamps')
        # Return a detached canonical copy, not a mutable reference into input.
        from .manifest import parse_json
        return parse_json(canonical_json(receipt))
    except (KeyError, TypeError, ValueError) as exc:
        raise ClientError('receipt verification failed') from exc


def decrypt_result(bundle, recipient_private, broker_public, *, expected_request,
                   expected_subject, expected_broker_signing_key_id):
    """Verify before decrypting; the caller explicitly controls plaintext use."""
    try:
        header = expected_request['header']
        recipient_public = crypto.public_key(recipient_private, 'x25519')
        receipt = verify_receipt(bundle, broker_public, sha256(canonical_json(expected_request)),
                                 expected_subject, recipient_public, expected_broker_signing_key_id)
        binding = bundle['binding']
        if (header['subject'] != expected_subject or header['submission_id'] != binding['submission_id']
                or header['recipient_key_id'] != binding['recipient_key_id']
                or header['recipient_fingerprint'] != binding['recipient_fingerprint']):
            raise ClientError('request binding mismatch')
        payload = crypto.open_envelope(bundle['envelope'], recipient_private, binding)
        if set(payload) != {'binding', 'manifest', 'result'} or payload['binding'] != binding:
            raise ClientError('encrypted binding mismatch')
        identity = payload['manifest']
        checks = {'schema': 'straty-frozen-run/1', 'owner': header['subject'],
                  'recipient_fingerprint': header['recipient_fingerprint'],
                  'data_sha256': header['dataset_sha256'], 'config_sha256': header['config_sha256'],
                  'engine_sha256': header['engine_sha256'], 'seed': header['seed']}
        if type(identity) is not dict or any(identity.get(k) != v for k, v in checks.items()):
            raise ClientError('execution identity mismatch')
        if payload['result']['verification']['status'] != receipt['verification']:
            raise ClientError('verification status mismatch')
        return payload
    except (KeyError, TypeError, ValueError) as exc:
        raise ClientError('result decryption or binding verification failed') from exc
