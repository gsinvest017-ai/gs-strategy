# Regime-overlay template (strategy_form: regime_overlay).
# Base signal (default: simple trend) scaled day-by-day by an external
# macro risk weight exported from gs-E-risk's risk_ew state machine.
# Overlay arrives as bundle-local assets/regime_weights.csv.
import os

import pandas as pd

from zipline.api import order_target, record, symbol


def load_overlay(context):
    path = os.path.join(os.path.dirname(__file__), context.overlay_csv)
    s = pd.read_csv(path, parse_dates=["date"]).set_index("date")["weight"]
    return s.clip(0.0, 1.0)


def base_signal(context, data):
    """Return +1 / -1 / 0 direction. TODO: swap in any base strategy signal."""
    hist = data.history(context.asset, "price", context.lookback, "1d")
    above = hist.iloc[-1] > hist.mean()
    if above:
        return 1
    return -1 if context.allow_short else 0


def initialize(context):
    p = context.params
    context.asset = symbol(p.get("base_symbol", "TX"))
    context.lookback = int(p.get("base_lookback", 20))
    context.default_w = float(p.get("overlay_default_weight", 0.5))
    context.max_contracts = int(p.get("max_contracts", 2))
    context.allow_short = bool(p.get("allow_short", True))
    context.overlay_csv = p.get("overlay_csv", "assets/regime_weights.csv")
    # TODO: align overlay date index with TEJ session calendar
    context.weights = load_overlay(context)


def handle_data(context, data):
    key = context.get_datetime().tz_localize(None).normalize()
    w = context.weights.reindex([key])
    weight = float(w.iloc[0]) if len(w) and not pd.isna(w.iloc[0]) else context.default_w

    direction = base_signal(context, data)
    target = int(round(direction * context.max_contracts * weight))
    order_target(context.asset, target)
    record(regime_weight=weight, target=target)
