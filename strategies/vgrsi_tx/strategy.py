"""VGRSI on TX continuous future.

Reference
---------
Rafał Rak, "Visibility graphs can make money in financial markets",
arXiv:2605.01300 (2026).

Idea
----
The Visibility Graph (VG) maps a price series to a graph: each bar is a node,
and two bars (i, j) are linked if every intermediate bar lies *below* the line
connecting them (backward visibility). The degree sequence of recent bars
captures local-vs-global geometric structure that classical RSI smooths over.

Definitions used here (paper, eqs. 1-3):
    * For window of length N, build the *backward* VG on the last N closes.
    * For each node t in the window, count edges only to nodes s < t such that
      the line (s, P_s) - (t, P_t) lies above all (k, P_k) for s < k < t.
    * "Up degree"  = #edges into t coming from a *lower* close (P_s < P_t)
      "Down degree"= #edges into t coming from a *higher* close (P_s > P_t)
    * VGRSI_t = 100 * Up / (Up + Down)  (rescaled to [0, 100])

The paper trades when VGRSI crosses the (30, 70) thresholds; the implementation
also allows a long-only variant for index futures where short selling is not
the priority.
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
    continuous_future,
    date_rules,
    order_target,
    record,
    schedule_function,
    time_rules,
)


# ---------------------------------------------------------------------------
# VGRSI core
# ---------------------------------------------------------------------------

def _backward_visibility_degrees(prices: np.ndarray) -> np.ndarray:
    """Return per-node (up_deg, down_deg) for backward VG over a window.

    For node t, look at every s < t and check whether the straight line from
    (s, P_s) to (t, P_t) stays strictly above every intermediate close P_k
    (s < k < t). Equivalent inequality:

        P_k < P_s + (P_t - P_s) * (k - s) / (t - s)  for all s < k < t

    Returns an array of shape (N, 2): columns = (up_deg, down_deg).
    """
    n = len(prices)
    degs = np.zeros((n, 2), dtype=np.int64)
    if n < 2:
        return degs
    for t in range(1, n):
        pt = prices[t]
        for s in range(t - 1, -1, -1):
            ps = prices[s]
            if t - s == 1:
                visible = True
            else:
                ks = np.arange(s + 1, t)
                line = ps + (pt - ps) * (ks - s) / (t - s)
                visible = bool(np.all(prices[ks] < line))
            if visible:
                if ps < pt:
                    degs[t, 0] += 1
                elif ps > pt:
                    degs[t, 1] += 1
                # ps == pt contributes nothing
    return degs


def vgrsi_value(window_closes: np.ndarray) -> float:
    """Single-bar VGRSI on the most recent close inside `window_closes`."""
    degs = _backward_visibility_degrees(np.asarray(window_closes, dtype=float))
    up_t, down_t = degs[-1]
    total = up_t + down_t
    if total == 0:
        return 50.0
    return 100.0 * up_t / total


# ---------------------------------------------------------------------------
# Zipline lifecycle
# ---------------------------------------------------------------------------

def initialize(context):
    p: Dict = getattr(context, "params", {})
    context.root_symbol = p.get("root_symbol", "TX")
    context.window = int(p.get("window", 30))
    context.upper = float(p.get("upper_threshold", 70.0))
    context.lower = float(p.get("lower_threshold", 30.0))
    context.allow_short = bool(p.get("allow_short", False))
    context.position_contracts = int(p.get("position_contracts", 1))

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
    history = data.history(cont, "close", context.window + 5, "1d")
    closes = history.dropna().values[-context.window:]
    if len(closes) < context.window:
        return

    rsi = vgrsi_value(closes)
    front = data.current(cont, "contract")
    if front is None:
        return

    pos = context.portfolio.positions.get(front)
    qty = pos.amount if pos else 0

    target_qty = qty
    if rsi < context.lower:
        target_qty = +context.position_contracts
    elif rsi > context.upper:
        target_qty = -context.position_contracts if context.allow_short else 0

    record(vgrsi=rsi, target_qty=target_qty)
    if target_qty != qty:
        order_target(front, target_qty)


def handle_data(context, data):
    """Required by zipline; the heavy lifting is in scheduled `_evaluate`."""
    return
