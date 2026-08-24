"""Cross-sectional multi-factor template (strategy_form: xs_multifactor).

Skeleton only -- fill score construction where marked TODO.
Contract: ~/gs-zipline-tej/docs/strategy-import-spec.md v1.2
Runner:   strategies/_common/runner.py (config.yaml -> context.params)
"""
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
    elig = [a for a in context.universe
            if data.current(a, "price") >= context.price_floor]
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


def initialize(context):
    p = context.params
    context.n_long = int(p.get("n_long", 10))
    context.n_short = int(p.get("n_short", 0))
    context.weighting = p.get("weighting", "equal")
    context.signals = list(p.get("signals", []))
    context.price_floor = float(p.get("price_floor", 10.0))
    context.universe = [symbol(s) for s in p.get("symbols", [])]

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
