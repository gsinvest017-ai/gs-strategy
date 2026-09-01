"""Auto-generated MEAN-REVERSION skeleton bundle.

Source paper: Trends, Volatility, Correlations, and Critical Phenomena in Financial Markets
              http://arxiv.org/abs/2606.20145v1

DO NOT TRADE AS-IS. Skeleton produced by ``quant_crawler.strategy_gen``;
``_compute_oscillator`` returns 50 (the neutral midpoint), so the strategy
never crosses the 30/70 thresholds and never opens a position. A human
must replace ``_compute_oscillator`` with the paper's specific indicator
(RSI, z-score, cointegration spread, etc.) and then flip
``manifest.requires_review`` to ``false``.
"""
from __future__ import annotations

import numpy as np

from futures_setup import (
    apply_taiwan_futures_costs,
    make_continuous_taiwan_futures,
    make_roll_futures_handler,
)
from zipline.api import (
    date_rules,
    order_target,
    record,
    schedule_function,
    time_rules,
)


def _compute_oscillator(prices: np.ndarray, window: int) -> float:
    """SKELETON: returns 50 (neutral) until a human fills in the indicator.

    Replace with e.g. RSI:
        diffs  = np.diff(prices)
        up     = diffs.clip(min=0).mean()
        down   = (-diffs).clip(min=0).mean()
        return 100 * up / (up + down) if (up + down) > 0 else 50.0
    """
    return 50.0


def initialize(context):
    p = context.params
    context.root = str(p.get("root_symbol", "TX"))
    context.window = int(p.get("window", 14))
    context.upper = float(p.get("upper_threshold", 70.0))
    context.lower = float(p.get("lower_threshold", 30.0))
    context.allow_short = bool(p.get("allow_short", True))
    context.position_contracts = int(p.get("position_contracts", 1))
    days_before_close = int(p.get("days_before_close", 10))

    apply_taiwan_futures_costs(
        per_contract_cost=p.get("per_contract_cost"),
        spread_points=p.get("spread_points"),
    )
    [context.cont] = make_continuous_taiwan_futures([context.root])
    schedule_function(
        make_roll_futures_handler(days_before_close=days_before_close),
        date_rules.every_day(),
        time_rules.market_close(minutes=30),
    )


def handle_data(context, data):
    need = context.window + 1
    history = data.history(context.cont, "close", need, "1d")
    if history.isna().any() or len(history) < need:
        return
    prices = history.values
    osc = _compute_oscillator(prices, context.window)
    if osc <= context.lower:
        target = context.position_contracts
    elif osc >= context.upper:
        target = -context.position_contracts if context.allow_short else 0
    else:
        target = 0
    front = data.current(context.cont, "contract")
    if front is not None:
        order_target(front, target)
    record(oscillator=osc, target_contracts=target)
