"""Run xsmom_stkfut_rmt across non-overlapping walk-forward sub-periods.

The full 2020-01-01 .. 2026-04-30 backtest hides regime structure: COVID
rebound, 2022 rate-hike bear, and the 2023+ AI bull may have very different
alpha properties. This script reruns the *current* M15-calibrated config
on three tiled sub-periods and reports per-period metrics + regime
diagnostics.

Each sub-period uses the same 60-root universe, beta-neutral hedge, and
60-root RMT thresholds (0.049 / 0.037) as M15.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_walkforward.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_env_path = _ROOT / ".env"
if _env_path.exists() and not os.environ.get("TEJAPI_KEY"):
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(_ROOT / "strategies" / "_common"))
from runner import run_strategy_from_config  # noqa: E402


# Tile the full 2020-01-01..2026-04-30 window into three roughly-equal
# non-overlapping pieces. Each piece is long enough (>= 2 years) that the
# 126-day lookback + 60-day beta window can warm up before any trading.
PERIODS = [
    ("P1_2020_2021", "2020-01-01", "2021-12-31"),
    ("P2_2022_2023", "2022-01-01", "2023-12-31"),
    ("P3_2024_2026", "2024-01-01", "2026-04-30"),
]

BASE_CONFIG = _ROOT / "strategies" / "xsmom_stkfut_rmt" / "config.yaml"
STRATEGY = _ROOT / "strategies" / "xsmom_stkfut_rmt" / "strategy.py"


def _summary(df: pd.DataFrame) -> dict:
    pv = df["portfolio_value"]
    daily_ret = df["returns"]
    years = (df.index[-1] - df.index[0]).days / 365.25
    total_ret = pv.iloc[-1] / pv.iloc[0] - 1
    cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 and pv.iloc[-1] > 0 else float("nan")
    sharpe = (
        daily_ret.mean() / daily_ret.std() * np.sqrt(252)
        if daily_ret.std() > 0
        else float("nan")
    )
    ann_vol = daily_ret.std() * np.sqrt(252)
    cummax = pv.cummax()
    max_dd = (pv / cummax - 1).min()
    return {
        "years": years,
        "CAGR": cagr,
        "ann_vol": ann_vol,
        "Sharpe": sharpe,
        "Max_DD": max_dd,
        "total_return": total_ret,
        "final": float(pv.iloc[-1]),
        "n_days": int(len(df)),
    }


def _regime_diag(df: pd.DataFrame) -> dict:
    """Pull regime_scale + basket_beta + gap from recorded fields, if present."""
    out: dict = {}
    for col in ("regime_scale", "basket_beta", "gap"):
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        out[f"{col}_n"] = int(len(s))
        out[f"{col}_mean"] = float(s.mean())
        out[f"{col}_std"] = float(s.std())
        if col == "regime_scale":
            for v in (0.0, 0.5, 1.0):
                frac = float((s == v).mean())
                out[f"scale_eq_{v}"] = frac
    return out


def main() -> int:
    with open(BASE_CONFIG, "r", encoding="utf-8") as fh:
        base = yaml.safe_load(fh)

    results = []
    diagnostics = []
    for name, start, end in PERIODS:
        cfg = yaml.safe_load(yaml.safe_dump(base))  # deep copy
        cfg["start"] = start
        cfg["end"] = end
        # Keep universe_start/end in sync (only matters if auto-discovery
        # falls back, but be defensive).
        cfg.setdefault("params", {})["universe_start"] = start
        cfg["params"]["universe_end"] = end

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(cfg, tmp)
            tmp_path = tmp.name
        out_path = Path(f"/tmp/xsmom_m16_walkforward_{name}_result.pkl")
        print(f"[{name}] {start} .. {end} -> {out_path}", flush=True)

        df = run_strategy_from_config(STRATEGY, tmp_path, out_path)

        s = _summary(df)
        s["name"] = name
        s["start"] = start
        s["end"] = end
        results.append(s)

        d = _regime_diag(df)
        d["name"] = name
        diagnostics.append(d)

        print(
            f"[{name}] years={s['years']:.2f} CAGR={s['CAGR']:.2%} "
            f"Sharpe={s['Sharpe']:.3f} vol={s['ann_vol']:.2%} "
            f"Max_DD={s['Max_DD']:.2%}",
            flush=True,
        )

    print()
    print("## Walk-forward metrics")
    print()
    print("| period | range | years | CAGR | ann_vol | Sharpe | Max_DD | final |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in results:
        print(
            f"| {r['name']} | {r['start']} .. {r['end']} | "
            f"{r['years']:.2f} | {r['CAGR']:.2%} | {r['ann_vol']:.2%} | "
            f"{r['Sharpe']:.3f} | {r['Max_DD']:.2%} | {r['final']:,.0f} |"
        )

    print()
    print("## Regime diagnostics")
    print()
    print(
        "| period | scale=0 | scale=0.5 | scale=1.0 | gap_mean | basket_beta_mean | basket_beta_std |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|")
    for d in diagnostics:
        s0 = d.get("scale_eq_0.0", float("nan"))
        s5 = d.get("scale_eq_0.5", float("nan"))
        s1 = d.get("scale_eq_1.0", float("nan"))
        gm = d.get("gap_mean", float("nan"))
        bbm = d.get("basket_beta_mean", float("nan"))
        bbs = d.get("basket_beta_std", float("nan"))
        print(
            f"| {d['name']} | {s0:.1%} | {s5:.1%} | {s1:.1%} | "
            f"{gm:.4f} | {bbm:+.3f} | {bbs:.3f} |"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
