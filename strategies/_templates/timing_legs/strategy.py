# Staged-entry timing template (strategy_form: timing_legs).
# Gate logic: a composite timing score (upstream: gs--Market-Timing legs)
# admits one entry leg per pass until fully invested; score collapse exits.
# Fill compute_gate_score() with real factors in Phase 1+.
from zipline.api import order, order_target, record, symbol


def compute_gate_score(context, data):
    """Return float in [0, 1] -- composite timing score for today.

    TODO Phase 1+: blend admitted legs from gs--Market-Timing
    (BBW family / chip family / IVOL / Amihud) with their gate weights.
    Placeholder: 20-day trend sign on the root symbol.
    """
    hist = data.history(context.asset, "price", 20, "1d")
    return 1.0 if hist.iloc[-1] > hist.mean() else 0.0


def initialize(context):
    p = context.params
    context.asset = symbol(p.get("root_symbol", "TX"))
    context.n_legs = int(p.get("n_legs", 3))
    per_leg = int(p.get("max_contracts", 3)) / max(context.n_legs, 1)
    context.leg_size = max(int(per_leg), 1)
    context.gate_threshold = float(p.get("gate_threshold", 0.6))
    context.cooldown = int(p.get("gate_cooldown_days", 5))
    context.exit_score = float(p.get("exit_score", 0.35))
    context.allow_short = bool(p.get("allow_short", False))

    context.legs_filled = 0
    context.days_since_last_leg = context.cooldown


def handle_data(context, data):
    score = compute_gate_score(context, data)
    context.days_since_last_leg += 1

    if score <= context.exit_score and context.legs_filled > 0:
        order_target(context.asset, 0)
        context.legs_filled = 0
        context.days_since_last_leg = context.cooldown
        record(gate_score=score, legs=0)
        return

    admitted = score >= context.gate_threshold
    can_add = (
        admitted
        and context.legs_filled < context.n_legs
        and context.days_since_last_leg >= context.cooldown
    )
    if can_add:
        if score >= 0.5:
            direction = 1
        elif context.allow_short:
            direction = -1
        else:
            direction = 0
        if direction != 0:
            order(context.asset, direction * context.leg_size)
            context.legs_filled += 1
            context.days_since_last_leg = 0

    record(gate_score=score, legs=context.legs_filled)
