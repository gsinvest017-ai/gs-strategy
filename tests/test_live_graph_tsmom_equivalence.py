"""R8: real Zipline fixture equivalence; no mocked orders or accounting."""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from strategies._common.graph.core import Context, Registry, Engine, Cancelled
from strategies._common.graph.ledger import SelectionLedger
from strategies._common.graph.stat_nodes import register_nodes as register_stats
from strategies.tsmom_tx_mtx import graph_nodes as nodes

HERE = Path(__file__).parents[1] / 'strategies' / 'tsmom_tx_mtx'


@pytest.fixture(scope='module')
def fixture_bundle(tmp_path_factory):
    from strategies.tsmom_tx_mtx.fixture_bundle import register_fixture
    directory = tmp_path_factory.mktemp('zipline_fixture')
    previous = os.environ.get('ZIPLINE_ROOT')
    os.environ['ZIPLINE_ROOT'] = str(directory)
    name = register_fixture()
    from zipline.data.bundles import ingest
    ingest(name, show_progress=False)
    yield name
    if previous is None:
        os.environ.pop('ZIPLINE_ROOT', None)
    else:
        os.environ['ZIPLINE_ROOT'] = previous


def run_upstream(bundle, start, end):
    registry = Registry()
    nodes.register_nodes(registry)
    ctx = Context()
    data = registry.types['data.futures_bars'].parameters({'bundle': bundle, 'start': start, 'end': end, 'data_version': 'initial'})
    pinned = nodes.prepare_graph({'nodes': [{'type': 'data.futures_bars', 'params': data}]})
    data = pinned['nodes'][0]['params']
    bars = nodes.futures_bars({}, data, ctx)
    cont = nodes.continuous(bars, {}, ctx)
    score = nodes.momentum(cont, {'lookback': 252, 'skip': 21}, ctx)
    sigma = nodes.volatility(cont, {'vol_com': 60}, ctx)
    direction = nodes.direction(score, {'allow_short': True}, ctx)
    raw = nodes.vol_target({**direction, **sigma}, {'target_vol': .15}, ctx)
    weights = nodes.gross_cap(raw, {'max_gross_leverage': 1.5}, ctx)
    return weights


def compare_paths(bundle, start, end, tmp_path):
    from strategies._common.runner import run_strategy_from_config
    config = yaml.safe_load((HERE / 'config.yaml').read_text(encoding='utf8'))
    config.update(bundle=bundle, start=start, end=end)
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(config), encoding='utf8')
    old = run_strategy_from_config(HERE / 'strategy.py', path)
    registry = Registry()
    nodes.register_nodes(registry)
    register_stats(registry)
    definition = json.loads((HERE / 'graph.json').read_text(encoding='utf8'))
    next(n for n in definition['nodes'] if n['id'] == 'bars')['params'].update(bundle=bundle, start=start, end=end)
    definition = nodes.prepare_graph(definition)
    ledger = SelectionLedger(tmp_path / 'trials.jsonl')
    engine = Engine(registry, tmp_path / 'cache')
    context = Context(ledger=ledger)
    preview = engine.run(definition, preview=True, context=context)
    assert 'backtest' not in preview and ledger.summary()['selection_n'] == 0
    values = engine.run(definition, context=context)
    assert len(values) == 13, engine.states
    graph = values['backtest']
    weights = values['cap']
    assert ledger.summary()['selection_n'] == 1
    engine.run(definition, context=context)
    assert ledger.summary()['selection_n'] == 1
    assert engine.states['backtest']['status'] == 'cached'

    np.testing.assert_allclose(old['returns'], graph['Returns'], atol=1e-10, rtol=0)

    def positions(series):
        return [{str(p['sid']): p['amount'] for p in row if p['amount']} for row in series]
    assert positions(old['positions']) == positions(graph['Positions'])
    assert any(len(row) for row in old['positions']), 'fixture must execute real positions'
    assert np.count_nonzero(old['returns']) > 100, 'fixture must exercise returns'
    # HTTP and CLI both use this service, with the same real cached fixture run.
    from strategies._common.graph.service import GraphService, restore_sidecar
    service = GraphService(tmp_path, registry=registry, cache_dir=tmp_path / 'cache', ledger_path=tmp_path / 'trials.jsonl')
    service.set_graph(definition)
    job = service.start()
    service._thread.join(timeout=60)
    assert service.jobs[job['id']]['status'] == 'complete', service.engine.states
    sidecar = json.loads((tmp_path / service.jobs[job['id']]['sidecar']).read_text(encoding='utf8'))
    restored = restore_sidecar(sidecar, registry)
    assert restored['graph_hash'] == engine.identity(definition)[0]
    assert restored['warnings'] == []
    # Exercise the headless CLI entry with the same ingested futures fixture.
    from strategies._common.graph.__main__ import main
    from strategies._common.graph.service import write_json
    cli_graph = tmp_path / 'strategies/tsmom_tx_mtx/graph.json'
    write_json(cli_graph, definition)
    assert main(['run', '--root', str(tmp_path), '--ledger', str(tmp_path / 'trials.jsonl'),
                 '--cache-dir', str(tmp_path / 'cache')]) == 0
    assert ledger.summary()['selection_n'] == 1
    # Real cancellation inside Zipline must not append a selection record.
    capital = next(n for n in definition['nodes'] if n['id'] == 'backtest')['params']
    capital['capital_base'] = 9000000
    cancel_context = Context(ledger=ledger)
    cancel_context.progress = lambda event: cancel_context.token.cancel() if event.get('phase') == 'backtest' else None
    with pytest.raises(Cancelled):
        engine.run(definition, context=cancel_context)
    assert ledger.summary()['selection_n'] == 1
    # Alter only the wired sizing node: the actual event loop must now hold zero.
    next(n for n in definition['nodes'] if n['id'] == 'sizing')['params']['target_vol'] = 0
    zero = engine.run(definition, context=Context(ledger=ledger))['backtest']
    assert not any(positions(zero['Positions']))
    assert (zero['Returns'] == 0).all()
    assert ledger.summary()['selection_n'] == 2
    for node_id in ('bars', 'continuous', 'momentum', 'volatility', 'direction'):
        assert engine.states[node_id]['status'] == 'cached'
    assert engine.states['sizing']['status'] == 'recomputed'
    assert engine.states['cap']['status'] == 'recomputed'
    return weights


def test_r8_fixture_real_zipline_equivalence(fixture_bundle, tmp_path):
    compare_paths(fixture_bundle, '2018-01-02', '2020-12-31', tmp_path)


def test_r8_real_tquant_future_equivalence(tmp_path):
    if os.environ.get('GS_TEST_REAL_BUNDLE') != '1':
        pytest.skip('requires explicit GS_TEST_REAL_BUNDLE=1 and local tquant_future bundle/calendar access')
    if not os.environ.get('TEJAPI_KEY'):
        pytest.skip('TEJ credentials required for production calendar import')
    # Fresh process: the synthetic fixture's offline holiday import must never
    # contaminate the production calendar used for the real-bundle comparison.
    script = """
import runpy, sys
from pathlib import Path
from zipline.data.bundles import load
try:
    load('tquant_future')
except (ValueError, OSError):
    sys.exit(77)
test = runpy.run_path(sys.argv[1])
cfg = test['yaml'].safe_load((test['HERE'] / 'config.yaml').read_text(encoding='utf8'))
test['compare_paths']('tquant_future', cfg['start'], cfg['end'], Path(sys.argv[2]))
"""
    result = subprocess.run([sys.executable, '-c', script, __file__, str(tmp_path)], capture_output=True, timeout=600)
    if result.returncode == 77:
        pytest.skip('local tquant_future bundle unavailable')
    assert result.returncode == 0, 'isolated production-bundle equivalence failed; external output suppressed'


def test_data_version_is_pinned_and_changes_hash(fixture_bundle, tmp_path):
    from strategies._common.graph.core import GraphError
    registry = Registry()
    nodes.register_nodes(registry)
    definition = {'schema': 'live-strategy-graph/1', 'nodes': [
        {'id': 'bars', 'type': 'data.futures_bars', 'params': {'bundle': fixture_bundle}}], 'edges': []}
    pinned = nodes.prepare_graph(definition)
    version = pinned['nodes'][0]['params']['data_version']
    assert version not in ('auto', 'initial')
    assert nodes.prepare_graph(pinned) == pinned
    engine = Engine(registry, tmp_path / 'cache')
    before = engine.identity(pinned)[0]
    pinned['nodes'][0]['params']['data_version'] = '1900-01-01T00:00:00'
    assert engine.identity(pinned)[0] != before
    with pytest.raises(GraphError, match='unavailable'):
        nodes.prepare_graph(pinned)


@pytest.mark.parametrize('roots', [[], ['TX', 'TX'], ['UNKNOWN'], [None]])
def test_invalid_roots_rejected_before_data_access(roots):
    from strategies._common.graph.core import GraphError
    with pytest.raises(GraphError, match='roots'):
        nodes.futures_bars({}, {'roots': roots}, Context())


@pytest.mark.parametrize('value', [-1, float('inf'), float('nan'), '200', True])
def test_invalid_cost_rejected(value):
    from strategies._common.graph.core import GraphError
    with pytest.raises(GraphError, match='per_contract_cost'):
        nodes.costs({}, {'per_contract_cost': {'TX': value}}, Context())


def test_mixed_data_sources_rejected():
    from strategies._common.graph.core import GraphError
    with pytest.raises(GraphError, match='sources'):
        nodes.vol_target({'Direction': {'source': {'bundle': 'a'}},
                          'Sigma': {'source': {'bundle': 'b'}}}, {'target_vol': .15}, Context())


def test_r8_future_prices_do_not_change_past_weights(fixture_bundle):
    index = pd.date_range('2016-01-01', periods=450, freq='B', tz='UTC')
    prices = pd.DataFrame({'TX': 10000 * np.exp(np.arange(450) * .001 + np.sin(np.arange(450)) * .01),
                           'MTX': 10000 * np.exp(np.arange(450) * .001 + np.cos(np.arange(450)) * .01)}, index=index)

    def calc(frame):
        cont = {'ContinuousBars': {'source': {'history_days': 1024}, 'values': frame,
                                  'histories': {dt: frame.loc[:dt] for dt in frame.index}}}
        score = nodes.momentum(cont, {'lookback': 252, 'skip': 21}, Context())
        sigma = nodes.volatility(cont, {'vol_com': 60}, Context())
        direction = nodes.direction(score, {'allow_short': True}, Context())
        raw = nodes.vol_target({**direction, **sigma}, {'target_vol': .15}, Context())
        return nodes.gross_cap(raw, {'max_gross_leverage': 1.5}, Context())['Weights']['values']
    original = calc(prices)
    changed = prices.copy()
    changed.iloc[351:] *= 7
    pd.testing.assert_frame_equal(original.iloc[:351], calc(changed).iloc[:351])
