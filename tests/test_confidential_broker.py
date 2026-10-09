"""Broker trust-boundary checks; Docker/evaluator are isolated test doubles."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

import pytest

from strategies._common.confidential import broker as mod
from strategies._common.confidential.crypto import generate_keypair, open_envelope, seal, sign, verify
from strategies._common.confidential.manifest import canonical_json, sha256


ENGINE = 'a' * 64
CANARY = 'PRIVATE_SOURCE_AND_METRICS_CANARY_793124'


class DummyWorker:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def cancel(self):
        pass


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'trusted_package_fingerprint', lambda *args: ENGINE)
    monkeypatch.setattr(mod, 'DockerStreamingWorker', DummyWorker)
    decrypt, decrypt_public = generate_keypair('x25519')
    signer, signer_public = generate_keypair('ed25519')
    alice, alice_public = generate_keypair('ed25519')
    alice_new, alice_new_public = generate_keypair('ed25519')
    recipient, recipient_public = generate_keypair('x25519')
    bob, bob_public = generate_keypair('ed25519')
    bob_recipient, bob_recipient_public = generate_keypair('x25519')
    (tmp_path / 'decrypt.key').write_text(decrypt)
    (tmp_path / 'sign.key').write_text(signer)
    data = b'[{"open":100,"close":101}]'
    (tmp_path / 'data.json').write_bytes(data)
    policy = {'schema': 'straty-broker/1', 'root': 'store', 'image': 'sha256:' + 'b' * 64,
              'engine_sha256': ENGINE, 'decrypt_key': {'id': 'broker-1', 'path': 'decrypt.key'},
              'signing_key': {'id': 'sign-1', 'path': 'sign.key'},
              'datasets': {'daily': {'path': 'data.json', 'sha256': sha256(data)}},
              'subjects': {}}
    for subject, public, rec in [('alice', alice_public, recipient_public),
                                  ('bob', bob_public, bob_recipient_public)]:
        policy['subjects'][subject] = {'datasets': ['daily'],
            'signing_keys': {'owner-1': {'active': True, 'public_key': public}},
            'recipient_keys': {'recipient-1': {'active': True, 'public_key': rec}}}
    policy['subjects']['alice']['signing_keys']['owner-2'] = {'active': True, 'public_key': alice_new_public}
    policy_path = tmp_path / 'policy.json'
    policy_path.write_bytes(canonical_json(policy))
    instances = []

    def create(evaluator=None):
        if evaluator is None:
            evaluator = lambda *args: {'verification': {'status': 'passed'}, 'metrics': {'private': CANARY}}
        instance = mod.Broker(policy_path, evaluator=evaluator)
        instances.append(instance)
        return instance

    def request(subject='alice', *, submission_id=None, owner_key='owner-1'):
        rec = recipient_public if subject == 'alice' else bob_recipient_public
        private = alice_new if owner_key == 'owner-2' else (alice if subject == 'alice' else bob)
        config = {'cost': '1.0'}
        now = int(time.time())
        header = {'schema': 'straty-submission/1', 'subject': subject,
                  'submission_id': submission_id or uuid.uuid4().hex, 'owner_key_id': owner_key,
                  'broker_key_id': 'broker-1', 'recipient_key_id': 'recipient-1',
                  'recipient_fingerprint': mod.key_fingerprint(rec), 'dataset_id': 'daily',
                  'dataset_sha256': sha256(data), 'engine_sha256': ENGINE,
                  'config_sha256': sha256(canonical_json(config)), 'seed': 0,
                  'issued_at': now, 'expires_at': now + 300}
        envelope = seal({'source': f'# {CANARY}\ndef decide(history):\n return 0\n', 'config': config},
                        decrypt_public, header)
        unsigned = {'header': header, 'envelope': envelope}
        return {**unsigned, 'signature': sign(unsigned, private)}

    yield {'create': create, 'request': request, 'path': policy_path, 'policy': policy,
           'root': tmp_path / 'store', 'recipient': recipient, 'signer_public': signer_public,
           'alice': alice, 'bob_recipient': bob_recipient, 'tmp': tmp_path}
    for instance in instances:
        instance.close()


def finish(instance, job):
    instance.thread.join(timeout=5)
    assert not instance.thread.is_alive()
    return instance.status('alice', job['id'])


def test_owner_access_ciphertext_and_signed_receipt(setup):
    broker = setup['create']()
    request = setup['request']()
    job = broker.submit('alice', request)
    assert finish(broker, job)['delivery'] == 'available'
    bundle = broker.result('alice', job['id'])
    verify(bundle['receipt'], bundle['signature'], setup['signer_public'])
    assert bundle['receipt']['result_envelope_hash'] == sha256(canonical_json(bundle['envelope']))
    assert bundle['binding']['request_hash'] == sha256(canonical_json(request))
    result = open_envelope(bundle['envelope'], setup['recipient'], bundle['binding'])
    assert result['result']['metrics']['private'] == CANARY
    with pytest.raises(ValueError):
        open_envelope(bundle['envelope'], setup['bob_recipient'], bundle['binding'])
    for operation in (broker.status, broker.result):
        with pytest.raises(mod.BrokerError):
            operation('bob', job['id'])
    with pytest.raises(mod.BrokerError):
        broker.submit('bob', request)
    with pytest.raises(mod.BrokerError):
        broker.capabilities('unknown')
    assert CANARY not in json.dumps(broker.status('alice', job['id']))
    assert CANARY not in json.dumps(bundle)
    broker.close()
    for path in setup['root'].rglob('*'):
        if path.is_file():
            assert CANARY.encode() not in path.read_bytes()


@pytest.mark.parametrize('field,value', [('subject', 'bob'), ('recipient_key_id', 'unknown'),
    ('recipient_fingerprint', '0' * 64), ('dataset_sha256', '0' * 64), ('engine_sha256', '0' * 64),
    ('config_sha256', '0' * 64), ('seed', 1), ('expires_at', 1)])
def test_header_tampering_rejected(setup, field, value):
    broker = setup['create']()
    request = setup['request']()
    request['header'][field] = value
    with pytest.raises(mod.BrokerError):
        broker.submit('alice', request)


def test_replay_persists_across_restart_and_signing_rotation(setup):
    broker = setup['create']()
    request = setup['request']()
    finish(broker, broker.submit('alice', request))
    broker.close()
    broker = setup['create']()
    for repeated in (request, setup['request'](submission_id=request['header']['submission_id'], owner_key='owner-2')):
        with pytest.raises(mod.BrokerError):
            broker.submit('alice', repeated)


def test_concurrent_submission_reserves_once(setup):
    entered, release = threading.Event(), threading.Event()
    count = []
    def evaluator(*args):
        count.append(1)
        entered.set()
        assert release.wait(5)
        return {'verification': {'status': 'passed'}, 'metrics': {'private': CANARY}}
    broker = setup['create'](evaluator)
    request = setup['request']()
    try:
        first = broker.submit('alice', request)
        assert entered.wait(3)
        failures = []
        def submit_again():
            try:
                broker.submit('alice', request)
            except mod.BrokerError:
                failures.append(True)
        threads = [threading.Thread(target=submit_again) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(3)
        assert len(failures) == 8
    finally:
        release.set()
    finish(broker, first)
    assert len(count) == 1


def test_process_lifetime_lock_rejects_second_process(setup):
    setup['create']()
    code = ('import sys\nfrom strategies._common.confidential.broker import Broker, BrokerError\n'
            'try:\n Broker(sys.argv[1])\nexcept BrokerError as e:\n'
            ' print(str(e))\n sys.exit(7)\n')
    result = subprocess.run([sys.executable, '-c', code, str(setup['path'])], capture_output=True,
                            text=True, timeout=15, cwd=Path(__file__).resolve().parents[1])
    assert result.returncode == 7, result.stderr
    assert 'already in use' in result.stdout


def test_errors_do_not_persist_exception_or_source(setup):
    def evaluator(*args):
        raise RuntimeError(CANARY)
    broker = setup['create'](evaluator)
    job = broker.submit('alice', setup['request']())
    status = finish(broker, job)
    assert status['execution'] == 'failed'
    assert status['verification'] == 'not_run'
    assert status['delivery'] == 'not_ready'
    with pytest.raises(mod.BrokerError):
        broker.result('alice', job['id'])
    broker.close()
    for path in setup['root'].rglob('*'):
        if path.is_file():
            assert CANARY.encode() not in path.read_bytes()


@pytest.mark.parametrize('execution', ['accepted', 'running'])
def test_restart_marks_orphan_interrupted_without_reexecution(setup, execution):
    broker = setup['create']()
    request = setup['request']()
    job = broker.submit('alice', request)
    finish(broker, job)
    with broker._db() as db:
        db.execute('UPDATE jobs SET execution=?, result_json=NULL WHERE id=?', (execution, job['id']))
    broker.close()
    calls = []
    broker = setup['create'](lambda *args: calls.append(True))
    status = broker.status('alice', job['id'])
    assert status['execution'] == 'interrupted'
    assert status['delivery'] == 'not_ready'
    assert not calls
    with pytest.raises(mod.BrokerError):
        broker.submit('alice', request)


def test_constructor_rejects_changed_data_and_releases_lock(setup):
    (setup['tmp'] / 'data.json').write_bytes(b'[123]')
    for _ in range(2):
        with pytest.raises(mod.BrokerError, match='dataset snapshot mismatch'):
            setup['create']()


def test_constructor_rejects_engine_change(setup, monkeypatch):
    monkeypatch.setattr(mod, 'trusted_package_fingerprint', lambda *args: 'c' * 64)
    with pytest.raises(mod.BrokerError, match='approved engine'):
        setup['create']()


def test_engine_changed_during_execution_never_releases_result(setup, monkeypatch):
    def evaluator(*args):
        monkeypatch.setattr(mod, 'trusted_package_fingerprint', lambda *args: 'c' * 64)
        return {'verification': {'status': 'passed'}, 'metrics': {'private': CANARY}}
    broker = setup['create'](evaluator)
    job = broker.submit('alice', setup['request']())
    assert finish(broker, job)['execution'] == 'failed'
    with pytest.raises(mod.BrokerError):
        broker.result('alice', job['id'])


def test_caller_cannot_mutate_accepted_execution_request(setup, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = mod.Broker._run
    def paused(self, *args):
        entered.set()
        assert release.wait(5)
        original(self, *args)
    monkeypatch.setattr(mod.Broker, '_run', paused)
    broker = setup['create']()
    request = setup['request']()
    original_request = copy.deepcopy(request)
    try:
        job = broker.submit('alice', request)
        assert entered.wait(3)
        request['header']['subject'] = 'bob'
        request['envelope']['ciphertext'] = 'corrupted'
    finally:
        release.set()
    assert finish(broker, job)['execution'] == 'succeeded'
    bundle = broker.result('alice', job['id'])
    assert bundle['binding']['request_hash'] == sha256(canonical_json(original_request))


def test_owner_signature_does_not_authorize_unregistered_recipient(setup):
    broker = setup['create']()
    request = setup['request']()
    request['header']['recipient_fingerprint'] = 'f' * 64
    request['signature'] = sign({'header': request['header'], 'envelope': request['envelope']}, setup['alice'])
    with pytest.raises(mod.BrokerError):
        broker.submit('alice', request)


def test_signed_wrong_config_binding_fails_without_result(setup):
    broker = setup['create']()
    request = setup['request']()
    h = request['header']
    request['envelope'] = seal({'source': f'# {CANARY}', 'config': {'cost': '999'}}, broker.decrypt_public, h)
    request['signature'] = sign({'header': h, 'envelope': request['envelope']}, setup['alice'])
    job = broker.submit('alice', request)
    assert finish(broker, job)['execution'] == 'failed'
    with pytest.raises(mod.BrokerError):
        broker.result('alice', job['id'])


def test_dataset_file_change_after_start_cannot_replace_frozen_snapshot(setup):
    seen = []
    def evaluator(frozen, *args):
        seen.append(frozen.data_json_bytes)
        return {'verification': {'status': 'passed'}, 'metrics': {'private': CANARY}}
    broker = setup['create'](evaluator)
    original = (setup['tmp'] / 'data.json').read_bytes()
    (setup['tmp'] / 'data.json').write_bytes(b'[{"open":999,"close":999}]')
    job = broker.submit('alice', setup['request']())
    assert finish(broker, job)['execution'] == 'succeeded'
    assert seen == [original]


@pytest.mark.parametrize('update', [{'active': False}, {'expires_at': 1}, {'valid_from': 2**62}])
def test_owner_key_policy_is_enforced(setup, update):
    broker = setup['create']()
    broker.subjects['alice']['signing_keys']['owner-1'].update(update)
    with pytest.raises(mod.BrokerError):
        broker.submit('alice', setup['request']())
