import copy
import json
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import pytest

from strategies._common.graph.access import AccessDenied, WorkspaceServices
from strategies._common.graph.api import GraphHTTPServer
from strategies._common.graph.core import NodeType, Registry
from strategies._common.graph.service import GraphService, write_json


TOKEN = 'test-only-token-never-use-in-production-123456'


def source_node(inputs, params, context):
    return {'Value': 1}


def factory(root, **kwargs):
    registry = Registry()
    registry.register(NodeType('data.pool_strategy', {}, {'Value': 'Value'},
                      {'strategy_id': {'type': 'string', 'default': 'alpha'}},
                      source_node))
    return GraphService(root, registry=registry, **kwargs)


@pytest.fixture
def manager(tmp_path):
    (tmp_path / 'token').write_text(TOKEN)
    policy = {'schema': 'straty-access/1', 'workspace_root': str(tmp_path / 'private'),
              'source_root': str(tmp_path / 'templates'), 'proxy_token_file': 'token',
              'principals': {name: {'workspace': name, 'strategies': [sid],
                                   'node_types': ['data.pool_strategy']}
                             for name, sid in [('issuer|alice', 'alpha'), ('issuer|bob', 'beta')]}}
    for name, grant in policy['principals'].items():
        grant['workspace'] = name.split('|')[1]
    path = tmp_path / 'policy.json'
    write_json(path, policy)
    return WorkspaceServices(path, service_factory=factory)


def headers(subject='issuer|alice'):
    return {'X-Straty-Subject': subject, 'X-Straty-Proxy-Token': TOKEN}


def graph(sid):
    return {'schema': 'live-strategy-graph/1', 'strategy': sid,
            'nodes': [{'id': 'source', 'type': 'data.pool_strategy', 'params': {'strategy_id': sid}}], 'edges': []}


def test_fail_closed_authentication(manager):
    for hdr, peer in [({}, '127.0.0.1'), ({'X-Straty-Subject': 'issuer|alice'}, '127.0.0.1'),
                      (headers('issuer|unknown'), '127.0.0.1'), (headers(), '192.0.2.1')]:
        with pytest.raises(AccessDenied):
            manager.authenticate(hdr, peer)
    from email.message import Message
    duplicate = Message()
    for k, v in headers().items():
        duplicate[k] = v
    duplicate['X-Straty-Subject'] = 'issuer|bob'
    with pytest.raises(AccessDenied):
        manager.authenticate(duplicate, '127.0.0.1')


def test_private_storage_and_cross_strategy_rejection(manager):
    _, a = manager.authenticate(headers(), '127.0.0.1')
    _, b = manager.authenticate(headers('issuer|bob'), '127.0.0.1')
    a.set_graph(graph('alpha'), 'strategies/alpha/graph.json')
    a.save()
    assert b.document()['graph'] is None
    assert a.root != b.root and a.ledger.path != b.ledger.path
    with pytest.raises(Exception):
        b.load('../alice/strategies/alpha/graph.json')
    with pytest.raises(Exception):
        b.confined('../alice/.graph-runs/private.validation.json', sidecar=True)
    before = a.document()
    with pytest.raises(AccessDenied):
        a.parameters('source', {'strategy_id': 'beta'})
    assert a.document() == before
    forged = graph('alpha')
    forged['nodes'][0]['params']['strategy_id'] = 'beta'
    with pytest.raises(AccessDenied):
        a.set_graph(forged)
    assert b.results() == {'runs': []}
    assert b.experiments() == {'experiments': []}
    assert b.ledger.summary()['selection_n'] == 0
    a.jobs['secret'] = {'id': 'secret', 'status': 'complete'}
    assert 'secret' not in b.jobs


def test_pool_listing_select_and_private_template(manager, monkeypatch):
    from strategies._common import pool
    rows = [{'id': sid, 'selectable': True, 'graph_path': f'strategies/{sid}/graph.json'}
            for sid in ('alpha', 'beta')]
    monkeypatch.setattr(pool, 'pool', lambda **kwargs: {'strategies': rows, 'factors': [], 'pool_error': 'secret'})
    for row in rows:
        write_json(manager.source_root / row['graph_path'], graph(row['id']))
    _, a = manager.authenticate(headers(), '127.0.0.1')
    assert [s['id'] for s in a.strategies()['strategies']] == ['alpha']
    assert 'pool_error' not in a.strategies()
    with pytest.raises(AccessDenied):
        a.select_strategy('beta')
    a.select_strategy('alpha')
    assert a.path.is_relative_to(a.root)
    assert not a.path.is_relative_to(manager.source_root)


def test_http_cross_owner_endpoints(manager):
    _, a = manager.authenticate(headers(), '127.0.0.1')
    a.set_graph(graph('alpha'), 'strategies/alpha/graph.json')
    a.save()
    a.jobs['secret-job'] = {'id': 'secret-job', 'status': 'complete'}
    server = GraphHTTPServer(('127.0.0.1', 0), None, access=manager)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def call(path, subject='issuer|bob', body=None, authenticated=True):
        hdr = headers(subject) if authenticated else {}
        if body is not None:
            hdr['Content-Type'] = 'application/json'
        req = Request(f'http://127.0.0.1:{server.server_port}/api/{path}',
                      data=None if body is None else json.dumps(body).encode(), headers=hdr)
        try:
            with urlopen(req) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)
    try:
        assert call('graph', authenticated=False)[0] == 403
        assert call('graph')[1]['graph'] is None
        assert call('nodes')[1] == {'nodes': []}
        assert call('jobs/secret-job')[0] == 404
        assert call('jobs/secret-job/cancel', body={})[0] != 202
        assert call('results/secret-job')[0] != 200
        assert call('experiments/secret-job')[0] != 200
        assert call('strategies/select', body={'id': 'alpha'})[0] == 403
        assert call('graph/load', body={'path': '../alice/strategies/alpha/graph.json'})[0] != 200
        assert call('graph', body={'graph': graph('alpha')})[0] == 403
        assert call('session')[1]['access_mode'] == 'isolated'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_duplicate_workspace_policy_rejected(manager, tmp_path):
    policy_path = tmp_path / 'policy.json'
    policy = json.loads(policy_path.read_text())
    policy['principals']['issuer|bob']['workspace'] = 'alice'
    write_json(policy_path, policy)
    with pytest.raises(ValueError, match='shared'):
        WorkspaceServices(policy_path)


def test_node_grants_and_filesystem_escape(manager):
    _, service = manager.authenticate(headers(), '127.0.0.1')
    denied = graph('alpha')
    denied['nodes'][0]['type'] = 'agent.llm_view'
    with pytest.raises(AccessDenied):
        service.set_graph(denied)
    escaped = graph('alpha')
    escaped['nodes'][0]['params']['db_path'] = '../bob/data/papers.db'
    with pytest.raises(AccessDenied):
        service.set_graph(escaped)
    assert service.document()['graph'] is None


def test_distinct_cache_layout_and_saved_state(manager):
    _, a = manager.authenticate(headers(), '127.0.0.1')
    _, b = manager.authenticate(headers('issuer|bob'), '127.0.0.1')
    a.set_graph(graph('alpha'), 'strategies/alpha/graph.json')
    b.set_graph(graph('beta'), 'strategies/beta/graph.json')
    a.save()
    b.save()
    a.layout({'source': {'x': 123, 'y': 456}})
    assert b.layout()['positions'] == {}
    a.engine.values['source'] = {'Value': 'private alpha'}
    assert b.node('source')['outputs'] == {}
    assert a.engine.cache_dir != b.engine.cache_dir


def test_case_alias_workspace_rejected(manager, tmp_path):
    path = tmp_path / 'policy.json'
    policy = json.loads(path.read_text())
    policy['principals']['issuer|bob']['workspace'] = 'ALICE'
    write_json(path, policy)
    with pytest.raises(ValueError, match='shared'):
        WorkspaceServices(path)


@pytest.mark.parametrize('nested', [False, True])
def test_resolved_symlink_workspace_overlap_rejected(manager, tmp_path, nested):
    target = manager.root / 'alice'
    target.mkdir(parents=True)
    if nested:
        target = target / 'nested'
        target.mkdir()
    try:
        (manager.root / 'bob').symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip('directory symlink creation unavailable on this host')
    with pytest.raises(ValueError, match='shared or nested'):
        WorkspaceServices(tmp_path / 'policy.json')


def test_normalized_defaults_are_authorized(manager):
    _, service = manager.authenticate(headers(), '127.0.0.1')
    # An admin-defined node default may introduce a path absent from the raw
    # request. The normalized graph must be checked before state is changed.
    service.registry.types['data.pool_strategy'].params['db_path'] = {
        'type': 'string', 'default': '../bob/private.db'}
    with pytest.raises(AccessDenied):
        service.set_graph(graph('alpha'))
    assert service.graph is None
