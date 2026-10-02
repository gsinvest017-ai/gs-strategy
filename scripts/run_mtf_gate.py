#!/usr/bin/env python3
"""Multi-timeframe resonance study on TX — the notes' "central idea", tested.

Reproduces docs/findings-mtf-resonance-tx.md.

    python scripts/run_mtf_gate.py --freq daily     # gate + filter chain + variants
    python scripts/run_mtf_gate.py --freq hourly    # gate only, with session split
    python scripts/run_mtf_gate.py --freq both --json out.json

Order matters and is not negotiable: the §5 tradability gate runs BEFORE any
strategy is built. If the price path cannot be distinguished from a martingale,
a backtest edge is selection noise and the honest move is to stop.

Three construction traps this script exists to avoid (all were hit while
writing it, all silently produce plausible numbers):

1. **Hourly returns across rolls, session gaps and data holes.** Diffing a
   concatenated bar sequence gave an annualised volatility of 142% against
   19.7% on daily bars. Returns are formed only inside contiguous
   same-contract runs, and the reconciliation is asserted, not assumed.

2. **Homoskedastic test statistics under volatility clustering.** On the same
   hourly data the homoskedastic variance-ratio z is 24.5 while the
   heteroskedasticity-robust z is 1.38. Ljung-Box shares the flaw. Only the
   robust statistic is used for the verdict; both are printed so the gap is
   visible.

3. **Thin-bar staleness.** The full-sample runs test rejects at p=0.002, but
   split by session that is p=0.019 in the illiquid night session and p=0.324
   in the liquid day session. Any intraday verdict is reported per session.
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
from strategies._common.factors import multiscale as ms  # noqa: E402
from strategies._common.factors import volume as vol  # noqa: E402
from strategies._common.validation import reality_check as rc  # noqa: E402
from strategies._common.validation import tradability as tb  # noqa: E402

DAILY_START, DAILY_END = "2016-01-01", "2026-08-27"
COST_BPS = 4.0                      # TX round trip: ~6 index points + fees
DAY_SESSION_UTC = range(0, 6)       # 00:00-05:59 UTC ~ the TW day session

HOURLY_SQL = """
WITH front AS (
    SELECT trade_date, expiry,
           row_number() OVER (PARTITION BY trade_date ORDER BY sum(volume) DESC) AS rn
    FROM taifex_futures_1m WHERE product = 'TX' AND year = {y} GROUP BY 1, 2
)
SELECT date_trunc('hour', b.ts_utc) AS bar_ts, min(b.trade_date) AS trade_date,
       min(b.expiry) AS expiry, arg_max(b.close, b.ts_utc) AS close,
       sum(b.volume) AS volume, sum(b.n_trades) AS n_trades
FROM taifex_futures_1m b
JOIN front f ON b.trade_date = f.trade_date AND b.expiry = f.expiry AND f.rn = 1
WHERE b.product = 'TX' AND b.year = {y} GROUP BY 1 ORDER BY 1
"""


def say(*a):
    print(*a, flush=True)


def gate(px: np.ndarray, ret: np.ndarray, label: str, out: dict, lags=(5, 10, 20)):
    """The §5 battery. Reports the robust statistic as the verdict-bearing one."""
    say(f"\n=== §5 gate: {label} (n={len(ret):,}) ===")
    vr = tb.variance_ratio_profile(ret, qs=(2, 4, 8, 16, 32))
    say(vr[["q", "vr", "z_heteroskedastic", "p_heteroskedastic",
            "z_homoskedastic", "p_homoskedastic"]].round(4).to_string(index=False))
    n_rob = int((vr["p_heteroskedastic"] < 0.05).sum())
    n_hom = int((vr["p_homoskedastic"] < 0.05).sum())
    say(f"  significant horizons: robust {n_rob}/5   homoskedastic {n_hom}/5")
    if n_hom > n_rob:
        say("  ^ the gap IS volatility clustering. Only the robust column counts.")

    lb_r = tb.ljung_box_returns(ret, lags=lags)
    lb_a = tb.ljung_box_abs_returns(ret, lags=lags)
    say(f"  Ljung-Box  max stat on r_t = {lb_r['lb_stat'].max():,.0f}"
        f" | on |r_t| = {lb_a['lb_stat'].max():,.0f}"
        f"  (|r| >> r means volatility, not direction)")
    rt = tb.runs_test(ret)
    say(f"  runs test  z={rt['z']:.3f}  p={rt['p_value']:.4g}")

    sub = ret[:8000]
    rng = np.random.default_rng(0)
    ctrl = rng.normal(sub.mean(), sub.std(ddof=1), len(sub))
    say(f"  permutation entropy {tb.permutation_entropy(sub, m=4):.4f}")
    say(f"  Hurst R/S {tb.hurst_rs(np.cumsum(sub)):.4f} "
        f"(control {tb.hurst_rs(np.cumsum(ctrl)):.4f})")
    say(f"  Hurst DFA {tb.hurst_dfa(np.cumsum(sub)):.4f} "
        f"(control {tb.hurst_dfa(np.cumsum(ctrl)):.4f})")

    s1 = tb.ta_suitability(px[:8000] if len(px) > 8000 else px)
    s2 = tb.ta_suitability(np.exp(np.cumsum(ctrl)) * 10000.0)
    say(f"  VERDICT {s1['score']:.1f}/100 -> {s1['verdict']}"
        f"   | random-walk control {s2['score']:.1f}/100 -> {s2['verdict']}")
    if s2["verdict"] == s1["verdict"]:
        say("  ^ control lands in the same bucket: the score does not discriminate here.")

    out[label] = {
        "n": len(ret),
        "vr": vr[["q", "vr", "z_heteroskedastic", "p_heteroskedastic"]].round(4).to_dict("records"),
        "robust_significant_horizons": n_rob,
        "homoskedastic_significant_horizons": n_hom,
        "runs_z": round(float(rt["z"]), 3), "runs_p": round(float(rt["p_value"]), 5),
        "score": round(float(s1["score"]), 1), "verdict": s1["verdict"],
        "control_score": round(float(s2["score"]), 1), "control_verdict": s2["verdict"],
    }


def run_daily(out: dict):
    tx = qd.futures_continuous("TX", DAILY_START, DAILY_END)
    tx = tx.sort_values("trading_date").set_index("trading_date")
    close, volu = tx["close"].astype(float), tx["volume"].astype(float)
    ret = np.diff(np.log(close.to_numpy()))
    say(f"TX daily {len(tx):,} sessions  ann.vol {ret.std(ddof=1)*np.sqrt(252)*100:.1f}%")
    gate(close.to_numpy(), ret, "daily", out)

    # ---- §4 filter chain -------------------------------------------------
    fwd1 = pd.Series(np.log(close).diff().shift(-1).to_numpy(), index=close.index)
    hi = pd.Series(ms.cross_scale_resonance(close.to_numpy(), scales=(3, 4), wavelet="d4"),
                   index=close.index)
    lo = pd.Series(ms.cross_scale_resonance(close.to_numpy(), scales=(1, 2), wavelet="d4"),
                   index=close.index)
    brk = pd.Series(np.asarray(vol.volume_breakout(volu.to_numpy(), window=20, k=1.0)),
                    index=close.index).fillna(False)
    usable = fwd1.notna() & hi.notna() & lo.notna()

    say("\n=== §4.3 conditional lift, layer by layer ===")
    chain = [("no filter", pd.Series(True, index=close.index)),
             ("+ large scale", hi > 0),
             ("+ medium scale", (hi > 0) & (lo > 0)),
             ("+ volume breakout", (hi > 0) & (lo > 0) & brk)]
    rows = []
    for label, c in chain:
        cond = (c & usable).fillna(False)
        r = ms.conditional_lift(np.ones(len(close), dtype=bool), cond.to_numpy(),
                                fwd1.to_numpy(), threshold=0.0)
        rows.append({"layer": label, "n_cond": r["n_cond"],
                     "p_cond": round(r["p_cond"], 4), "lift": round(r["lift"], 4),
                     "ci": [round(x, 4) for x in r["ci_cond"]],
                     "p_value": round(r["p_value"], 4),
                     "power_warning": r["power_warning"]})
    say(pd.DataFrame(rows).to_string(index=False))
    n0 = rows[0]["n_cond"]
    say("\n  §4.4 sample cost (multiplicative, as predicted):")
    for r in rows[1:]:
        say(f"    {r['layer']:20s} n={r['n_cond']:5d} = {100*r['n_cond']/n0:5.1f}%")
    out["lift_chain"] = rows

    # ---- §6 variant sweep ------------------------------------------------
    variants = {"large only": hi > 0, "medium only": lo > 0,
                "large+medium": (hi > 0) & (lo > 0),
                "large+medium+vol": (hi > 0) & (lo > 0) & brk,
                "vol only": brk, "large+vol": (hi > 0) & brk}
    series, srows = {}, []
    for name, c in variants.items():
        for side in ("long", "short"):
            pos = (c & usable).fillna(False).astype(float) * (1 if side == "long" else -1)
            pnl = (pos * fwd1).dropna()
            turn = pos.diff().abs().fillna(0).reindex(pnl.index).fillna(0)
            net = (pnl - turn * COST_BPS / 1e4).replace([np.inf, -np.inf], np.nan).dropna()
            if len(net) < 100 or net.std(ddof=1) == 0:
                continue
            key = f"{name}|{side}"
            series[key] = net
            srows.append({"variant": key, "days_in": int((pos != 0).sum()),
                          "net_bps_per_day": round(float(net.mean() * 1e4), 3),
                          "t": round(float(net.mean() / (net.std(ddof=1) / np.sqrt(len(net)))), 3)})
    summ = pd.DataFrame(srows).sort_values("net_bps_per_day", ascending=False)
    say("\n=== §6 variants (costed) ===")
    say(summ.to_string(index=False))

    names = list(series)
    idx = sorted(set().union(*[set(series[n].index) for n in names]))
    mat = pd.DataFrame({n: series[n].reindex(idx) for n in names}).fillna(0.0).to_numpy()
    white = rc.whites_reality_check(mat, n_boot=2000, mean_block=10, seed=11)
    spa = rc.hansens_spa(mat, n_boot=2000, mean_block=10, seed=11)
    stepm = rc.stepwise_multiple_testing(mat, alpha=0.05, n_boot=2000, mean_block=10, seed=11)
    say(f"\n  best={names[white['best_index']]}  naive best t={summ.iloc[0]['t']:.2f}")
    say(f"  White RC p={white['p_value']:.4f}   SPA p_consistent={spa['p_consistent']:.4f}")
    say(f"  StepM survivors: {[names[i] for i in stepm['rejected']] or 'NONE'}")
    out["variants"] = summ.to_dict("records")
    out["snooping"] = {"best": names[white["best_index"]],
                       "naive_best_t": float(summ.iloc[0]["t"]),
                       "white_p": round(float(white["p_value"]), 4),
                       "spa_p_consistent": round(float(spa["p_consistent"]), 4),
                       "stepm_survivors": [names[i] for i in stepm["rejected"]]}


def _clean_hourly_returns(frame: pd.DataFrame) -> np.ndarray:
    gap = frame["bar_ts"].diff().dt.total_seconds() / 3600.0
    same = frame["expiry"] == frame["expiry"].shift(1)
    r = np.log(frame["close"]).diff()[same & (gap <= 1.5)].to_numpy()
    return r[np.isfinite(r)]


def run_hourly(out: dict):
    frames = []
    for y in range(2016, 2027):
        try:
            df = qd.sql(HOURLY_SQL.format(y=y), timeout=150, retries=0)
            if len(df) > 100:
                frames.append(df)
            else:
                say(f"  {y}: {len(df)} bars -- data hole, dropped")
        except Exception as exc:
            say(f"  {y}: FAILED {str(exc)[:70]}")
    h = pd.concat(frames, ignore_index=True)
    h["bar_ts"] = pd.to_datetime(h["bar_ts"], utc=True)
    h = h.sort_values("bar_ts").drop_duplicates("bar_ts").reset_index(drop=True)
    h = h[np.isfinite(h["close"]) & (h["close"] > 0)].reset_index(drop=True)
    h["utc_hour"] = h["bar_ts"].dt.hour
    h["is_day"] = h["utc_hour"].isin(DAY_SESSION_UTC)

    ret = _clean_hourly_returns(h)
    bpd = len(h) / h["trade_date"].nunique()
    ann = ret.std(ddof=1) * np.sqrt(252 * bpd) * 100
    say(f"\nhourly bars {len(h):,}  usable returns {len(ret):,}  bars/session {bpd:.1f}")
    say(f"annualised vol {ann:.1f}%  (daily reference ~19.7%)")
    if not (10 <= ann <= 35):
        raise SystemExit(
            f"annualised vol {ann:.1f}% does not reconcile with the daily series -- "
            "the bar construction is wrong; refusing to report statistics on it"
        )
    say("  reconciles: roll / session-gap / data-hole handling is correct")
    out["hourly_ann_vol"] = round(float(ann), 1)

    px = np.exp(np.cumsum(ret)) * 10000.0
    gate(px, ret, "hourly_all", out, lags=(5, 10, int(round(bpd))))

    say("\n=== session split (thin bars manufacture sign structure) ===")
    for label, mask in (("hourly_day", h["is_day"]), ("hourly_night", ~h["is_day"])):
        sub = h[mask].reset_index(drop=True)
        r = _clean_hourly_returns(sub)
        if len(r) < 500:
            continue
        vr = tb.variance_ratio_profile(r, qs=(2, 4, 8))
        rt = tb.runs_test(r)
        say(f"  {label:14s} n={len(r):6,}  median trades/bar={sub['n_trades'].median():7,.0f}"
            f"  VR(2)={vr['vr'].iloc[0]:.4f} (p={vr['p_heteroskedastic'].iloc[0]:.3f})"
            f"  runs p={rt['p_value']:.4f}")
        out[label] = {"n": len(r),
                      "median_trades_per_bar": float(sub["n_trades"].median()),
                      "vr2": round(float(vr["vr"].iloc[0]), 4),
                      "vr2_p_robust": round(float(vr["p_heteroskedastic"].iloc[0]), 4),
                      "runs_p": round(float(rt["p_value"]), 4)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", choices=("daily", "hourly", "both"), default="both")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    out: dict = {}
    if args.freq in ("daily", "both"):
        run_daily(out)
    if args.freq in ("hourly", "both"):
        run_hourly(out)

    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
        say(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
