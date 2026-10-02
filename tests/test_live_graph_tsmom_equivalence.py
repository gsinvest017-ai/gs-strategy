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
    sigma = nodes.volatility({**cont, **score}, {'vol_com': 60}, ctx)
    direction = nodes.direction(score, {'allow_short': True}, ctx)
    raw = nodes.vol_target({**direction, **sigma}, {'target_vol': .15}, ctx)
    weights = nodes.gross_cap(raw, {'max_gross_leverage': 1.5}, ctx)
    return weights


def assert_independent_futures_pnl(perf, config):
    """Reconcile raw contract prices and actual fills, independent of Zipline PnL."""
    from collections import defaultdict, deque
    from zipline.assets import Future
    from zipline.data.bundles import load

    capital = config['capital_base']
    delta = perf['portfolio_value'].diff()
    delta.iloc[0] = perf['portfolio_value'].iloc[0] - capital
    np.testing.assert_allclose(perf['pnl'], delta, atol=1e-7, rtol=0)
    gain = perf['portfolio_value'].iloc[-1] - capital
    assert abs(perf['pnl'].sum() - gain) < 1e-7

    bundle = load(config['bundle'])
    reader = bundle.equity_daily_bar_reader
    previous = {}
    last_close = {}
    lots = defaultdict(deque)
    trade_pnl = []
    overnight, intraday, fees = [], [], []
    for timestamp, row in perf.iterrows():
        session = timestamp.tz_convert('UTC').normalize()
        fills = row['transactions']
        assets = set(previous) | {fill['sid'] for fill in fills}
        on = day = commission = 0.0
        close = {}
        for asset in assets:
            assert isinstance(asset, Future), 'PnL check requires actual futures'
            opening = float(reader.get_value(asset.sid, session, 'open'))
            close[asset] = float(reader.get_value(asset.sid, session, 'close'))
            assert np.isfinite(opening) and np.isfinite(close[asset])
            quantity = previous.get(asset, 0)
            if quantity:
                on += quantity * asset.price_multiplier * (opening - last_close[asset])
                day += quantity * asset.price_multiplier * (close[asset] - opening)
        for fill in fills:
            asset, quantity, price = fill['sid'], fill['amount'], fill['price']
            multiplier = asset.price_multiplier
            day += quantity * multiplier * (close[asset] - price)
            # Zipline synthetic auto-close fills have no order and charge no
            # commission. Ordinary fills use the explicitly configured fee.
            fee = (abs(quantity) * config['params']['per_contract_cost'][asset.root_symbol]
                   if fill['order_id'] is not None else 0.0)
            commission += fee
            trade_pnl.append(-fee)
            remaining = quantity
            queue = lots[asset]
            while remaining and queue and np.sign(remaining) != np.sign(queue[0][0]):
                held, entry = queue[0]
                matched = min(abs(remaining), abs(held))
                trade_pnl.append(matched * np.sign(held) * multiplier * (price - entry))
                remaining += matched * np.sign(held)
                held -= matched * np.sign(held)
                if held:
                    queue[0] = (held, entry)
                else:
                    queue.popleft()
            if remaining:
                queue.append((remaining, price))
        previous = {position['sid']: position['amount'] for position in row['positions'] if position['amount']}
        fifo_positions = {asset: sum(q for q, _ in queue) for asset, queue in lots.items() if queue}
        assert fifo_positions == previous, 'fills must reconstruct reported inventory'
        last_close = close
        overnight.append(on)
        intraday.append(day)
        fees.append(commission)

    # Terminal MTM values open lots without fabricating a closing transaction.
    for asset, queue in lots.items():
        for quantity, entry in queue:
            trade_pnl.append(quantity * asset.price_multiplier * (last_close[asset] - entry))
    rebuilt = np.asarray(overnight) + np.asarray(intraday) - np.asarray(fees)
    np.testing.assert_allclose(rebuilt, perf['pnl'], atol=1e-7, rtol=0)
    assert abs(rebuilt.sum() - gain) < 1e-7
    assert abs(sum(trade_pnl) - gain) < 1e-7
    assert np.any(np.asarray(overnight) != 0), 'fixture must exercise overnight PnL'
    assert np.any(np.asarray(intraday) != 0), 'fixture must exercise intraday PnL'
    assert sum(fees) > 0, 'fixture must exercise commissions'


def compare_paths(bundle, start, end, tmp_path):
    from strategies._common.runner import run_strategy_from_config
    config = yaml.safe_load((HERE / 'config.yaml').read_text(encoding='utf8'))
    config.update(bundle=bundle, start=start, end=end)
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(config), encoding='utf8')
    old = run_strategy_from_config(HERE / 'strategy.py', path)
    assert_independent_futures_pnl(old, config)
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
    next(n for n in definition['nodes'] if n['id'] == 'facts')['params']['family'] = 'bounded_multiple'
    engine.run(definition, context=context)
    assert engine.states['backtest']['status'] == 'cached'
    assert ledger.summary()['selection_n'] == 1
    next(n for n in definition['nodes'] if n['id'] == 'facts')['params']['family'] = 'open_mining'

    np.testing.assert_allclose(old['returns'], graph['Returns'], atol=1e-10, rtol=0)

    def positions(series):
        return [{str(p['sid']): p['amount'] for p in row if p['amount']} for row in series]
    assert positions(old['positions']) == positions(graph['Positions'])
    assert any(len(row) for row in old['positions']), 'fixture must execute real positions'
    assert np.count_nonzero(old['returns']) > 100, 'fixture must exercise returns'
    # HTTP and CLI both use this service, with the same real cached fixture run.
    from strategies._common.graph.service import GraphService, restore_sidecar
    service = GraphService(tmp_path, registry=registry, cache_dir=tmp_path / 'cache', ledger_path=tmp_path / 'trials.jsonl')
    import copy
    from strategies._common.graph.service import write_json
    editable = copy.deepcopy(definition)
    next(n for n in editable['nodes'] if n['id'] == 'bars')['params']['data_version'] = 'auto'
    graph_path = tmp_path / 'strategies/tsmom_tx_mtx/graph.json'
    write_json(graph_path, registry.normalize(editable)[0])
    service.load('strategies/tsmom_tx_mtx/graph.json')
    before = graph_path.read_bytes()
    document = service.document()
    job = service.start()
    service._thread.join(timeout=60)
    assert service.jobs[job['id']]['status'] == 'complete', service.engine.states
    assert service.document() == document and not service.document()['dirty']
    assert graph_path.read_bytes() == before
    service.save()
    assert graph_path.read_bytes() == before
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
    capital['capital_base'] = config['capital_base']
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
        sigma = nodes.volatility({**cont, **score}, {'vol_com': 60}, Context())
        direction = nodes.direction(score, {'allow_short': True}, Context())
        raw = nodes.vol_target({**direction, **sigma}, {'target_vol': .15}, Context())
        return nodes.gross_cap(raw, {'max_gross_leverage': 1.5}, Context())['Weights']['values']
    original = calc(prices)
    changed = prices.copy()
    changed.iloc[351:] *= 7
    pd.testing.assert_frame_equal(original.iloc[:351], calc(changed).iloc[:351])


def test_sigma_preview_is_sizing_sigma_lookback_50_skip_5(fixture_bundle, monkeypatch):
    index = pd.bdate_range('2018-01-01', periods=300)
    frame = pd.DataFrame({'TX': np.exp(np.arange(300)*.002 + np.sin(np.arange(300))*.02)}, index=index)
    cont = {'ContinuousBars': {'source': {'history_days': 1024}, 'values': frame,
                              'histories': {dt: frame.loc[:dt] for dt in frame.index}}}
    score = nodes.momentum(cont, {'lookback': 50, 'skip': 5}, Context())
    original = nodes._sigma
    calls = []
    def once(histories, com, window):
        calls.append(window)
        return original(histories, com, window)
    monkeypatch.setattr(nodes, '_sigma', once)
    sigma = nodes.volatility({**cont, **score}, {'vol_com': 60}, Context())
    direction = nodes.direction(score, {'allow_short': True}, Context())
    raw = nodes.vol_target({**direction, **sigma}, {'target_vol': .15}, Context())['RawWeights']['values']
    expected = (direction['Direction']['values']*.15/sigma['Sigma']['values']).where(score['Score']['values'].notna())
    pd.testing.assert_frame_equal(raw, expected)
    assert calls == [60]
    inferred = (direction['Direction']['values']*.15/raw).dropna()
    pd.testing.assert_frame_equal(inferred, sigma['Sigma']['values'].loc[inferred.index], check_freq=False)
    legacy = nodes._legacy()._ewma_vol(np.diff(np.log(frame['TX'].tail(60))), 60)
    assert sigma['Sigma']['values'].iloc[-1, 0] == legacy
