#!/usr/bin/env python3
"""End-to-end disposition-stock study, reproducible from the quantdata service.

Runs the whole chain that produced docs/findings-disposition-rebound.md:

  1. feasibility  -- can these names be shorted at all? (answers: effectively no)
  2. matched event study -- abnormal returns vs a momentum/turnover-matched
     control basket, with matching characteristics read at u-1 so the event
     day's own return cannot leak into control selection
  3. variant sweep -- 24 side x window combinations, costed
  4. data-snooping correction -- White RC / Hansen SPA / Romano-Wolf StepM over
     all 24 jointly, because reporting the best of 24 uncorrected is the exact
     error the validation package exists to prevent
  5. censoring -- separates right-censoring (sample end) from true suspension,
     and marks suspended names to their actual resumption price

Usage::

    python scripts/run_disposition_study.py                  # full study
    python scripts/run_disposition_study.py --skip-feasibility
    python scripts/run_disposition_study.py --json out.json

Two data traps this script is built around, both verified rather than assumed:

  * ``stock_attrs_status.is_disposition_bool`` is empty before 2021.
  * ``tw_stock_bars.adj_close`` is NULL before 2026. Returns therefore come
    from ``stock_factor_daily.ret_1d``, whose coverage is asserted at startup.
    Reading adjusted bars instead silently collapses the sample to one year
    while ``groupby.size()`` keeps reporting the full n.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from strategies._common import qd  # noqa: E402
from strategies._common.risk import drawdown as ddm  # noqa: E402
from strategies._common.validation import reality_check as rc  # noqa: E402

START, END = "2020-11-01", "2026-08-27"
FLAG_START = "2021-01-01"
HOLD, K_CONTROLS = 10, 10

FEE_BPS, TAX_BPS, AUCTION_SLIP_BPS, SHORT_EXTRA_BPS = 5.415, 30.0, 25.0, 20.0
COST_LONG = 2 * FEE_BPS + TAX_BPS + 2 * AUCTION_SLIP_BPS          # 90.83
COST_SHORT = COST_LONG + SHORT_EXTRA_BPS                          # 110.83


def round_trip_cost_bps(side: str, in_disposition: bool) -> float:
    """Round-trip cost in bps.

    ``in_disposition`` controls the call-auction slippage charge: it applies only
    while the name is under 5- or 20-minute periodic matching. A window that opens
    after the disposition has ended trades on a continuous book and must not be
    charged for an auction it never faced.
    """
    c = 2 * FEE_BPS + TAX_BPS
    if side == "short":
        c += SHORT_EXTRA_BPS
    if in_disposition:
        c += 2 * AUCTION_SLIP_BPS
    return c


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------- data load
def load_all():
    attrs = qd.attrs_status(FLAG_START, END, events_only=True)
    for c in ("is_attention_bool", "is_disposition_bool", "is_no_daytrade_bool",
              "is_full_settle_bool", "is_suspended_bool"):
        if c in attrs.columns:
            attrs[c] = attrs[c].astype("boolean").fillna(False).astype(bool)

    fac = qd.cached_sql(
        "SELECT trading_date, symbol, ret_1d, ret_20d, turnover_20d "
        "FROM stock_factor_daily "
        "WHERE trading_date BETWEEN DATE '{start}' AND DATE '{end}'",
        start=START, end=END, tag="fac_match",
    )
    fac["trading_date"] = pd.to_datetime(fac["trading_date"])
    fac["symbol"] = fac["symbol"].astype(str)

    nan_rate = float(fac["ret_1d"].isna().mean())
    if nan_rate > 0.05:
        raise SystemExit(
            f"stock_factor_daily.ret_1d is {nan_rate:.1%} NULL -- refusing to run a "
            "study on a column with material gaps"
        )
    log(f"ret_1d NULL rate {nan_rate:.4%} (ok)")
    return attrs, fac


def episodes_from(attrs, max_gap_days=5):
    d = attrs[attrs["is_disposition_bool"]].sort_values(["stock_id", "trading_date"]).copy()
    gap = d.groupby("stock_id")["trading_date"].diff().dt.days.fillna(9999)
    d["_ep"] = (gap > max_gap_days).astype(int).groupby(d["stock_id"]).cumsum()
    ep = (d.groupby(["stock_id", "_ep"])
            .agg(start=("trading_date", "min"), end=("trading_date", "max"),
                 sessions=("trading_date", "size"))
            .reset_index().drop(columns="_ep"))
    ep["stock_id"] = ep["stock_id"].astype(str)
    return ep.sort_values(["start", "stock_id"]).reset_index(drop=True)


# ------------------------------------------------------------- 1 feasibility
def feasibility(attrs, eps, out):
    log("[1] short-side feasibility")
    d = attrs[attrs["is_disposition_bool"]]
    n = len(d)
    out["feasibility"] = {
        "disposition_stock_days": int(n),
        "also_no_daytrade_pct": round(100 * float(d["is_no_daytrade_bool"].mean()), 2),
        "also_full_settle_pct": round(100 * float(d["is_full_settle_bool"].mean()), 2),
        "episodes": int(len(eps)),
        "distinct_stocks": int(eps["stock_id"].nunique()),
        "median_sessions": float(eps["sessions"].median()),
    }
    log(f"    {n:,} disposition stock-days; "
        f"{out['feasibility']['also_no_daytrade_pct']:.1f}% also day-trade banned")

    syms = sorted(eps[eps["start"] >= "2024-01-01"]["stock_id"].unique())[:150]
    try:
        mg = qd.margin_daily("2024-01-01", END, symbols=syms)
    except Exception as exc:
        log(f"    margin pull failed: {exc}")
        return
    if mg.empty:
        return
    mg["stock_id"] = mg["stock_id"].astype(str)
    rows = []
    for _, ep in eps[eps["stock_id"].isin(syms)].iterrows():
        g = mg[mg["stock_id"] == ep["stock_id"]]
        pre = g[(g["trading_date"] < ep["start"])
                & (g["trading_date"] >= ep["start"] - pd.Timedelta(days=45))]
        dur = g[(g["trading_date"] >= ep["start"]) & (g["trading_date"] <= ep["end"])]
        if len(pre) < 5 or len(dur) < 3:
            continue
        rows.append({"pre": pre["short_sell_lot"].median(),
                     "dur": dur["short_sell_lot"].median(),
                     "all_zero": float((dur["short_sell_lot"].fillna(0) == 0).all())})
    r = pd.DataFrame(rows)
    if len(r):
        ratio = (r["dur"] / r["pre"].replace(0, np.nan)).median()
        out["feasibility"].update({
            "margin_episodes_checked": int(len(r)),
            "median_short_sell_lots_pre": float(r["pre"].median()),
            "median_short_sell_lots_during": float(r["dur"].median()),
            "median_during_over_pre": round(float(ratio), 3),
            "pct_episodes_zero_short_throughout": round(100 * float(r["all_zero"].mean()), 1),
        })
        log(f"    short-sell lots/day  pre={r['pre'].median():.0f} "
            f"during={r['dur'].median():.0f}  ratio={ratio:.3f}")


# --------------------------------------------------- 2/3 matched event study
def build_matrices(fac):
    dates = np.array(sorted(fac["trading_date"].unique()))
    piv = fac.pivot_table(index="trading_date", columns="symbol", values="ret_1d").reindex(dates)
    return dates, {d: i for i, d in enumerate(dates)}, piv, \
        {s: i for i, s in enumerate(piv.columns)}, piv.to_numpy()


def matched_panel(eps, fac, dates, date_pos, col, R, attrs, anchor_col, pre=5, post=15):
    flagged = attrs[attrs["is_attention_bool"] | attrs["is_disposition_bool"]]
    flag_arrays = {s: np.sort(np.array([date_pos[d] for d in v if d in date_pos]))
                   for s, v in flagged.groupby("stock_id")["trading_date"].apply(list).items()}
    by_date = {d: g for d, g in fac.groupby("trading_date")}

    def clean(sym, ipos, radius=30):
        a = flag_arrays.get(str(sym))
        if a is None or a.size == 0:
            return True
        return (np.searchsorted(a, ipos + radius, "right")
                == np.searchsorted(a, ipos - radius, "left"))

    rows = []
    for _, ep in eps.iterrows():
        sid = ep["stock_id"]
        i0 = date_pos.get(ep[anchor_col])
        if i0 is None or sid not in col or i0 < 1:
            continue
        day = by_date.get(dates[i0 - 1])          # characteristics BEFORE the event
        if day is None:
            continue
        me = day[day["symbol"] == sid]
        if me.empty or not np.isfinite(me["ret_20d"].iloc[0]):
            continue
        pool = day[(day["symbol"] != sid) & day["ret_20d"].notna() & day["turnover_20d"].notna()]
        pool = pool[[clean(s, i0) for s in pool["symbol"]]]
        if len(pool) < K_CONTROLS:
            continue
        rs = pool["ret_20d"].std(ddof=0) or 1.0
        ts = pool["turnover_20d"].std(ddof=0) or 1.0
        dist = (((pool["ret_20d"] - float(me["ret_20d"].iloc[0])) / rs) ** 2
                + ((pool["turnover_20d"] - float(me["turnover_20d"].iloc[0])) / ts) ** 2)
        ctrl = [col[c] for c in pool.assign(d=dist).nsmallest(K_CONTROLS, "d")["symbol"] if c in col]

        lo, hi = max(0, i0 - pre), min(len(dates) - 1, i0 + post)
        ev = R[lo:hi + 1, col[sid]]
        ct = np.nanmean(R[lo:hi + 1, ctrl], axis=1)
        for u, a, b in zip(np.arange(lo, hi + 1) - i0, ev, ct):
            if np.isfinite(a) and np.isfinite(b):
                rows.append((f"{sid}_{ep['start'].date()}", ep["start"], int(u), a - b))
    return pd.DataFrame(rows, columns=["episode", "ep_start", "u", "abn"])


def variant_sweep(p_in, p_out, out):
    log("[3] variant sweep + [4] data-snooping correction")
    series, rows = {}, []
    for anchor, p in (("entry", p_in), ("exit", p_out)):
        for w in [(0, 0), (0, 1), (0, 2), (1, 5), (1, 10), (0, 10)]:
            for side in ("long", "short"):
                s = p[p["u"].between(*w)].groupby(["episode", "ep_start"])["abn"].sum()
                s = s[np.isfinite(s)]
                if len(s) < 100:
                    continue
                sign = 1.0 if side == "long" else -1.0
                # Auction slippage applies only while the name is actually under
                # call-auction matching. An exit-anchored window that opens at
                # u >= 1 starts after the disposition has ended, so the stock is
                # back on continuous matching and charging 2 x 25 bps there
                # overstates its cost by 50 bps. Getting this wrong does not
                # change any sign here, but it moved four variants' t-stats by up
                # to 2.5x, which is enough to reorder a leaderboard.
                in_disposition = not (anchor == "exit" and w[0] >= 1)
                cost = round_trip_cost_bps(side, in_disposition) / 1e4
                net = sign * s - cost
                name = f"{anchor}|{side}|CAR[{w[0]},{w[1]}]"
                rows.append({"variant": name, "n": len(net),
                             "gross_bps": float((sign * s).mean() * 1e4),
                             "net_bps": float(net.mean() * 1e4),
                             "t_net": float(net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))),
                             "hit": float((net > 0).mean())})
                series[name] = pd.Series(net.to_numpy(),
                                         index=pd.to_datetime([i[1] for i in net.index]))
    summary = pd.DataFrame(rows).sort_values("net_bps", ascending=False)
    names = list(series)
    common = sorted(set().union(*[set(series[n].index) for n in names]))
    mat = pd.DataFrame({n: series[n].groupby(level=0).mean().reindex(common)
                        for n in names}).fillna(0.0).to_numpy()

    white = rc.whites_reality_check(mat, n_boot=2000, mean_block=10, seed=7)
    spa = rc.hansens_spa(mat, n_boot=2000, mean_block=10, seed=7)
    stepm = rc.stepwise_multiple_testing(mat, alpha=0.05, n_boot=2000, mean_block=10, seed=7)
    out["variants"] = summary.round(2).to_dict("records")
    out["snooping"] = {
        "n_variants": len(names),
        "best": names[white["best_index"]],
        "white_p": round(float(white["p_value"]), 4),
        "spa_p_consistent": round(float(spa["p_consistent"]), 4),
        "stepm_survivors": [names[i] for i in stepm["rejected"]],
        "naive_best_t": float(summary.iloc[0]["t_net"]),
    }
    log(f"    best={out['snooping']['best']}  White p={out['snooping']['white_p']}  "
        f"StepM survivors={len(out['snooping']['stepm_survivors'])}/{len(names)}")
    return summary


# ------------------------------------------------------------- 5 censoring
def censoring_and_headline(eps, dates, date_pos, col, R, out):
    log("[5] censoring + headline")
    last = len(dates) - 1
    recs = []
    for _, ep in eps.iterrows():
        sid, i0 = ep["stock_id"], date_pos.get(ep["start"])
        if i0 is None or sid not in col:
            continue
        if (i0 + HOLD) > last:
            recs.append({"stock_id": sid, "start": ep["start"], "year": ep["start"].year,
                         "kind": "right_censored", "gross": np.nan, "i0": i0})
            continue
        r = R[i0 + 1: i0 + 1 + HOLD, col[sid]]
        n_obs = int(np.isfinite(r).sum())
        kind = "complete" if n_obs == HOLD else ("silent" if n_obs == 0 else "partial")
        recs.append({"stock_id": sid, "start": ep["start"], "year": ep["start"].year,
                     "kind": kind, "n_obs": n_obs, "i0": i0,
                     "gross": float(np.prod(1 + r[np.isfinite(r)]) - 1) if n_obs else np.nan})
    D = pd.DataFrame(recs)
    counts = D["kind"].value_counts().to_dict()
    log(f"    {counts}")

    # follow the silent names to their actual resumption price
    marks = {}
    for _, row in D[D["kind"] == "silent"].iterrows():
        series = R[int(row["i0"]) + 1:, col[row["stock_id"]]]
        fin = np.where(np.isfinite(series))[0]
        marks[(row["stock_id"], row["start"])] = float(series[int(fin[0])]) if fin.size else -1.0

    usable = D[D["kind"] != "right_censored"].copy()
    usable["gross_marked"] = [
        marks.get((r["stock_id"], r["start"]), r["gross"]) if r["kind"] == "silent" else r["gross"]
        for _, r in usable.iterrows()
    ]
    usable["net"] = usable["gross_marked"] - COST_LONG / 1e4
    net = usable["net"].dropna()
    t = float(net.mean() / (net.std(ddof=1) / np.sqrt(len(net))))
    out["headline"] = {
        "kind_counts": {k: int(v) for k, v in counts.items()},
        "n": int(len(net)),
        "net_bps": round(float(net.mean() * 1e4), 1),
        "median_bps": round(float(net.median() * 1e4), 1),
        "t": round(t, 2),
        "hit_rate": round(float((net > 0).mean()), 3),
        "cost_bps_assumed": COST_LONG,
    }
    log(f"    headline net={out['headline']['net_bps']} bps  t={t:.2f}  n={len(net):,}")

    yr = usable.groupby("year")["net"].agg(n="size", mean=lambda s: s.mean() * 1e4)
    yr["t"] = usable.groupby("year")["net"].apply(
        lambda s: s.mean() / (s.std(ddof=1) / np.sqrt(len(s))) if len(s) > 2 else np.nan)
    out["by_year"] = {int(k): {"n": int(v["n"]), "net_bps": round(float(v["mean"]), 1),
                               "t": round(float(v["t"]), 2)}
                      for k, v in yr.iterrows()}

    out["cost_breakeven"] = {}
    for c in (COST_LONG, 150, 200, 300, 400, 500):
        n2 = usable["gross_marked"].dropna() - c / 1e4
        out["cost_breakeven"][str(round(c, 1))] = round(float(n2.mean() * 1e4), 1)

    seq = usable.dropna(subset=["net"]).sort_values("start").copy()
    seq["bucket"] = seq["start"].dt.to_period("W")
    port = seq.groupby("bucket")["net"].mean()
    rr = ddm.ratio_report(port.to_numpy(), periods_per_year=52)
    out["portfolio"] = {k: round(float(rr[k]), 3) for k in
                        ("cagr", "vol", "sharpe", "max_drawdown", "calmar",
                         "sterling_original", "sortino_full", "ulcer_index")
                        if k in rr}
    out["portfolio"]["weekly_periods"] = int(len(port))
    return usable


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--skip-feasibility", action="store_true")
    args = ap.parse_args()

    out: dict = {"window": {"start": FLAG_START, "end": END},
                 "cost_model_bps": {"long": COST_LONG, "short": COST_SHORT}}
    attrs, fac = load_all()
    eps = episodes_from(attrs)
    log(f"episodes {len(eps):,} / stocks {eps['stock_id'].nunique():,}")

    if not args.skip_feasibility:
        feasibility(attrs, eps, out)

    dates, date_pos, piv, col, R = build_matrices(fac)
    log("[2] matched event study")
    p_in = matched_panel(eps, fac, dates, date_pos, col, R, attrs, "start")
    eps["exit_anchor"] = eps["end"]
    p_out = matched_panel(eps, fac, dates, date_pos, col, R, attrs, "exit_anchor")
    log(f"    entry panel {p_in['episode'].nunique():,} episodes, "
        f"exit panel {p_out['episode'].nunique():,}")
    ent = p_in.groupby("u")["abn"]
    out["entry_car_bps"] = {int(u): round(float(v * 1e4), 1)
                            for u, v in ent.mean().items() if -3 <= u <= 12}

    variant_sweep(p_in, p_out, out)
    censoring_and_headline(eps, dates, date_pos, col, R, out)

    text = json.dumps(out, indent=2, ensure_ascii=False)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
        log(f"wrote {args.json}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
