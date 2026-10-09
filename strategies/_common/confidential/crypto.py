"""Versioned confidential-lane cryptography; authorization belongs to the broker.

Raw private keys are never persisted here. These helpers do not assert that an
arbitrary supplied public key is trusted, nor promise Python memory zeroization.
"""
from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .manifest import ManifestError, canonical_json, parse_json, sha256


MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_AAD_BYTES = 256 * 1024
MAX_DOCUMENT_BYTES = 24 * 1024 * 1024
VERSION = 'straty-envelope/1'
_KDF_DOMAIN = b'straty-confidential/kdf/x25519-hkdf-sha256-aes256gcm/v1\x00'
_AAD_DOMAIN = b'straty-confidential/encryption/v1\x00'
_SIGN_DOMAIN = b'straty-confidential/signature/ed25519/v1\x00'
_FIELDS = {'version', 'ephemeral_public_key', 'nonce', 'ciphertext'}


class CryptoError(ValueError):
    """Invalid cryptographic input or failed authentication; contains no secrets."""


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode('ascii')


def _decode(value, *, maximum, exact=None):
    if type(value) is not str or len(value) > 4 * ((maximum + 2) // 3):
        raise CryptoError('invalid cryptographic encoding')
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise CryptoError('invalid cryptographic encoding') from None
    if len(raw) > maximum or (exact is not None and len(raw) != exact) or _encode(raw) != value:
        raise CryptoError('invalid cryptographic encoding')
    return raw


def _json(document, limit):
    if type(document) is not dict:
        raise CryptoError('JSON object required')
    try:
        raw = canonical_json(document)
    except (ManifestError, ValueError, RecursionError):
        raise CryptoError('invalid cryptographic document') from None
    if len(raw) > limit:
        raise CryptoError('cryptographic document exceeds size limit')
    return raw


def _private(private_b64, kind):
    if kind not in ('ed25519', 'x25519'):
        raise CryptoError('unsupported key kind')
    raw = _decode(private_b64, maximum=32, exact=32)
    cls = ed25519.Ed25519PrivateKey if kind == 'ed25519' else x25519.X25519PrivateKey
    return cls.from_private_bytes(raw)


def _public_raw(key):
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def generate_keypair(kind: str) -> tuple[str, str]:
    if kind not in ('ed25519', 'x25519'):
        raise CryptoError('unsupported key kind')
    cls = ed25519.Ed25519PrivateKey if kind == 'ed25519' else x25519.X25519PrivateKey
    key = cls.generate()
    private = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                serialization.NoEncryption())
    return _encode(private), _encode(_public_raw(key))


def public_key(private_b64: str, kind: str) -> str:
    return _encode(_public_raw(_private(private_b64, kind)))


def _derive(private, public_raw, ephemeral_raw, recipient_raw):
    try:
        secret = private.exchange(x25519.X25519PublicKey.from_public_bytes(public_raw))
    except ValueError:
        raise CryptoError('invalid key agreement') from None
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=_KDF_DOMAIN + ephemeral_raw + recipient_raw).derive(secret)


def seal(payload: dict, recipient_pub_b64: str, aad: dict) -> dict:
    plaintext = _json(payload, MAX_PAYLOAD_BYTES)
    associated = _AAD_DOMAIN + _json(aad, MAX_AAD_BYTES)
    recipient = _decode(recipient_pub_b64, maximum=32, exact=32)
    ephemeral = x25519.X25519PrivateKey.generate()
    ephemeral_raw = _public_raw(ephemeral)
    key = _derive(ephemeral, recipient, ephemeral_raw, recipient)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated)
    return {'version': VERSION, 'ephemeral_public_key': _encode(ephemeral_raw),
            'nonce': _encode(nonce), 'ciphertext': _encode(ciphertext)}


def open_envelope(envelope: dict, private_b64: str, aad: dict) -> dict:
    if type(envelope) is not dict or set(envelope) != _FIELDS or envelope['version'] != VERSION:
        raise CryptoError('unsupported envelope')
    associated = _AAD_DOMAIN + _json(aad, MAX_AAD_BYTES)
    ephemeral = _decode(envelope['ephemeral_public_key'], maximum=32, exact=32)
    nonce = _decode(envelope['nonce'], maximum=12, exact=12)
    ciphertext = _decode(envelope['ciphertext'], maximum=MAX_PAYLOAD_BYTES + 16)
    if len(ciphertext) < 16:
        raise CryptoError('invalid ciphertext')
    private = _private(private_b64, 'x25519')
    key = _derive(private, ephemeral, ephemeral, _public_raw(private))
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, associated)
    except InvalidTag:
        raise CryptoError('envelope authentication failed') from None
    try:
        payload = parse_json(plaintext)
        if type(payload) is not dict or canonical_json(payload) != plaintext:
            raise CryptoError('invalid encrypted document')
    except (ManifestError, ValueError, RecursionError):
        raise CryptoError('invalid encrypted document') from None
    return payload


def sign(document: dict, private_b64: str) -> str:
    raw = _json(document, MAX_DOCUMENT_BYTES)
    return _encode(_private(private_b64, 'ed25519').sign(_SIGN_DOMAIN + raw))


def verify(document: dict, signature_b64: str, public_b64: str) -> None:
    raw = _json(document, MAX_DOCUMENT_BYTES)
    signature = _decode(signature_b64, maximum=64, exact=64)
    public = _decode(public_b64, maximum=32, exact=32)
    try:
        ed25519.Ed25519PublicKey.from_public_bytes(public).verify(signature, _SIGN_DOMAIN + raw)
    except (InvalidSignature, ValueError):
        raise CryptoError('signature verification failed') from None
