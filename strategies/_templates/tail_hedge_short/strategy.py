# Breakdown-short tail hedge template (strategy_form: tail_hedge_short).
# State machine per symbol: IDLE -> SHORTED -> (staged covers) -> IDLE.
# Entry: price makes a lookback-high then fades back below it by
# fake_break_margin (bull trap). Exits: prior-high stop or staged trailing
# take-profit. Monte Carlo position sizing plugs into risk_fraction.
from zipline.api import order, order_target, record, symbol

IDLE = "idle"
SHORTED = "shorted"


def initialize(context):
    p = context.params
    context.lookback = int(p.get("breakout_lookback", 60))
    context.margin_pct = float(p.get("fake_break_margin", 0.02))
    context.trail_steps = list(p.get("trail_steps_pct", [0.05, 0.10]))
    context.risk_fraction = float(p.get("risk_fraction_per_trade", 0.08))
    # TODO Phase 2: cap concurrent positions via max_positions + Monte Carlo
    context.state = {symbol(s): {"phase": IDLE, "steps_done": 0}
                     for s in p.get("symbols", [])}


def handle_data(context, data):
    for asset, st in context.state.items():
        if not data.can_trade(asset):
            continue
        hist = data.history(asset, "price", context.lookback, "1d")
        prior_high = float(hist.iloc[:-1].max())
        price = float(data.current(asset, "price"))
        pos = context.portfolio.positions[asset]

        if st["phase"] == IDLE:
            broke_out = float(hist.iloc[-2]) >= prior_high
            faded = price <= prior_high * (1 - context.margin_pct)
            if broke_out and faded and pos.amount == 0:
                shares = int(-(context.portfolio.portfolio_value
                               * context.risk_fraction) // price)
                if shares < 0:
                    order(asset, shares)
                    st["phase"] = SHORTED
                    st["entry_high"] = prior_high
                    st["steps_done"] = 0
        elif st["phase"] == SHORTED:
            if price >= st.get("entry_high", price):   # 前高停損
                order_target(asset, 0)
                st["phase"] = IDLE
            else:
                gain = (st["entry_high"] - price) / st["entry_high"]
                steps = context.trail_steps
                if (st["steps_done"] < len(steps)
                        and gain >= steps[st["steps_done"]]
                        and pos.amount < 0):
                    order_target(asset, int(pos.amount * 2 / 3))  # 分批減碼
                    st["steps_done"] += 1
                    if st["steps_done"] == len(steps):
                        order_target(asset, 0)                    # 全數了結
                        st["phase"] = IDLE

    active = sum(1 for s in context.state.values() if s["phase"] != IDLE)
    record(short_states=active)
