import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from tests.test_live_graph_api import make_service, finish
from strategies._common.graph.api import GraphHTTPServer

@pytest.fixture
def api(tmp_path):
    service = make_service(tmp_path)
    server = GraphHTTPServer(('127.0.0.1', 0), service)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(path, body=None):
        request = Request(f'http://127.0.0.1:{server.server_port}/api{path}', data=None if body is None else json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        try:
            with urlopen(request) as response: return response.status, json.load(response)
        except HTTPError as error: return error.code, json.load(error)
    yield service, call
    server.shutdown(); server.server_close(); thread.join()

def test_seen_estimate_conflict_does_not_add_selection(api):
    service, call = api
    finish(service)
    shown = call('/run-estimate')[1]
    assert shown['delta_n'] == 0
    revision = call('/graph')[1].get('revision', 0)
    assert call('/nodes/feature/params', {'params': {'value': 2}, 'expected_revision': revision})[0] == 200
    jobs_before = len(service.jobs)
    status, result = call('/run', {'expected_revision': revision, 'expected_backtest_key': shown['backtest_key']})
    assert status == 409
    assert result['code'] == 'graph_revision_conflict'
    assert service.ledger.summary()['selection_n'] == 1
    assert len(service.jobs) == jobs_before

def test_stale_edge_delete_preserves_new_parameters(api):
    service, call = api
    old = call('/graph')[1]
    revision = old.get('revision', 0)
    assert call('/nodes/feature/params', {'params': {'value': 2}, 'expected_revision': revision})[0] == 200
    edges_before = copy.deepcopy(service.graph['edges'])
    old['graph']['edges'].pop()
    status, result = call('/graph', {'graph': old['graph'], 'expected_revision': revision})
    assert status == 409
    assert result['code'] == 'graph_revision_conflict'
    assert next(n for n in service.graph['nodes'] if n['id'] == 'feature')['params']['value'] == 2
    assert service.graph['edges'] == edges_before

def test_two_fixture_processes_never_write_shared_calendar(tmp_path):
    package = tmp_path / 'TejToolAPI'; package.mkdir()
    (package / '__init__.py').write_text('')
    cache = package / 'temp/exchange_calendar.csv'; cache.parent.mkdir()
    original = b'original-calendar-sentinel\n'; cache.write_bytes(original)
    (tmp_path / 'tejapi.py').write_text('def fastget(*args, **kwargs): pass\n')
    (tmp_path / 'zipline.py').write_text("import os,time\nfrom pathlib import Path\np=Path(os.environ['AUDIT_GATE'])\np.with_suffix('.ready').touch()\nwhile not p.exists(): time.sleep(.02)\n")
    program = 'import sys; sys.path.insert(0,sys.argv[1]); sys.path.append(sys.argv[2]); from strategies.tsmom_tx_mtx.fixture_bundle import import_zipline_offline; import_zipline_offline()'
    children = []
    unchanged = []
    try:
        for label in ('a', 'b'):
            gate = tmp_path / label
            child = subprocess.Popen([sys.executable, '-B', '-c', program, str(tmp_path), str(Path.cwd())], cwd=tmp_path, env={**os.environ, 'AUDIT_GATE': str(gate)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            children.append((child, gate))
            deadline = time.monotonic() + 30
            while not gate.with_suffix('.ready').exists():
                assert child.poll() is None, 'fixture process failed'
                assert time.monotonic() < deadline, 'fixture process timeout'
                time.sleep(.02)
            unchanged.append(cache.read_bytes() == original)
        for child, gate in children:
            gate.touch(); child.wait(timeout=30)
            assert child.returncode == 0
            unchanged.append(cache.read_bytes() == original)
        assert all(unchanged), 'shared calendar was modified'
    finally:
        for child, gate in children:
            gate.touch()
            if child.poll() is None: child.wait(timeout=30)

@pytest.mark.parametrize('endpoint', ['/graph', '/graph/load', '/graph/save', '/graph/from-sidecar', '/nodes/feature/params'])
@pytest.mark.parametrize('invalid_revision', [None, -1, True, 1.0])
def test_every_graph_mutation_rejects_invalid_revision_atomically(api, endpoint, invalid_revision):
    service, call = api
    before = service.document()
    saved = service.path.read_bytes()
    body = {'graph': before['graph'], 'params': {'value': 2}, 'path': 'strategies/tsmom_tx_mtx/graph.json'}
    if invalid_revision is not None:
        body['expected_revision'] = invalid_revision
    status, result = call(endpoint, body)
    assert status == 409
    assert result == {'code': 'graph_revision_conflict', 'error': '圖已被其他分頁修改，請重新載入', 'revision': before['revision']}
    assert service.document() == before
    assert service.path.read_bytes() == saved

@pytest.mark.parametrize('key', [None, '', 'stale-key'])
def test_run_key_conflict_creates_no_job(api, key):
    service, call = api
    body = {'expected_revision': service.revision}
    if key is not None:
        body['expected_backtest_key'] = key
    status, result = call('/run', body)
    assert status == 409
    assert result['code'] == 'run_estimate_conflict'
    assert not service.jobs
    assert service.ledger.summary()['selection_n'] == 0

def test_run_executes_once_prepared_checked_snapshot(api, monkeypatch):
    service, call = api
    estimate = service.run_estimate()
    original = service.prepare
    calls = []
    def prepare(graph):
        calls.append(copy.deepcopy(graph))
        return original(graph)
    monkeypatch.setattr(service, 'prepare', prepare)
    status, job = call('/run', {'expected_revision': estimate['revision'], 'expected_backtest_key': estimate['backtest_key']})
    assert status == 202
    service._thread.join(20)
    assert service.jobs[job['id']]['status'] == 'complete'
    assert len(calls) == 1
    assert service.jobs[job['id']]['backtest_key'] == estimate['backtest_key']
