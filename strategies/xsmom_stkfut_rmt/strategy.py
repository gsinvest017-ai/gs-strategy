"""Cross-sectional momentum on Taiwan single-stock futures, gated by an RMT
"complexity gap" market-regime filter.

References
----------
- Mukhia, Ansari et al., "Structural Dynamics of G5 Stock Markets During
  Exogenous Shocks: A Random Matrix Theory-Based Complexity Gap Approach",
  arXiv:2604.19107 (2026).
- Jegadeesh & Titman (1993), classic cross-sectional momentum.
- Asness, Moskowitz, Pedersen (2013), value & momentum everywhere.

Idea
----
1. Universe: individual stock futures (FFF, DFF, JFF, ...) returned by TEJ's
   ``get_stock_futures_universe`` helper. We use their continuous front-month
   contracts.

2. Cross-sectional 6-1 momentum:
        score_i = log(P_{i, t-21}) - log(P_{i, t-21-126})
   Long top decile, short bottom decile (equal-weight inside each leg), held
   for one month, monthly rebalanced.

3. Regime filter (Mukhia et al. 2026):
        rolling correlation matrix C of universe daily returns over `rmt_window`
        lambda_max  = largest eigenvalue of C, normalised by N
        rho_avg     = mean off-diagonal correlation
        complexity_gap = lambda_max - rho_avg
   Paper finding: gap collapses near zero during exogenous shocks (panic
   synchronisation) and is positive during structurally rich regimes. We use:
        gap > rmt_threshold        -> full position
        gap in [low, threshold]    -> half position
        gap <= rmt_low_threshold   -> de-risk to zero

4. Hedge with TX continuous future: keep cross-section beta neutral by short
   TX equal in notional to net long stock-fut book minus net short.
"""
from __future__ import annotations

import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

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
    order_target_percent,
    record,
    schedule_function,
    time_rules,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_log_return(closes: np.ndarray) -> np.ndarray:
    pos = closes[closes > 0]
    if len(pos) < 2:
        return np.array([])
    return np.diff(np.log(pos))


def _complexity_gap(returns_matrix: np.ndarray) -> float:
    """Compute the RMT complexity gap from a (T, N) matrix of returns.

    gap = lambda_max(C) / N - mean(off-diagonal C)

    where C is the Pearson correlation matrix of the columns. The
    normalisation by N keeps `lambda_max` comparable across universe sizes.
    """
    if returns_matrix.ndim != 2:
        return float("nan")
    T, N = returns_matrix.shape
    if T < 30 or N < 5:
        return float("nan")

    valid = ~np.any(~np.isfinite(returns_matrix), axis=0)
    R = returns_matrix[:, valid]
    if R.shape[1] < 5:
        return float("nan")

    # Standardise each column
    means = R.mean(axis=0, keepdims=True)
    stds = R.std(axis=0, ddof=1, keepdims=True)
    stds[stds == 0] = 1.0
    Z = (R - means) / stds
    C = (Z.T @ Z) / max(R.shape[0] - 1, 1)
    n = C.shape[0]

    eigenvalues = np.linalg.eigvalsh(C)
    lam_max = float(eigenvalues[-1])

    if n > 1:
        off_mask = ~np.eye(n, dtype=bool)
        rho_avg = float(C[off_mask].mean())
    else:
        rho_avg = 0.0

    return float(lam_max / n - rho_avg)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def initialize(context):
    p: Dict = getattr(context, "params", {})
    context.lookback = int(p.get("lookback", 126))
    context.skip = int(p.get("skip", 21))
    context.long_decile = float(p.get("long_decile", 0.1))
    context.short_decile = float(p.get("short_decile", 0.1))
    context.gross_target = float(p.get("gross_target", 1.0))
    context.rmt_window = int(p.get("rmt_window", 60))
    context.rmt_threshold = float(p.get("rmt_threshold", 0.20))
    context.rmt_low_threshold = float(p.get("rmt_low_threshold", 0.05))
    context.min_universe = int(p.get("min_universe", 20))
    context.hedge_with_tx = bool(p.get("hedge_with_tx", True))
    # M11 ablation flag: when True, long the bottom decile and short the top
    # decile (i.e. trade short-horizon reversal instead of momentum).
    context.reverse_momentum = bool(p.get("reverse_momentum", False))
    # M12 ablation flag: when True, drop the short leg entirely. Taiwan stock
    # futures shorts have higher margin + borrowing cost than longs in practice.
    context.long_only = bool(p.get("long_only", False))

    apply_taiwan_futures_costs(
        per_contract_cost=p.get("per_contract_cost"),
        spread_points=p.get("spread_points"),
        benchmark=p.get("benchmark"),
    )

    # Resolve universe lazily — need the TEJ helper if available; otherwise
    # fall back to a user-provided list in the YAML.
    universe_roots = p.get("universe_roots")
    if not universe_roots:
        try:
            from zipline.TQresearch.futures_package import get_stock_futures_universe  # type: ignore
            start = p.get("universe_start", "2020-01-01")
            end = p.get("universe_end", str(pd.Timestamp.now().date()))
            _, fut_universe = get_stock_futures_universe(st=start, et=end)
            universe_roots = list(fut_universe)
        except Exception:
            universe_roots = []
    context.universe_roots = list(universe_roots)

    context.continuous = [
        continuous_future(rs, offset=0, roll="calendar", adjustment="add")
        for rs in context.universe_roots
    ]

    if context.hedge_with_tx:
        context.tx_cont = continuous_future(
            "TX", offset=0, roll="calendar", adjustment="add"
        )

    context._roll = make_roll_futures_handler(
        days_before_close=int(p.get("days_before_close", 10))
    )
    schedule_function(context._roll, date_rules.every_day(), time_rules.market_close())
    schedule_function(_rebalance, date_rules.month_start(), time_rules.market_close())


def _scale_from_gap(gap: float, ctx) -> float:
    if not np.isfinite(gap):
        return 0.0
    if gap >= ctx.rmt_threshold:
        return 1.0
    if gap >= ctx.rmt_low_threshold:
        return 0.5
    return 0.0


def _rebalance(context, data):
    needed = max(context.lookback + context.skip + 5, context.rmt_window + 5)
    rows: List[np.ndarray] = []
    momentum_scores: Dict[str, float] = {}
    last_prices: Dict[str, float] = {}

    for root, cont in zip(context.universe_roots, context.continuous):
        try:
            closes = data.history(cont, "close", needed, "1d").dropna().values
        except Exception:
            continue
        if len(closes) < context.lookback + context.skip + 1:
            continue
        end_idx = -context.skip - 1 if context.skip > 0 else -1
        start_idx = end_idx - context.lookback
        end_p = closes[end_idx]
        start_p = closes[start_idx]
        if start_p <= 0 or end_p <= 0:
            continue
        momentum_scores[root] = float(np.log(end_p) - np.log(start_p))
        last_prices[root] = float(closes[-1])

        ret = _safe_log_return(closes[-context.rmt_window - 1:])
        if len(ret) >= context.rmt_window - 1:
            rows.append(ret[-context.rmt_window:])

    if len(momentum_scores) < context.min_universe:
        record(regime_scale=0.0, gap=float("nan"), n_universe=len(momentum_scores))
        _flatten_all(context)
        return

    if rows:
        L = min(len(r) for r in rows)
        R = np.column_stack([r[-L:] for r in rows])
        gap = _complexity_gap(R)
    else:
        gap = float("nan")
    regime_scale = _scale_from_gap(gap, context)

    record(regime_scale=regime_scale, gap=float(gap), n_universe=len(momentum_scores))

    if regime_scale <= 0:
        _flatten_all(context)
        return

    sorted_roots = sorted(momentum_scores.items(), key=lambda kv: kv[1])
    n = len(sorted_roots)
    n_short = max(1, int(round(n * context.short_decile)))
    n_long = max(1, int(round(n * context.long_decile)))
    shorts = [r for r, _ in sorted_roots[:n_short]]
    longs = [r for r, _ in sorted_roots[-n_long:]]
    if context.reverse_momentum:
        longs, shorts = shorts, longs
    if context.long_only:
        shorts = []

    # long_only puts the full gross_target on the long side; L/S splits 50/50.
    if context.long_only:
        long_w = (context.gross_target * regime_scale) / max(len(longs), 1)
        short_w = 0.0
    else:
        long_w = (context.gross_target * regime_scale) / 2.0 / max(len(longs), 1)
        short_w = -(context.gross_target * regime_scale) / 2.0 / max(len(shorts), 1)

    target_pct: Dict[str, float] = {}
    for r in longs:
        target_pct[r] = long_w
    for r in shorts:
        target_pct[r] = short_w

    held_roots = set()
    for asset in list(context.portfolio.positions.keys()):
        held_roots.add(asset.root_symbol)

    # Close roots that drop out of the basket (and aren't TX hedge)
    for asset in list(context.portfolio.positions.keys()):
        if asset.root_symbol == "TX":
            continue
        if asset.root_symbol not in target_pct:
            order_target(asset, 0)

    for root, w in target_pct.items():
        cont = continuous_future(root, offset=0, roll="calendar", adjustment="add")
        front = data.current(cont, "contract")
        if front is None:
            continue
        order_target_percent(front, w)

    # TX hedge: short notional equal to net long basket
    if context.hedge_with_tx:
        net_w = sum(target_pct.values())
        tx_front = data.current(context.tx_cont, "contract")
        if tx_front is not None:
            order_target_percent(tx_front, -net_w)


def _flatten_all(context):
    for asset in list(context.portfolio.positions.keys()):
        order_target(asset, 0)


def handle_data(context, data):
    return
