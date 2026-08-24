"""Cross-sectional multi-factor template (strategy_form: xs_multifactor).

Skeleton only -- fill score construction where marked TODO.
Contract: ~/gs-zipline-tej/docs/strategy-import-spec.md v1.2
Runner:   strategies/_common/runner.py (config.yaml -> context.params)
"""
import sys
from pathlib import Path

import pandas as pd

from zipline.api import (
    date_rules,
    order_target_percent,
    record,
    schedule_function,
    symbol,
    time_rules,
)


def build_scores(context, data):
    """Return pd.Series {asset: composite score} over context.universe.

    TODO Phase 1/2: resolve context.params['signals'] factor ids into
    per-asset scores (FORGE factor exports / MINT tournament weights).
    Placeholder: 12-1 momentum as a stand-in signal.
    """
    prices = data.history(context.universe, "price", 252, "1d")
    ret_12_1 = prices.iloc[-21] / prices.iloc[0] - 1.0
    return ret_12_1.dropna()


def rebalance(context, data):
    elig = _eligible(context, data)
    if len(elig) < context.n_long:
        return
    scores = build_scores(context, data).reindex([a.symbol for a in elig])
    ranked = scores.sort_values(ascending=False).dropna()

    longs = set(ranked.index[: context.n_long])
    shorts = set(ranked.index[-context.n_short:]) if context.n_short > 0 else set()

    # TODO: factor_proportional weighting
    weight = 1.0 / (len(longs) or 1)
    for a in elig:
        if a.symbol in longs:
            order_target_percent(a, weight)
        elif a.symbol in shorts:
            order_target_percent(a, -weight)
        else:
            order_target_percent(a, 0)


def _eligible(context, data):
    """Price floor + trailing mean dollar-volume liquidity floor."""
    out = []
    for a in context.universe:
        if not data.can_trade(a):
            continue
        px = float(data.current(a, "price"))
        if px < context.price_floor:
            continue
        hist = data.history(a, ["price", "volume"],
                            context.liq_window, "1d")
        amount = float((hist["price"] * hist["volume"]).mean())
        if amount >= context.liquidity_floor:
            out.append(a)
    return out


def initialize(context):
    p = context.params
    context.n_long = int(p.get("n_long", 10))
    context.n_short = int(p.get("n_short", 0))
    context.weighting = p.get("weighting", "equal")
    context.signals = list(p.get("signals", []))
    context.price_floor = float(p.get("price_floor", 10.0))
    context.liquidity_floor = float(p.get("liquidity_floor_ntd", 20_000_000))
    context.liq_window = int(p.get("liquidity_window", 20))

    # Universe resolution: explicit symbols override universe_source.
    if p.get("symbols"):
        context.universe = [symbol(s) for s in p["symbols"]]
    elif str(p.get("universe_source", "")).startswith("quantdata"):
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from strategies._common.quantdata import derive_universe

        as_of = p.get("universe_as_of")
        if not as_of:
            # PIT 建議：明確設在 backtest start 之前；未設則退回今天。
            as_of = pd.Timestamp.today().strftime("%Y-%m-%d")
        codes = derive_universe(
            as_of,
            top_n=int(p.get("universe_top_n", 200)),
            liquidity_floor_ntd=context.liquidity_floor,
            min_price=context.price_floor,
        )
        print(f"[xs_multifactor] quantdata universe as_of={as_of}: "
              f"{len(codes)} codes")
        context.universe = [symbol(c) for c in codes]
    else:
        context.universe = []

    freq = p.get("rebalance", "monthly")
    if freq == "daily":
        rule = date_rules.every_day()
    elif freq == "weekly":
        rule = date_rules.week_start()
    else:
        rule = date_rules.month_start()
    schedule_function(rebalance, date_rule=rule, time_rule=time_rules.market_open())


def handle_data(context, data):
    record(portfolio_value=context.portfolio.portfolio_value,
           positions=len(context.portfolio.positions))
