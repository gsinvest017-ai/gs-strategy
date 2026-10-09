"""Opt-in real Docker + authenticated HTTP + crypto + broker integration.

Set STRATY_TEST_DOCKER_IMAGE to an immutable locally available Python image
digest. No worker, evaluator, engine measurement or authentication is mocked.
"""
import copy
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from strategies._common.confidential.broker import Broker, PACKAGE
from strategies._common.confidential.client import ClientError, decrypt_result, pack_submission, verify_receipt
from strategies._common.confidential.crypto import generate_keypair
from strategies._common.confidential.manifest import canonical_json, sha256, trusted_package_fingerprint
from strategies._common.graph.access import WorkspaceServices
from strategies._common.graph.api import GraphHTTPServer
from strategies._common.graph.core import Registry
from strategies._common.graph.service import GraphService


IMAGE = os.environ.get('STRATY_TEST_DOCKER_IMAGE')
pytestmark = pytest.mark.skipif(not IMAGE, reason='set STRATY_TEST_DOCKER_IMAGE for real Docker E2E')
SUBJECT = 'test-issuer|alice'
OTHER = 'test-issuer|bob'
CONFIG = {'adapter': 'daily-futures-next-open/1', 'point_value': '50',
          'commission_per_side': '3', 'slippage_points': '1', 'initial_capital': '100000',
          'margin_per_contract': '10000', 'max_contracts': 2}


@pytest.fixture
def live(tmp_path):
    assert (PACKAGE / 'engine.py').exists(), 'real engine must exist before running E2E'
    decrypt, decrypt_public = generate_keypair('x25519')
    signing, signing_public = generate_keypair('ed25519')
    owner, owner_public = generate_keypair('ed25519')
    recipient, recipient_public = generate_keypair('x25519')
    _, other_owner = generate_keypair('ed25519')
    _, other_recipient = generate_keypair('x25519')
    (tmp_path / 'broker-decrypt.key').write_text(decrypt, encoding='utf-8')
    (tmp_path / 'broker-signing.key').write_text(signing, encoding='utf-8')
    data = canonical_json([
        {'date': '2025-01-01', 'open': 100, 'high': 101, 'low': 99, 'close': 100},
        {'date': '2025-01-02', 'open': 100, 'high': 103, 'low': 99, 'close': 102},
        {'date': '2025-01-03', 'open': 103, 'high': 104, 'low': 100, 'close': 101},
        {'date': '2025-01-04', 'open': 104, 'high': 106, 'low': 103, 'close': 105},
    ])
    (tmp_path / 'dataset.json').write_bytes(data)
    engine = trusted_package_fingerprint(PACKAGE, IMAGE)
    policy = {'schema': 'straty-broker/1', 'root': 'broker-store', 'image': IMAGE,
              'engine_sha256': engine,
              'decrypt_key': {'id': 'decrypt-1', 'path': 'broker-decrypt.key'},
              'signing_key': {'id': 'sign-1', 'path': 'broker-signing.key'},
              'datasets': {'daily': {'path': 'dataset.json', 'sha256': sha256(data)}}, 'subjects': {}}
    for subject, verify_key, recipient_key in [(SUBJECT, owner_public, recipient_public),
                                              (OTHER, other_owner, other_recipient)]:
        policy['subjects'][subject] = {'datasets': ['daily'],
            'signing_keys': {'owner-1': {'active': True, 'public_key': verify_key}},
            'recipient_keys': {'recipient-1': {'active': True, 'public_key': recipient_key}}}
    (tmp_path / 'broker-policy.json').write_bytes(canonical_json(policy))
    token = secrets.token_hex(32)
    (tmp_path / 'proxy-token').write_text(token, encoding='utf-8')
    access_policy = {'schema': 'straty-access/1', 'workspace_root': str(tmp_path / 'workspaces'),
        'source_root': str(tmp_path / 'templates'), 'proxy_token_file': 'proxy-token',
        'principals': {subject: {'workspace': workspace, 'strategies': [], 'node_types': []}
                       for subject, workspace in [(SUBJECT, 'alice'), (OTHER, 'bob')]}}
    (tmp_path / 'access-policy.json').write_bytes(canonical_json(access_policy))
    # Real GraphService with no legacy nodes: the confidential lane needs none.
    access = WorkspaceServices(tmp_path / 'access-policy.json',
        service_factory=lambda root, **kwargs: GraphService(root, registry=Registry(), **kwargs))
    broker = Broker(tmp_path / 'broker-policy.json')
    server = GraphHTTPServer(('127.0.0.1', 0), None, access=access, broker=broker)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def call(path, *, subject=SUBJECT, body=None, proxy_token=token):
        headers = {'Content-Type': 'application/json', 'X-Straty-Subject': subject,
                   'X-Straty-Proxy-Token': proxy_token}
        request = Request(f'http://127.0.0.1:{server.server_port}/api/confidential/{path}',
                          data=None if body is None else canonical_json(body), headers=headers)
        try:
            with urlopen(request, timeout=15) as response:
                assert response.headers['Cache-Control'] == 'no-store'
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def package(source):
        now = int(time.time())
        return pack_submission(source=source, config=CONFIG, subject=SUBJECT, submission_id=None,
            dataset_id='daily', dataset_sha256=sha256(data), engine_sha256=engine, seed=42,
            owner_key_id='owner-1', owner_private=owner, broker_key_id='decrypt-1', broker_public=decrypt_public,
            recipient_key_id='recipient-1', recipient_public=recipient_public, issued_at=now, expires_at=now + 600)

    def wait(job_id):
        deadline = time.monotonic() + 135
        while time.monotonic() < deadline:
            code, status = call('jobs/' + job_id)
            assert code == 200
            if status['execution'] not in ('accepted', 'running'):
                return status
            time.sleep(0.1)
        pytest.fail('broker did not finish within bounded E2E deadline')

    yield {'call': call, 'package': package, 'wait': wait, 'broker': broker, 'root': tmp_path,
           'recipient': recipient, 'recipient_public': recipient_public, 'signing_public': signing_public}
    server.shutdown()
    server.server_close()
    thread.join(timeout=10)
    broker.close()
    access.close()


def assert_no_canary_on_disk(live, canary):
    # Release the Windows byte-range lock before inspecting every persisted file.
    live['broker'].close()
    for path in live['root'].rglob('*'):
        if path.is_file():
            assert canary.encode() not in path.read_bytes(), f'plaintext leak in {path.name}'
            if (live['root'] / 'broker-store') in path.parents:
                assert b'"net_pnl"' not in path.read_bytes(), f'plaintext metrics in {path.name}'


def test_real_docker_broker_http_crypto_and_financial_result(live):
    canary = 'E2E_SOURCE_CANARY_' + secrets.token_hex(16)
    source = f'# {canary}\ndef decide(history):\n    return 1\n'
    call = live['call']
    assert call('capabilities', proxy_token='wrong')[0] == 403
    assert call('capabilities', subject='unknown')[0] == 403
    code, capabilities = call('capabilities')
    assert code == 200 and capabilities['adapter'] == CONFIG['adapter']
    request = live['package'](source)
    assert canary not in json.dumps(request)
    assert call('jobs', subject=OTHER, body=request)[0] == 400
    code, job = call('jobs', body=request)
    assert code == 202
    status = live['wait'](job['id'])
    assert status['execution'] == 'succeeded', status
    assert status['verification'] == 'passed', status
    assert status['delivery'] == 'available'
    assert call(f"jobs/{job['id']}", subject=OTHER)[0] == 400
    assert call(f"jobs/{job['id']}/result", subject=OTHER)[0] == 400
    code, bundle = call(f"jobs/{job['id']}/result")
    assert code == 200
    receipt = verify_receipt(bundle, live['signing_public'], sha256(canonical_json(request)),
                             SUBJECT, live['recipient_public'], 'sign-1')
    assert receipt['research_qualification'] == 'not_evaluated'
    payload = decrypt_result(bundle, live['recipient'], live['signing_public'],
        expected_request=request, expected_subject=SUBJECT, expected_broker_signing_key_id='sign-1')
    result = payload['result']
    # Financial assertions use Decimal; expected result is independently derived:
    # -100 intraday +150 overnight +50 intraday -2*(3+50) costs = -6.
    assert Decimal(result['metrics']['net_pnl']) == Decimal('-6')
    assert Decimal(result['metrics']['equity_end']) == Decimal('99994')
    assert result['metrics']['first_execution_date'] == '2025-01-03'
    assert result['metrics']['last_execution_date'] == '2025-01-04'
    assert len(result['daily']) == 2
    first, last = result['daily']
    assert Decimal(first['intraday_pnl']) == Decimal('-100')
    assert Decimal(first['overnight_pnl']) == 0
    assert Decimal(first['pnl']) == Decimal('-153')
    assert Decimal(last['overnight_pnl']) == Decimal('150')
    assert Decimal(last['intraday_pnl']) == Decimal('50')
    assert Decimal(last['terminal_exit_cost']) == Decimal('53')
    assert last['closing_position'] == 0
    assert len(result['trades']) == 1
    trade = result['trades'][0]
    assert trade['entry_date'] == '2025-01-03' and trade['entry_event'] == 'open'
    assert trade['exit_date'] == '2025-01-04' and trade['exit_event'] == 'terminal_close'
    assert Decimal(trade['pnl']) == Decimal('-6')
    assert sum(Decimal(item['pnl']) for item in result['trades']) == (
        Decimal(result['metrics']['equity_end']) - Decimal(CONFIG['initial_capital']))
    assert all(result['verification']['checks'].values())
    assert payload['manifest']['source_sha256'] == sha256(source.encode())
    modified = copy.deepcopy(bundle)
    modified['receipt']['result_envelope_hash'] = '0' * 64
    with pytest.raises(ClientError):
        decrypt_result(modified, live['recipient'], live['signing_public'],
            expected_request=request, expected_subject=SUBJECT, expected_broker_signing_key_id='sign-1')
    assert call('jobs', body=request)[0] == 400
    assert canary not in json.dumps(bundle)
    assert_no_canary_on_disk(live, canary)


def test_real_docker_rejects_forged_worker_protocol(live):
    canary = 'E2E_ATTACK_CANARY_' + secrets.token_hex(16)
    source = (f'# {canary}\nimport os\n'
              'os.write(1, b\'{"nonce":"forged","ready":true,"metrics":{"net_pnl":"999999"}}\\n\')\n'
              'def decide(history):\n    return 1\n')
    code, job = live['call']('jobs', body=live['package'](source))
    assert code == 202
    status = live['wait'](job['id'])
    assert status['execution'] == 'failed'
    assert status['verification'] == 'not_run'
    assert status['delivery'] == 'not_ready'
    assert live['call'](f"jobs/{job['id']}/result")[0] == 400
    assert canary not in json.dumps(status)
    assert_no_canary_on_disk(live, canary)
