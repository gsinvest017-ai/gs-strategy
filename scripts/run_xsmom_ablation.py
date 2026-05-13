"""Run xsmom_stkfut_rmt under multiple parameter overrides for ablation study.

Loads the base config, applies per-variant overrides to the `params` block,
runs each variant, and writes a result pickle per variant. Outputs a metrics
table at the end.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_ablation.py
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


VARIANTS = [
    ("baseline_m10", {}),  # current config.yaml as-is (calibrated thresholds)
    ("no_hedge", {"hedge_with_tx": False}),
    ("wide_decile", {"long_decile": 0.2, "short_decile": 0.2}),
    ("reverse", {"reverse_momentum": True}),
    ("reverse_no_hedge", {"reverse_momentum": True, "hedge_with_tx": False}),
    # M12 long-only variants — drop the short leg, since Taiwan stock-fut
    # shorts plausibly carry materially higher cost than longs.
    ("long_only_mom", {"long_only": True}),
    ("long_only_mom_wide", {"long_only": True, "long_decile": 0.2}),
    ("long_only_reverse", {"long_only": True, "reverse_momentum": True}),
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
    cummax = pv.cummax()
    max_dd = (pv / cummax - 1).min()
    return {
        "CAGR": cagr,
        "Sharpe": sharpe,
        "Max_DD": max_dd,
        "total_return": total_ret,
        "final": float(pv.iloc[-1]),
    }


def main() -> int:
    with open(BASE_CONFIG, "r", encoding="utf-8") as fh:
        base = yaml.safe_load(fh)

    results = []
    for name, overrides in VARIANTS:
        cfg = yaml.safe_load(yaml.safe_dump(base))  # deep copy
        cfg.setdefault("params", {}).update(overrides)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(cfg, tmp)
            tmp_path = tmp.name
        out_path = Path(f"/tmp/xsmom_m11_{name}_result.pkl")
        print(f"[{name}] overrides={overrides} -> {out_path}", flush=True)
        df = run_strategy_from_config(STRATEGY, tmp_path, out_path)
        s = _summary(df)
        s["name"] = name
        results.append(s)
        print(
            f"[{name}] CAGR={s['CAGR']:.2%} Sharpe={s['Sharpe']:.3f} "
            f"Max_DD={s['Max_DD']:.2%}",
            flush=True,
        )

    print()
    print("| variant | CAGR | Sharpe | Max_DD | final |")
    print("|---|---:|---:|---:|---:|")
    for r in results:
        print(
            f"| {r['name']} | {r['CAGR']:.2%} | {r['Sharpe']:.3f} | "
            f"{r['Max_DD']:.2%} | {r['final']:,.0f} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
