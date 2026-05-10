"""Cubic-Momentum trend-and-crash strategy on TX continuous future.

Reference
---------
Naohiro Yoshida, "Dynamics of Periodic Bubbles and Crashes: Modeling Market
Overheating and Panic Selling via Cubic Momentum", arXiv:2605.00854 (2026).

Idea
----
Yoshida (2026) models price formation with two endogenous knobs:

    momentum_t      = sum_{i=1..L} (P_{t-i+1} - P_{t-i})              (signed)
    overheat_t      = momentum_t + alpha * cumulative_excess_volume   (Hawkes-like)

Trade direction is set by ``f(momentum_t) = a*momentum_t - b*momentum_t^3``,
i.e. trend-following for moderate momentum but **flips sign** above a critical
threshold (cubic term dominates -> "panic selling"). The threshold occurs at
|momentum_t| = sqrt(a / (3 * b)).

Translation to a tradeable rule on TX continuous future:

    1. Standardise momentum by its rolling stdev to make `a`, `b` regime-free
       (z = momentum / sigma).
    2. Long when 0 < z < z_crit; short when z > z_crit (cubic flip);
       symmetrical on the downside if `allow_short`.
    3. Position size in *contracts* scales with |f(z)| / |f(z_crit)|, capped at
       `max_contracts`.
"""
from __future__ import annotations

import os
import sys
from typing import Dict

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from _common.futures_setup import (
    apply_taiwan_futures_costs,
    make_roll_futures_handler,
)

from zipline.api import (
    continuous_future,
    date_rules,
    order_target,
    record,
    schedule_function,
    time_rules,
)


def _cubic_signal(z: float, z_crit: float) -> float:
    """Normalised cubic ``a*z - b*z^3`` so that the maximum is at ``z_crit``.

    Choose b such that f'(z_crit) = 0 -> a = 3 b z_crit^2. WLOG set a = 1, then
    b = 1 / (3 z_crit^2). Returns f(z) / f(z_crit) so the result is in
    approximately [-1, 1] for |z| <= sqrt(3) * z_crit.
    """
    if z_crit <= 0:
        return float(np.tanh(z))
    a = 1.0
    b = 1.0 / (3.0 * z_crit ** 2)
    f_z = a * z - b * z ** 3
    f_peak = a * z_crit - b * z_crit ** 3  # = (2/3) * z_crit
    return float(f_z / f_peak) if f_peak != 0 else 0.0


def initialize(context):
    p: Dict = getattr(context, "params", {})
    context.root_symbol = p.get("root_symbol", "TX")
    context.lookback = int(p.get("lookback", 20))
    context.sigma_window = int(p.get("sigma_window", 60))
    context.z_crit = float(p.get("z_crit", 1.5))
    context.max_contracts = int(p.get("max_contracts", 2))
    context.allow_short = bool(p.get("allow_short", True))

    apply_taiwan_futures_costs(
        per_contract_cost=p.get("per_contract_cost"),
        spread_points=p.get("spread_points"),
        benchmark=p.get("benchmark"),
    )

    context.cont = continuous_future(
        context.root_symbol, offset=0, roll="calendar", adjustment="add"
    )

    context._roll = make_roll_futures_handler(
        days_before_close=int(p.get("days_before_close", 10))
    )
    schedule_function(context._roll, date_rules.every_day(), time_rules.market_close())
    schedule_function(_evaluate, date_rules.every_day(), time_rules.market_close())


def _evaluate(context, data):
    cont = context.cont
    needed = max(context.lookback, context.sigma_window) + 5
    closes = data.history(cont, "close", needed, "1d").dropna().values
    if len(closes) < needed - 5:
        return

    diffs = np.diff(closes)
    if len(diffs) < context.sigma_window:
        return

    momentum = diffs[-context.lookback:].sum()
    sigma = diffs[-context.sigma_window:].std(ddof=1)
    if sigma <= 0 or not np.isfinite(sigma):
        return

    z = momentum / (sigma * np.sqrt(context.lookback))
    score = _cubic_signal(z, context.z_crit)

    target_size = int(round(score * context.max_contracts))
    if not context.allow_short:
        target_size = max(target_size, 0)
    target_size = max(-context.max_contracts, min(context.max_contracts, target_size))

    front = data.current(cont, "contract")
    if front is None:
        return

    pos = context.portfolio.positions.get(front)
    qty = pos.amount if pos else 0
    record(z=float(z), score=float(score), target=int(target_size))
    if target_size != qty:
        order_target(front, target_size)


def handle_data(context, data):
    return
