"""Volatility-targeted time-series momentum on TX & MTX continuous futures.

Reference
---------
- Wiley JFM fut.70093, "Curve Momentum in China" (2026, EarlyView).
- Moskowitz, Ooi, Pedersen, "Time-series momentum", JFE (2012).
- Hurst, Ooi, Pedersen, "A Century of Evidence on Trend-Following Investing",
  AQR (2017).

Idea
----
For each tradeable contract:

    sign_t   = sign( cumulative log return over `lookback` days,
                     skipping the most recent `skip` days )
    sigma_t  = exponentially-weighted vol of daily log returns
    weight_t = sign_t * (target_vol / sigma_t) / N_assets

Position sizing in *contracts*: weight_t * portfolio_value / (price * multiplier).

We adopt the canonical 12-1 lookback (252 / skip 21) for index futures, but
expose `lookback` and `skip` so the user can run 6-1, 3-1, etc.
"""
from __future__ import annotations

from typing import Dict, List

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


# Multipliers (NTD per index point) for Taiwan futures roots.
POINT_VALUE = {
    "TX": 200,
    "MTX": 50,
    "TE": 4000,
    "TF": 1000,
}


def _signed_momentum(closes: np.ndarray, lookback: int, skip: int) -> float:
    """log(P_{t-skip}) - log(P_{t-skip-lookback})."""
    if len(closes) < lookback + skip + 1:
        return 0.0
    end = closes[-skip - 1] if skip > 0 else closes[-1]
    start = closes[-skip - 1 - lookback]
    if start <= 0 or end <= 0:
        return 0.0
    return float(np.log(end) - np.log(start))


def _ewma_vol(log_returns: np.ndarray, com: int) -> float:
    """Exponentially-weighted std of daily returns (annualised)."""
    if len(log_returns) < 2:
        return 0.0
    w = np.exp(-np.arange(len(log_returns))[::-1] / com)
    w /= w.sum()
    mu = float((w * log_returns).sum())
    var = float((w * (log_returns - mu) ** 2).sum())
    return float(np.sqrt(max(var, 0.0) * 252.0))


def initialize(context):
    p: Dict = getattr(context, "params", {})
    context.roots: List[str] = list(p.get("roots", ["TX", "MTX"]))
    context.lookback = int(p.get("lookback", 252))
    context.skip = int(p.get("skip", 21))
    context.vol_com = int(p.get("vol_com", 60))
    context.target_vol = float(p.get("target_vol", 0.15))   # 15% annual
    context.max_gross_leverage = float(p.get("max_gross_leverage", 1.5))
    context.allow_short = bool(p.get("allow_short", True))

    apply_taiwan_futures_costs(
        per_contract_cost=p.get("per_contract_cost"),
        spread_points=p.get("spread_points"),
        benchmark=p.get("benchmark"),
    )

    context.continuous = make_continuous_taiwan_futures(context.roots)
    context.cont_by_root = dict(zip(context.roots, context.continuous))

    context._roll = make_roll_futures_handler(
        days_before_close=int(p.get("days_before_close", 10))
    )
    schedule_function(context._roll, date_rules.every_day(), time_rules.market_close())
    schedule_function(_rebalance, date_rules.month_start(), time_rules.market_close())


def _rebalance(context, data):
    n_needed = context.lookback + context.skip + 5
    log_returns_by_root: Dict[str, np.ndarray] = {}
    closes_by_root: Dict[str, np.ndarray] = {}
    for root, cont in context.cont_by_root.items():
        closes = data.history(cont, "close", n_needed, "1d").dropna().values
        if len(closes) < n_needed - 5:
            continue
        closes_by_root[root] = closes
        log_returns_by_root[root] = np.diff(np.log(closes))

    if not closes_by_root:
        return

    raw_weights = {}
    for root, closes in closes_by_root.items():
        mom = _signed_momentum(closes, context.lookback, context.skip)
        sign = np.sign(mom)
        if not context.allow_short and sign < 0:
            sign = 0
        sigma = _ewma_vol(log_returns_by_root[root][-context.vol_com * 4:], context.vol_com)
        if sigma <= 0:
            continue
        raw_weights[root] = float(sign) * (context.target_vol / sigma)

    if not raw_weights:
        return

    n_assets = max(len(raw_weights), 1)
    norm_weights = {r: w / n_assets for r, w in raw_weights.items()}

    gross = sum(abs(w) for w in norm_weights.values())
    if gross > context.max_gross_leverage and gross > 0:
        scale = context.max_gross_leverage / gross
        norm_weights = {r: w * scale for r, w in norm_weights.items()}

    portfolio_value = context.portfolio.portfolio_value
    for root, w in norm_weights.items():
        cont = context.cont_by_root[root]
        front = data.current(cont, "contract")
        if front is None:
            continue
        price = float(data.current(front, "close"))
        if not np.isfinite(price) or price <= 0:
            continue
        notional_per_contract = price * POINT_VALUE.get(root, 200)
        if notional_per_contract <= 0:
            continue
        n_contracts = int(round(w * portfolio_value / notional_per_contract))
        record(**{f"w_{root}": w, f"n_{root}": n_contracts})

        pos = context.portfolio.positions.get(front)
        qty = pos.amount if pos else 0
        if n_contracts != qty:
            order_target(front, n_contracts)


def handle_data(context, data):
    return
