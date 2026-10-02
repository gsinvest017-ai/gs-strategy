"""Walk-forward evaluation as a higher-order operator.

``walk_forward(signals, policy, grid, folds)`` takes a *family* of policies
``policy(theta): Signals -> Positions`` and returns one out-of-sample return
series: in every fold ``theta`` is chosen on the in-sample window only and then
applied to the next, unseen window.  Nested selection is part of the procedure,
so the whole procedure counts as **one** selection trial in the ledger; the
grid only changes N when the grid itself changes (a different backtest key).

The engine is a research-grade vector simulator for one futures root:
positions decided at the close of day *t* earn the contract's own return on
*t+1* (``roi`` from QUANTDATA is settle-to-settle on the same contract, so rolls
do not create price jumps), and turnover pays a fee plus slippage per contract.
It is not the Zipline event loop; equivalence with Zipline is not claimed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies._common.graph.core import GraphError

TRADING_DAYS = 252


def folds(index, *, train_days, test_days, embargo_days=1, scheme='anchored'):
    """Contiguous (train, test) position ranges over ``index``; test windows never overlap."""
    n = len(index)
    if train_days < 1 or test_days < 1 or embargo_days < 0:
        raise GraphError('walk-forward window lengths must be positive')
    out = []
    test_start = train_days + embargo_days
    while test_start < n:
        test_end = min(n, test_start + test_days)
        train_end = test_start - embargo_days
        train_start = 0 if scheme == 'anchored' else max(0, train_end - train_days)
        out.append({'train': (train_start, train_end), 'test': (test_start, test_end)})
        test_start = test_end
    return out


def threshold_policy(signals, threshold, exposure):
    """Direction where confidence clears ``threshold``, flat otherwise."""
    direction = signals['direction'].astype(float)
    confidence = signals['confidence'].astype(float)
    return (direction.where(confidence >= threshold, 0.0) * exposure).fillna(0.0)


def simulate(weights, bars, *, capital_base, point_value, fee_per_contract, slippage_points,
             round_contracts=True):
    """Daily vector backtest: weights at close t, return earned on t+1."""
    price = bars['settle'].where(bars['settle'] > 0, bars['close'])
    held = weights.reindex(bars.index).ffill().fillna(0.0)
    if round_contracts:
        contracts = np.round(held * capital_base / (price * point_value))
        held = contracts * price * point_value / capital_base
    turnover = held.diff().abs().fillna(held.abs())
    cost_rate = (fee_per_contract + slippage_points * point_value) / (price * point_value)
    gross = held.shift(1).fillna(0.0) * bars['ret']
    # A trade placed at the close of t is paid on t+1, alongside the return it buys.
    cost = (turnover * cost_rate).shift(1).fillna(0.0)
    return gross - cost, held


def sharpe(returns):
    r = pd.Series(returns).dropna()
    if len(r) < 2 or float(r.std(ddof=1)) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(TRADING_DAYS))


def run(signals, bars, *, grid, exposure, train_days, test_days, embargo_days, scheme,
        sim, clean_start=None):
    """Nested walk-forward over decision-date ``signals`` and daily ``bars``.

    Only trading days on or after ``clean_start`` take part; the first
    ``train_days`` of them are in-sample for the first fold.
    """
    days = bars.index if clean_start is None else bars.index[bars.index >= clean_start]
    plan = folds(days, train_days=train_days, test_days=test_days, embargo_days=embargo_days, scheme=scheme)
    if not plan:
        raise GraphError('乾淨樣本不足以切出任何 walk-forward 區段')
    candidates = {}
    for theta in grid:
        weights = threshold_policy(signals, theta, exposure)
        candidates[theta] = simulate(weights, bars, **sim)
    returns = []
    positions = []
    table = []
    for k, fold in enumerate(plan):
        tr = days[fold['train'][0]:fold['train'][1]]
        te = days[fold['test'][0]:fold['test'][1]]
        scores = {theta: sharpe(candidates[theta][0].loc[tr]) for theta in grid}
        chosen = max(grid, key=lambda theta: (scores[theta], -grid.index(theta)))
        oos, held = candidates[chosen]
        returns.append(oos.loc[te])
        positions.append(held.loc[te])
        table.append({'fold': k, 'train_start': tr[0], 'train_end': tr[-1], 'test_start': te[0],
                      'test_end': te[-1], 'is_sharpe': {str(t): s for t, s in scores.items()},
                      'chosen_threshold': chosen, 'oos_sharpe': sharpe(oos.loc[te]),
                      'oos_return': float((1 + oos.loc[te]).prod() - 1)})
    oos_returns = pd.concat(returns)
    oos_returns.name = 'returns'
    return oos_returns, pd.concat(positions), table
