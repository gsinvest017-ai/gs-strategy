import copy
import json
from pathlib import Path

import pytest

from strategies._common.confidential import crypto
from strategies._common.confidential.client import ClientError, key_fingerprint, pack_submission, verify_receipt, decrypt_result
from strategies._common.confidential.__main__ import main
from strategies._common.confidential.manifest import canonical_json, sha256


@pytest.fixture
def keys():
    return {kind: crypto.generate_keypair(keytype) for kind, keytype in
            [('owner', 'ed25519'), ('broker', 'x25519'), ('recipient', 'x25519')]}


def metadata(keys):
    return {'subject': 'issuer|alice', 'submission_id': '1' * 32, 'dataset_id': 'fixture',
            'dataset_sha256': 'a' * 64, 'engine_sha256': 'b' * 64, 'seed': 13,
            'owner_key_id': 'owner-1', 'owner_private': keys['owner'][0],
            'broker_key_id': 'broker-1', 'broker_public': keys['broker'][1],
            'recipient_key_id': 'recipient-1', 'recipient_public': keys['recipient'][1],
            'issued_at': 100, 'expires_at': 200}


def test_pack_signs_full_envelope_and_hides_source(keys):
    source = 'def target(history):\n    return 314159\n'
    config = {'cost': '0.25'}
    packed = pack_submission(source=source, config=config, **metadata(keys))
    signed = {key: packed[key] for key in ('header', 'envelope')}
    assert crypto.verify(signed, packed['signature'], keys['owner'][1]) is None
    assert source not in json.dumps(packed)
    assert crypto.open_envelope(packed['envelope'], keys['broker'][0], packed['header']) == {'source': source, 'config': config}
    assert packed['header']['config_sha256'] == sha256(canonical_json(config))
    assert packed['header']['recipient_fingerprint'] == key_fingerprint(keys['recipient'][1])
    assert 'source_sha256' not in packed['header']


@pytest.mark.parametrize('field', ['subject', 'recipient_key_id', 'recipient_fingerprint', 'dataset_sha256',
                                  'engine_sha256', 'config_sha256', 'seed', 'expires_at'])
def test_metadata_tampering_breaks_signature_and_aad(keys, field):
    packed = pack_submission(source='private code', config={}, **metadata(keys))
    header = copy.deepcopy(packed['header'])
    header[field] = header[field] + 1 if type(header[field]) is int else header[field] + 'changed'
    with pytest.raises(crypto.CryptoError):
        crypto.verify({'header': header, 'envelope': packed['envelope']}, packed['signature'], keys['owner'][1])
    with pytest.raises(crypto.CryptoError):
        crypto.open_envelope(packed['envelope'], keys['broker'][0], header)


@pytest.mark.parametrize('field,value', [('submission_id', '../path'), ('seed', True), ('seed', -1),
                                       ('expires_at', 99), ('dataset_sha256', 'bad'), ('subject', ''),
                                       ('broker_public', 'bad'), ('recipient_public', 'bad')])
def test_pack_rejects_invalid_metadata(keys, field, value):
    args = metadata(keys)
    args[field] = value
    with pytest.raises(ClientError):
        pack_submission(source='private code', config={}, **args)


def test_random_submission_ids(keys):
    args = metadata(keys)
    args['submission_id'] = None
    first = pack_submission(source='code', config={}, **args)
    second = pack_submission(source='code', config={}, **args)
    assert len(first['header']['submission_id']) == 32
    assert first['header']['submission_id'] != second['header']['submission_id']


def test_cli_keygen_exclusive_files_and_no_secret_stdout(tmp_path, capsys):
    private, public = tmp_path / 'private.key', tmp_path / 'public.key'
    args = ['keygen', '--kind', 'ed25519', '--private-out', str(private), '--public-out', str(public)]
    assert main(args) == 0
    private_bytes = private.read_bytes()
    assert public.read_text().strip() == crypto.public_key(private.read_text().strip(), 'ed25519')
    captured = capsys.readouterr()
    assert private.read_text().strip() not in captured.out + captured.err
    assert main(args) == 1
    assert private.read_bytes() == private_bytes
    assert 'error' in capsys.readouterr().err


def test_cli_pack_reads_relative_key_paths_and_preserves_existing_output(keys, tmp_path, capsys):
    spec = metadata(keys)
    for name, value in [('owner_private', keys['owner'][0]), ('broker_public', keys['broker'][1]),
                        ('recipient_public', keys['recipient'][1])]:
        spec.pop(name)
        spec[name + '_path'] = name + '.key'
        (tmp_path / spec[name + '_path']).write_text(value, encoding='ascii')
    spec_path = tmp_path / 'spec.json'
    spec_path.write_bytes(canonical_json(spec))
    source, config, output = tmp_path / 'strategy.py', tmp_path / 'config.json', tmp_path / 'submission.json'
    source.write_text('secret source', encoding='utf-8')
    config.write_bytes(b'{"cost":"0.25"}')
    args = ['pack', '--spec', str(spec_path), '--source', str(source), '--config', str(config), '--out', str(output)]
    assert main(args) == 0
    packed = json.loads(output.read_bytes())
    payload = crypto.open_envelope(packed['envelope'], keys['broker'][0], packed['header'])
    assert payload['source'] == 'secret source'
    original = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == original
    captured = capsys.readouterr()
    assert 'secret source' not in captured.out + captured.err


def test_cli_rejects_duplicate_config_keys(keys, tmp_path):
    spec = tmp_path / 'spec.json'
    document = metadata(keys)
    for name in ('owner_private', 'broker_public', 'recipient_public'):
        value = document.pop(name)
        document[name + '_path'] = name + '.key'
        (tmp_path / document[name + '_path']).write_text(value, encoding='ascii')
    spec.write_bytes(canonical_json(document))
    source, config, output = tmp_path / 'source.py', tmp_path / 'config.json', tmp_path / 'out.json'
    source.write_text('sensitive payload', encoding='utf-8')
    config.write_bytes(b'{"x":1,"x":2}')
    assert main(['pack', '--spec', str(spec), '--source', str(source), '--config', str(config), '--out', str(output)]) == 1
    assert not output.exists()


@pytest.fixture
def result_bundle(keys):
    request = pack_submission(source='secret source', config={'cost': '0.25'}, **metadata(keys))
    signing = crypto.generate_keypair('ed25519')
    header = request['header']
    binding = {'schema': 'straty-result/1', 'job_id': '2' * 32, 'subject': header['subject'],
               'submission_id': header['submission_id'], 'request_hash': sha256(canonical_json(request)),
               'recipient_key_id': header['recipient_key_id'], 'recipient_fingerprint': header['recipient_fingerprint']}
    manifest = {'schema': 'straty-frozen-run/1', 'owner': header['subject'], 'seed': header['seed'],
                'recipient_fingerprint': header['recipient_fingerprint'], 'data_sha256': header['dataset_sha256'],
                'config_sha256': header['config_sha256'], 'engine_sha256': header['engine_sha256']}
    payload = {'binding': binding, 'manifest': manifest,
               'result': {'verification': {'status': 'passed'}, 'secret_metric': '123456.78'}}
    envelope = crypto.seal(payload, keys['recipient'][1], binding)
    receipt = {**binding, 'schema': 'straty-receipt/1', 'broker_signing_key_id': 'signer-1',
               'result_envelope_hash': sha256(canonical_json(envelope)), 'execution': 'succeeded',
               'verification': 'passed', 'delivery': 'available', 'started_at': 101, 'finished_at': 102,
               'research_qualification': 'not_evaluated'}
    bundle = {'binding': binding, 'envelope': envelope, 'receipt': receipt, 'signature': crypto.sign(receipt, signing[0])}
    return request, bundle, signing, payload


def test_verify_then_decrypt_result(keys, result_bundle):
    request, bundle, signing, payload = result_bundle
    receipt = verify_receipt(bundle, signing[1], sha256(canonical_json(request)), 'issuer|alice', keys['recipient'][1], 'signer-1')
    assert receipt['verification'] == 'passed'
    assert decrypt_result(bundle, keys['recipient'][0], signing[1], expected_request=request,
                          expected_subject='issuer|alice', expected_broker_signing_key_id='signer-1') == payload


@pytest.mark.parametrize('field,value', [('subject', 'issuer|bob'), ('request_hash', '0' * 64),
                                       ('recipient_fingerprint', '0' * 64), ('result_envelope_hash', '0' * 64),
                                       ('broker_signing_key_id', 'other'), ('execution', 'failed'),
                                       ('verification', 'unknown'), ('delivery', 'acknowledged'),
                                       ('research_qualification', 'approved'), ('finished_at', 1)])
def test_valid_signature_still_requires_correct_binding_and_states(keys, result_bundle, field, value):
    request, bundle, signing, _ = result_bundle
    bundle['receipt'][field] = value
    bundle['signature'] = crypto.sign(bundle['receipt'], signing[0])
    with pytest.raises(ClientError):
        verify_receipt(bundle, signing[1], sha256(canonical_json(request)), 'issuer|alice', keys['recipient'][1], 'signer-1')


@pytest.mark.parametrize('field', ['owner', 'recipient_fingerprint', 'data_sha256', 'config_sha256', 'engine_sha256', 'seed'])
def test_encrypted_manifest_must_match_original_request(keys, result_bundle, field):
    request, bundle, signing, payload = result_bundle
    payload['manifest'][field] = 999 if field == 'seed' else 'wrong'
    bundle['envelope'] = crypto.seal(payload, keys['recipient'][1], bundle['binding'])
    bundle['receipt']['result_envelope_hash'] = sha256(canonical_json(bundle['envelope']))
    bundle['signature'] = crypto.sign(bundle['receipt'], signing[0])
    with pytest.raises(ClientError):
        decrypt_result(bundle, keys['recipient'][0], signing[1], expected_request=request,
                       expected_subject='issuer|alice', expected_broker_signing_key_id='signer-1')


def test_cli_verify_and_explicit_decrypt_never_print_plaintext(keys, result_bundle, tmp_path, capsys):
    request, bundle, signing, payload = result_bundle
    for name, doc in [('request.json', request), ('result.json', bundle)]:
        (tmp_path / name).write_bytes(canonical_json(doc))
    for name, key in [('broker.pub', signing[1]), ('recipient.pub', keys['recipient'][1]), ('recipient.key', keys['recipient'][0])]:
        (tmp_path / name).write_text(key, encoding='ascii')
    common = ['--result', str(tmp_path / 'result.json'), '--request', str(tmp_path / 'request.json'),
              '--broker-public', str(tmp_path / 'broker.pub'), '--broker-signing-key-id', 'signer-1', '--subject', 'issuer|alice']
    assert main(['verify', *common, '--recipient-public', str(tmp_path / 'recipient.pub')]) == 0
    assert '"verification": "passed"' in capsys.readouterr().out
    output = tmp_path / 'plaintext.json'
    args = ['decrypt', *common, '--recipient-private', str(tmp_path / 'recipient.key'), '--out', str(output)]
    assert main(args) == 0
    assert json.loads(output.read_bytes()) == payload
    assert '123456.78' not in capsys.readouterr().out
    assert main(args) == 1
    assert json.loads(output.read_bytes()) == payload


def test_wrong_recipient_and_broker_keys_fail(keys, result_bundle):
    request, bundle, signing, _ = result_bundle
    wrong_recipient, _ = crypto.generate_keypair('x25519')
    _, wrong_broker = crypto.generate_keypair('ed25519')
    for private, public in [(wrong_recipient, signing[1]), (keys['recipient'][0], wrong_broker)]:
        with pytest.raises(ClientError):
            decrypt_result(bundle, private, public, expected_request=request,
                           expected_subject='issuer|alice', expected_broker_signing_key_id='signer-1')


def test_authentic_failed_verification_is_not_upgraded(keys, result_bundle):
    request, bundle, signing, payload = result_bundle
    payload['result']['verification']['status'] = 'failed'
    bundle['envelope'] = crypto.seal(payload, keys['recipient'][1], bundle['binding'])
    bundle['receipt']['result_envelope_hash'] = sha256(canonical_json(bundle['envelope']))
    bundle['receipt']['verification'] = 'failed'
    bundle['signature'] = crypto.sign(bundle['receipt'], signing[0])
    receipt = verify_receipt(bundle, signing[1], sha256(canonical_json(request)), 'issuer|alice', keys['recipient'][1], 'signer-1')
    assert receipt['verification'] == 'failed'
    decrypted = decrypt_result(bundle, keys['recipient'][0], signing[1], expected_request=request,
                               expected_subject='issuer|alice', expected_broker_signing_key_id='signer-1')
    assert decrypted['result']['verification']['status'] == 'failed'
