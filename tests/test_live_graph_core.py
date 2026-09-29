import copy
from pathlib import Path
import pytest
from strategies._common.graph import Registry, NodeType, Engine, Context, GraphError, CancelToken, Cancelled, code_fingerprint

CALLS = {}
def source(inputs, params, ctx):
    CALLS['source'] = CALLS.get('source', 0) + 1
    return {'Score': params['value']}
def scale(inputs, params, ctx):
    CALLS['scale'] = CALLS.get('scale', 0) + 1
    return {'Weights': inputs['Score'] * params['factor']}
def changed(inputs, params, ctx):
    CALLS['scale'] = CALLS.get('scale', 0) + 1
    return {'Weights': inputs['Score'] * params['factor'] + 1}
def backtest(inputs, params, ctx):
    CALLS['backtest'] = CALLS.get('backtest', 0) + 1
    return {'Returns': [inputs['Weights']]}
class Ledger:
    def __init__(self): self.seen = set()
    def record_success(self, key, snapshot, result, ctx): self.seen.add(key)
    def summary(self): return {'n': len(self.seen)}
def setup():
    CALLS.clear()
    r = Registry()
    r.register(NodeType('feature.source', {}, {'Score': 'Score'}, {'value': {'type': 'number', 'default': 2}}, source))
    r.register(NodeType('sizing.scale', {'Score': 'Score'}, {'Weights': 'Weights'}, {'factor': {'type': 'number', 'default': 3}}, scale))
    r.register(NodeType('backtest.test', {'Weights': 'Weights'}, {'Returns': 'Returns'}, {}, backtest))
    g = {'schema': 'live-strategy-graph/1', 'nodes': [{'id': 'a', 'type': 'feature.source'}, {'id': 'b', 'type': 'sizing.scale'}, {'id': 'c', 'type': 'backtest.test'}], 'edges': [{'from': ['a','Score'], 'to': ['b','Score']}, {'from':['b','Weights'], 'to':['c','Weights']}]}
    return r,g

def test_registration_and_edges(tmp_path):
    r,g = setup()
    with pytest.raises(GraphError, match='Returns'):
        r.register(NodeType('feature.bad', {}, {'r':'Returns'}, {}, source))
    g['edges'][0]['to'] = ['c','Weights']
    with pytest.raises(GraphError, match='invalid edge'):
        r.normalize(g)

def test_incremental_restart_and_implementation(tmp_path):
    r,g = setup(); ledger = Ledger(); ctx = Context(ledger=ledger)
    e = Engine(r,tmp_path); e.run(g,context=ctx)
    g['nodes'][1]['params'] = {'factor':4}
    e.run(g,context=ctx)
    assert CALLS == {'source':1,'scale':2,'backtest':2}
    assert e.states['a']['status'] == 'cached'
    e = Engine(r,tmp_path); e.run(g,context=ctx)
    assert CALLS == {'source':1,'scale':2,'backtest':2}
    r.types['sizing.scale'].function = changed
    e.run(g,context=ctx)
    assert CALLS == {'source':1,'scale':3,'backtest':3}

def test_missing_preview_stale_and_cancel(tmp_path):
    r,g = setup(); e = Engine(r,tmp_path); ledger = Ledger(); ctx = Context(ledger=ledger)
    e.run(g,preview=True,context=ctx)
    assert 'backtest' not in CALLS and not ledger.seen
    e.run(g,context=ctx)
    old = copy.deepcopy(e.values['c'])
    assert e.invalidate(g,'b') == {'b','c'}
    assert e.states['c']['status'] == 'stale' and e.values['c'] == old
    g['edges'] = g['edges'][1:]
    e.run(g,context=ctx)
    assert e.states['b']['status'] == e.states['c']['status'] == 'not_ready'
    assert 'Score' in e.states['b']['message']
    token = CancelToken(); token.cancel()
    with pytest.raises(Cancelled): e.run(g,context=Context(token=token,ledger=ledger))
    assert len(ledger.seen) == 1

def test_ast_matches_triage(tmp_path):
    from scripts.triage_generated import code_fingerprint as triage
    p = tmp_path/'x.py'; p.write_text('def f():\n    "doc"\n    return 1 # hello\n')
    assert code_fingerprint(p) == triage(p)
    assert code_fingerprint(p) == code_fingerprint('def f():\n    "other"\n    return 1\n')
    assert code_fingerprint(p) != code_fingerprint('def f():\n    return 2\n')

def test_schema_cycles_and_parameter_validation():
    r,g = setup()
    g['nodes'][1]['params'] = {'factor': True}
    with pytest.raises(GraphError): r.normalize(g)
    g['nodes'][1]['params'] = {'factor': float('nan')}
    with pytest.raises(GraphError): r.normalize(g)
    g['nodes'][1]['params'] = {'n_trials': 1}
    with pytest.raises(GraphError): r.normalize(g)

def test_cancel_during_backtest_never_commits(tmp_path):
    def cancelled(inputs, params, ctx):
        ctx.token.cancel()
        return {'Returns': [1]}
    r,g = setup(); r.types['backtest.test'].function = cancelled
    ledger = Ledger(); e = Engine(r,tmp_path)
    with pytest.raises(Cancelled): e.run(g,context=Context(ledger=ledger))
    assert not ledger.seen
    assert e.states['c']['status'] == 'stale'

def test_cannot_cancel_after_successful_commit(tmp_path):
    r,g=setup(); ctx=Context(ledger=Ledger()); e=Engine(r,tmp_path)
    e.run(g,context=ctx)
    assert ctx.token.committed and not ctx.token.cancel()
    assert not ctx.token.cancelled

def test_multiple_backtests_cannot_hide_selection_trials():
    r,g = setup()
    g['nodes'].append({'id':'second','type':'backtest.test'})
    with pytest.raises(GraphError,match='one backtest'): r.normalize(g)

def test_unrecognized_metadata_is_not_embedded():
    r,g=setup(); g['credentials']={'value':'sensitive input'}
    with pytest.raises(GraphError,match='unsupported graph fields'): r.normalize(g)


def test_missing_ledger_rejects_before_backtest_execution(tmp_path):
    r,g=setup(); e=Engine(r,tmp_path)
    with pytest.raises(GraphError,match='before execution'): e.run(g)
    assert not CALLS
