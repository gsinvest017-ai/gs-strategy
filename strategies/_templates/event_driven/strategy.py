# Event-window template (strategy_form: event_driven).
# Loads external event dates from a bundle-local assets/events.csv
# (spec §3.3 allows assets/ sidecars), opens a position pre_days before
# each event and flattens post_days after. Fill signal semantics in Phase 1.
import os

import pandas as pd

from zipline.api import order_target_percent, record, symbol


def load_events(context):
    path = os.path.join(os.path.dirname(__file__), context.events_csv)
    df = pd.read_csv(path, parse_dates=["date"])
    return df[df["strength"] >= context.min_strength].sort_values("date")


def initialize(context):
    p = context.params
    context.pre_days = int(p.get("pre_days", 2))
    context.post_days = int(p.get("post_days", 10))
    context.position_pct = float(p.get("position_pct", 0.05))
    context.max_concurrent = int(p.get("max_concurrent_events", 5))
    context.min_strength = float(p.get("min_signal_strength", 0.0))
    context.events_csv = p.get("events_csv", "assets/events.csv")
    # TODO: align TEJ session tz with event dates (naive dates below assume
    # local calendar days; refine in Phase 1 with quantdata reference/calendar)
    context.events = load_events(context)
    context.open_windows = {}   # asset -> bars remaining


def handle_data(context, data):
    today = context.get_datetime().tz_localize(None).normalize()

    due = context.events[
        (context.events["date"] - pd.Timedelta(days=context.pre_days) <= today)
        & (context.events["date"] >= today)
    ]
    for _, row in due.iterrows():
        asset = symbol(str(row["symbol"]))
        if asset in context.open_windows:
            continue
        if len(context.open_windows) >= context.max_concurrent:
            break
        side = context.position_pct if row["direction"] == "long" else -context.position_pct
        order_target_percent(asset, side)
        horizon = int((row["date"] - today).days) + context.post_days
        context.open_windows[asset] = max(horizon, 1)

    for asset, remaining in list(context.open_windows.items()):
        remaining -= 1
        if remaining <= 0:
            order_target_percent(asset, 0)
            del context.open_windows[asset]
        else:
            context.open_windows[asset] = remaining

    record(open_windows=len(context.open_windows))
