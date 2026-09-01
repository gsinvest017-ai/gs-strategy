"""Auto-generated BUY-AND-HOLD fallback skeleton bundle.

Source paper: The Triadic Stress Index in Financial Markets
              http://arxiv.org/abs/2608.10788v1

The paper did NOT match any signal-driven template. This skeleton holds a
single fixed contract for the entire backtest window — useful as a
baseline placeholder but **not** a real strategy. A human must replace
this with the paper's actual mechanism if it has one (factor tilt, option
overlay, vol-targeting, ...) and then flip
``manifest.requires_review`` to ``false``.
"""
from __future__ import annotations

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


def initialize(context):
    p = context.params
    context.root = str(p.get("root_symbol", "TX"))
    context.position_contracts = int(p.get("position_contracts", 1))
    context.has_ordered = False
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
    if context.has_ordered:
        return
    front = data.current(context.cont, "contract")
    if front is None:
        return
    order_target(front, context.position_contracts)
    context.has_ordered = True
    record(target_contracts=context.position_contracts)
