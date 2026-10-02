"""Replay frames: one row per trading day and one card per decision date.

The UI scrubs a single time axis.  For each day it shows price, the held
position, strategy and benchmark equity, and whether the day is contaminated
(inside the model's knowledge cutoff) or out of sample.  For each decision date
it shows exactly what the model saw (features + retrieved documents), what it
reasoned (CoT), what it decided, and what that decision earned until the next
decision.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _num(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _find(values, port):
    for node_id, outputs in values.items():
        if isinstance(outputs, dict) and port in outputs:
            return node_id, outputs[port]
    return None, None


def build(values):
    """``values``: engine.values ({node_id: {port: value}}) after a run or preview."""
    _, bars = _find(values, 'PriceBars')
    _, signals = _find(values, 'Signals')
    _, view = _find(values, 'MarketView')
    _, docs = _find(values, 'Docs')
    _, returns = _find(values, 'Returns')
    _, summary = _find(values, 'WalkForward')
    _, probe = _find(values, 'ProbeReport')
    if bars is None or signals is None:
        return {'available': False, 'reason': '請先執行預覽（需要 PriceBars 與 Signals）'}
    frame = bars['values']
    clean = pd.Timestamp(signals['clean_start'])
    oos = pd.Series(np.nan, index=frame.index)
    bench = pd.Series(np.nan, index=frame.index)
    position = pd.Series(np.nan, index=frame.index)
    folds = []
    if returns is not None and summary is not None:
        oos.loc[returns.index] = returns.to_numpy()
        bench.loc[summary['benchmark'].index] = summary['benchmark'].to_numpy()
        folds = [{k: (v.date().isoformat() if hasattr(v, 'date') else v) for k, v in f.items()}
                 for f in summary['folds']]
    _, positions = _find(values, 'Positions')
    if positions is not None:
        position.loc[positions.index] = positions.iloc[:, 0].to_numpy()
    equity = (1 + oos.fillna(0)).cumprod().where(oos.notna().cumsum() > 0)
    bench_equity = (1 + bench.fillna(0)).cumprod().where(bench.notna().cumsum() > 0)
    days = [{'date': d.date().isoformat(), 'settle': _num(frame.at[d, 'settle']),
             'contaminated': bool(d < clean), 'oos': bool(not math.isnan(oos.at[d])),
             'position': _num(position.at[d]), 'equity': _num(equity.at[d]),
             'benchmark': _num(bench_equity.at[d])} for d in frame.index]
    decision_index = list(signals['values'].index)
    cards = []
    for k, d in enumerate(decision_index):
        iso = d.date().isoformat()
        trace = signals['traces'].get(iso)
        nxt = decision_index[k + 1] if k + 1 < len(decision_index) else frame.index[-1]
        window = oos.loc[(oos.index > d) & (oos.index <= nxt)].dropna()
        cards.append({
            'date': iso, 'contaminated': bool(d < clean),
            'features': {c: _num(v) for c, v in (view['values'].loc[d].items() if view is not None else [])},
            'docs': (docs or {}).get('values', {}).get(iso, []),
            'called': trace is not None,
            'reasoning': trace['reasoning'] if trace else None,
            'content': trace['content'] if trace else None,
            'prompt': trace['prompt'] if trace else None,
            'decision': trace['decision'] if trace else None,
            'cached': trace['cached'] if trace else None,
            'period_return': _num((1 + window).prod() - 1) if len(window) else None,
        })
    return {'available': True, 'model': signals['model'], 'cutoff': signals['cutoff'],
            'cutoff_basis': signals.get('cutoff_basis', ''), 'clean_start': signals['clean_start'],
            'anonymize': signals.get('anonymize'), 'days': days, 'decisions': cards, 'folds': folds,
            'summary': ({k: v for k, v in summary.items() if k not in ('benchmark', 'folds')} if summary else None),
            'probe': probe}
