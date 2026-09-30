"""TSMOM graph nodes: as-of continuous histories and real Zipline execution."""
from __future__ import annotations

import builtins
import copy
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd

from strategies._common.graph.core import GraphError, NodeType

HERE = Path(__file__).parent


def prepare_graph(graph):
    """Pin every data source to an immutable, existing bundle ingestion."""
    from zipline.data.bundles.core import ingestions_for_bundle
    graph = copy.deepcopy(graph)
    for node in graph['nodes']:
        if node['type'] != 'data.futures_bars':
            continue
        params = node.setdefault('params', {})
        versions = ingestions_for_bundle(params.get('bundle', 'tquant_future'))
        if not versions:
            raise GraphError('bundle has no ingestions')
        version = params.get('data_version', 'initial')
        if version in ('initial', 'auto'):
            params['data_version'] = versions[0].isoformat()
        else:
            matched = next((v for v in versions if v.tz_localize(None) == pd.Timestamp(version).tz_localize(None)), None)
            if matched is None:
                raise GraphError('pinned bundle ingestion is unavailable')
            params['data_version'] = matched.isoformat()
    return graph


def _legacy():
    # Fresh source compilation bypasses both sys.modules and timestamp-based pyc.
    # A private import namespace avoids mutating imports used by other workers.
    modules = {}
    def local_import(name, globals=None, locals=None, fromlist=(), level=0):
        path = HERE / (name + '.py')
        if level == 0 and '.' not in name and path.is_file():
            return load(name, path)
        return builtins.__import__(name, globals, locals, fromlist, level)
    def load(name, path):
        if name not in modules:
            module = ModuleType('_tsmom_graph_' + name)
            modules[name] = module
            module.__file__ = str(path)
            module.__dict__['__builtins__'] = dict(vars(builtins), __import__=local_import)
            exec(compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec'), module.__dict__)
        return modules[name]
    return load('strategy', HERE / 'strategy.py')


def _portal(p):
    from zipline.data import bundles
    from zipline.data.data_portal import DataPortal
    from zipline.utils.calendar_utils import get_calendar
    from zipline.data.bundles.core import ingestions_for_bundle
    version = p['data_version']
    if version in ('initial', 'auto'):
        raise GraphError('pin data_version with prepare_graph before execution')
    timestamp = pd.Timestamp(version)
    if timestamp.tz_localize(None) not in [v.tz_localize(None) for v in ingestions_for_bundle(p['bundle'])]:
        raise GraphError('pinned bundle ingestion is unavailable')
    bundle = bundles.load(p['bundle'], timestamp=timestamp)
    calendar = get_calendar(p['calendar'])
    reader = bundle.equity_daily_bar_reader
    portal = DataPortal(bundle.asset_finder, calendar, reader.first_trading_day,
                        equity_daily_reader=reader, future_daily_reader=reader,
                        adjustment_reader=bundle.adjustment_reader)
    assets = [bundle.asset_finder.create_continuous_future(r, 0, 'calendar', 'add') for r in p['roots']]
    return portal, calendar, assets, reader


def futures_bars(inputs, p, ctx):
    roots = p['roots']
    if not roots or any(not isinstance(r, str) or r not in ('TX', 'MTX', 'TE', 'TF') for r in roots) or len(set(roots)) != len(roots):
        raise GraphError('roots must be a nonempty unique supported futures list')
    portal, calendar, assets, reader = _portal(p)
    sessions = calendar.sessions_in_range(pd.Timestamp(p['start'], tz='UTC'), pd.Timestamp(p['end'], tz='UTC'))
    rows = []
    for dt in sessions:
        ctx.check_cancelled()
        rows.append(portal.get_history_window(assets, dt, 1, '1d', 'close', 'daily').iloc[-1].to_numpy())
    return {'Bars': {'source': dict(p), 'values': pd.DataFrame(rows, index=sessions, columns=p['roots'])}}


def continuous(inputs, p, ctx):
    bars = inputs['Bars']
    source = bars['source']
    portal, calendar, assets, reader = _portal(source)
    histories = {}
    for dt in bars['values'].index:
        ctx.check_cancelled()
        count = min(source['history_days'], len(calendar.sessions_in_range(reader.first_trading_day, dt)))
        frame = portal.get_history_window(assets, dt, count, '1d', 'close', 'daily')
        frame.columns = source['roots']
        histories[dt] = frame
    return {'ContinuousBars': {'source': source, 'values': bars['values'], 'histories': histories}}


def momentum(inputs, p, ctx):
    data = inputs['ContinuousBars']
    need = p['lookback'] + p['skip'] + 5
    if need > data['source']['history_days']:
        raise GraphError('data history_days must cover lookback + skip + 5')
    fn = _legacy()._signed_momentum
    values = pd.DataFrame(index=data['values'].index, columns=data['values'].columns, dtype=float)
    for dt, history in data['histories'].items():
        for root in values.columns:
            closes = history[root].tail(need).dropna().to_numpy()
            if len(closes) >= need - 5:
                values.loc[dt, root] = fn(closes, p['lookback'], p['skip'])
    return {'Score': {'source': data['source'], 'values': values, 'window': need}}


def volatility(inputs, p, ctx):
    data = inputs['ContinuousBars']
    score = inputs['Score']
    if data['source'] != score['source']:
        raise GraphError('Score and volatility data sources must match')
    return {'Sigma': {'source': data['source'], 'window': score['window'],
                      'values': _sigma(data['histories'], p['vol_com'], score['window'])}}


def _sigma(histories, com, window):
    fn = _legacy()._ewma_vol
    rows = {}
    for dt, history in histories.items():
        rows[dt] = {r: fn(np.diff(np.log(history[r].tail(window).dropna().to_numpy()))[-com * 4:], com)
                    for r in history.columns}
    return pd.DataFrame.from_dict(rows, orient='index')


def direction(inputs, p, ctx):
    score = inputs['Score']
    values = np.sign(score['values'])
    if not p['allow_short']:
        values = values.clip(lower=0)
    return {'Direction': {**score, 'values': values}}


def vol_target(inputs, p, ctx):
    d, s = inputs['Direction'], inputs['Sigma']
    if d['source'] != s['source']:
        raise GraphError('Direction and Sigma data sources must match')
    if d['window'] != s['window']:
        raise GraphError('Direction and Sigma history windows must match')
    sigma = s['values']
    valid = (sigma > 0) & d['values'].notna()
    raw = (d['values'] * p['target_vol'] / sigma).where(valid)
    weights = raw.div(valid.sum(axis=1).clip(lower=1), axis=0)
    return {'RawWeights': {'source': d['source'], 'values': weights}}


def gross_cap(inputs, p, ctx):
    raw = inputs['RawWeights']
    values = raw['values']
    scale = (p['max_gross_leverage'] / values.abs().sum(axis=1)).clip(upper=1)
    return {'Weights': {**raw, 'values': values.mul(scale, axis=0)}}


def costs(inputs, p, ctx):
    if any(not isinstance(v, (float, int)) or isinstance(v, bool) or not np.isfinite(v) or v < 0
           for v in p['per_contract_cost'].values()):
        raise GraphError('per_contract_cost values must be finite and nonnegative')
    return {'CostModel': dict(p)}


def backtest(inputs, p, ctx):
    from zipline import run_algorithm
    from zipline.api import date_rules, time_rules, schedule_function, order_target, record
    from zipline.utils.calendar_utils import get_calendar
    legacy = _legacy()
    weights = inputs['Weights']
    source = weights['source']
    calendar = get_calendar(p['calendar'])
    sessions = calendar.sessions_in_range(pd.Timestamp(source['start'], tz='UTC'), pd.Timestamp(source['end'], tz='UTC'))
    if p['calendar'] != source['calendar']:
        raise GraphError('backtest and data calendars must match')

    def rebalance(context, data):
        ctx.check_cancelled()
        dt = data.current_session
        if dt not in weights['values'].index:
            raise GraphError('Weights do not cover execution session')
        for root, weight in weights['values'].loc[dt].dropna().items():
            front = data.current(context.cont_by_root[root], 'contract')
            if front is None:
                continue
            price = float(data.current(front, 'close'))
            if not np.isfinite(price) or price <= 0:
                continue
            quantity = int(round(weight * context.portfolio.portfolio_value / (price * legacy.POINT_VALUE.get(root, 200))))
            record(**{f'w_{root}': weight, f'n_{root}': quantity})
            held = context.portfolio.positions.get(front)
            if quantity != (held.amount if held else 0):
                order_target(front, quantity)

    def initialize(context):
        legacy.apply_taiwan_futures_costs(**inputs['CostModel'])
        context.cont_by_root = dict(zip(source['roots'], legacy.make_continuous_taiwan_futures(source['roots'])))
        schedule_function(legacy.make_roll_futures_handler(p['days_before_close']), date_rules.every_day(), time_rules.market_close())
        schedule_function(rebalance, date_rules.month_start(), time_rules.market_close())
        context.graph_bars = 0

    def handle_data(context, data):
        ctx.check_cancelled()
        context.graph_bars += 1
        ctx.progress({'phase': 'backtest', 'completed': context.graph_bars, 'total': len(sessions)})

    perf = run_algorithm(start=sessions[0], end=sessions[-1], initialize=initialize,
                         handle_data=handle_data, capital_base=p['capital_base'],
                         bundle=source['bundle'], bundle_timestamp=pd.Timestamp(source['data_version']),
                         trading_calendar=calendar, data_frequency='daily')
    ctx.check_cancelled()
    return {'Returns': perf['returns'], 'Positions': perf['positions']}


def register_nodes(registry):
    def param(kind, default, **extra):
        return {'type': kind, 'default': default, **extra}
    specs = [
        ('data.futures_bars', [], ['Bars'], {'bundle': param('string', 'tquant_future'), 'roots': param('array', ['TX', 'MTX']), 'start': param('string', '2018-01-01'), 'end': param('string', '2026-04-30'), 'calendar': param('string', 'TEJ_morning_future'), 'data_version': param('string', 'initial'), 'history_days': param('integer', 1024, minimum=5)}, futures_bars),
        ('data.continuous', ['Bars'], ['ContinuousBars'], {}, continuous),
        ('feature.signed_momentum', ['ContinuousBars'], ['Score'], {'lookback': param('integer', 252, minimum=1), 'skip': param('integer', 21, minimum=0)}, momentum),
        ('feature.ewma_vol', ['ContinuousBars', 'Score'], ['Sigma'], {'vol_com': param('integer', 60, minimum=1)}, volatility),
        ('signal.direction', ['Score'], ['Direction'], {'allow_short': param('boolean', True)}, direction),
        ('sizing.vol_target', ['Direction', 'Sigma'], ['RawWeights'], {'target_vol': param('number', .15, minimum=0)}, vol_target),
        ('sizing.gross_cap', ['RawWeights'], ['Weights'], {'max_gross_leverage': param('number', 1.5, minimum=0)}, gross_cap),
        ('cost.futures', [], ['CostModel'], {'per_contract_cost': param('object', {'TX': 200, 'MTX': 100}), 'spread_points': param('number', 6., minimum=0)}, costs),
        ('backtest.zipline', ['Weights', 'CostModel'], ['Returns', 'Positions'], {'capital_base': param('number', 10000000, minimum=1), 'calendar': param('string', 'TEJ_morning_future'), 'days_before_close': param('integer', 10, minimum=0)}, backtest),
    ]
    dependencies = {
        'data.futures_bars': (_portal,), 'data.continuous': (_portal,),
        'feature.signed_momentum': (_legacy, HERE / 'strategy.py'),
        'feature.ewma_vol': (_sigma, _legacy, HERE / 'strategy.py'),
        'backtest.zipline': (_legacy, HERE / 'strategy.py', HERE / 'futures_setup.py'),
    }
    for name, ins, outs, params, fn in specs:
        registry.register(NodeType(name, {x: x for x in ins}, {x: x for x in outs}, params, fn,
                                   dependencies=dependencies.get(name, ())))
