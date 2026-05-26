"""Compare pooled vs sector-neutral cross-sectional momentum on the M14 60-root
bundle (M21).

M20 split the 60-root universe into TECH / FIN / TRAD sector-restricted
sub-universes and confirmed each absolute-return-wise had no alpha — but
sector-restricted ≠ sector-neutral. A pooled cross-section ranks all 60 roots
together, so a TSMC momentum signal can be dominated by a stronger Hon Hai or
masked by a dispersed financial-leg. *Sector-neutral* construction ranks
momentum within each sector independently and picks the per-sector top/bottom
decile, then unions across sectors. If TECH-relative momentum is real but FIN
relative momentum is noise, sector-neutral should preserve the TECH alpha
while diluting the FIN noise rather than mixing them.

This script:
  1. Loads strategies/xsmom_stkfut_rmt/config.yaml (M17 canonical: 60 roots,
     beta-neutral hedge, calibrated commission, RMT thresholds 0.049/0.037).
  2. Runs two variants on the same start/end/bundle/cost stack:
       baseline  — sector_neutral=False (identical to M17 canonical)
       sn        — sector_neutral=True with the TECH/FIN/TRAD partition from
                   scripts/run_xsmom_sectors.py (15/12/33 roots, total 60)
  3. Prints a comparison metrics table + regime diagnostics, persists each
     result to /tmp/xsmom_m21_<variant>_result.pkl.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_sector_neutral.py
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


# Same sector partition used by scripts/run_xsmom_sectors.py (M20).
# Keeping a verbatim copy here rather than importing it: the M20 script
# computes a different thing (sector-restricted backtests); we want to
# import its data without picking up its module-level side effects.
SECTOR_MAP: dict[str, str] = {
    # TECH (15 roots): semis + EMS/ODM + display + PC OEM
    "QFF": "TECH", "CCF": "TECH", "DIF": "TECH", "CYF": "TECH",
    "PUF": "TECH", "DUF": "TECH", "DHF": "TECH", "DKF": "TECH",
    "DXF": "TECH", "CGF": "TECH", "DSF": "TECH", "CHF": "TECH",
    "DQF": "TECH", "CWF": "TECH", "QRF": "TECH",
    # FIN (12 roots): financial holdings + banks
    "CEF": "FIN", "CJF": "FIN", "CKF": "FIN", "CLF": "FIN",
    "CMF": "FIN", "CNF": "FIN", "DCF": "FIN", "DDF": "FIN",
    "DEF": "FIN", "DNF": "FIN", "DOF": "FIN", "DPF": "FIN",
    # TRAD (33 roots): petrochem, steel, food, telco, shipping, cement,
    # textile, auto-parts, machinery, etc.
    "CAF": "TRAD", "CBF": "TRAD", "CFF": "TRAD", "CQF": "TRAD",
    "CRF": "TRAD", "CSF": "TRAD", "CUF": "TRAD", "CXF": "TRAD",
    "CZF": "TRAD", "DAF": "TRAD", "DBF": "TRAD", "DFF": "TRAD",
    "DGF": "TRAD", "DLF": "TRAD", "DWF": "TRAD", "DYF": "TRAD",
    "DZF": "TRAD", "EEF": "TRAD", "EGF": "TRAD", "EHF": "TRAD",
    "EKF": "TRAD", "EMF": "TRAD", "EOF": "TRAD", "EPF": "TRAD",
    "ERF": "TRAD", "EYF": "TRAD", "EZF": "TRAD", "FBF": "TRAD",
    "FCF": "TRAD", "FEF": "TRAD", "QMF": "TRAD", "SVF": "TRAD",
    "FKF": "TRAD",
}


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
    n_tx = int(
        df.get("orders", pd.Series(dtype=object))
        .map(lambda x: len(x) if isinstance(x, list) else 0)
        .sum()
    )
    return {
        "years": years,
        "CAGR": cagr,
        "ann_vol": ann_vol,
        "Sharpe": sharpe,
        "Max_DD": max_dd,
        "total_return": total_ret,
        "final": float(pv.iloc[-1]),
        "n_days": int(len(df)),
        "n_tx": n_tx,
    }


def _regime_diag(df: pd.DataFrame) -> dict:
    out: dict = {}
    for col in ("regime_scale", "basket_beta", "gap", "n_universe"):
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


def _build_variant_cfg(base: dict, sector_neutral: bool) -> dict:
    cfg = yaml.safe_load(yaml.safe_dump(base))  # deep copy
    cfg["params"]["sector_neutral"] = sector_neutral
    if sector_neutral:
        cfg["params"]["sector_map"] = dict(SECTOR_MAP)
    return cfg


def main() -> int:
    with open(BASE_CONFIG, "r", encoding="utf-8") as fh:
        base = yaml.safe_load(fh)

    # Coverage check: every root in the base universe should have a sector.
    universe = set(base["params"]["universe_roots"])
    mapped = set(SECTOR_MAP) & universe
    missing = sorted(universe - set(SECTOR_MAP))
    if missing:
        print(f"WARN: sector_map missing roots from base universe: {missing}",
              flush=True)
    print(
        f"Universe size: {len(universe)} | sector_map covers {len(mapped)} | "
        f"TECH={sum(1 for v in SECTOR_MAP.values() if v=='TECH')} "
        f"FIN={sum(1 for v in SECTOR_MAP.values() if v=='FIN')} "
        f"TRAD={sum(1 for v in SECTOR_MAP.values() if v=='TRAD')}",
        flush=True,
    )

    variants = [
        ("baseline", False),
        ("sn", True),
    ]

    results = []
    diagnostics = []
    for name, sn in variants:
        cfg = _build_variant_cfg(base, sector_neutral=sn)
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(cfg, tmp)
            tmp_path = tmp.name
        out_path = Path(f"/tmp/xsmom_m21_{name}_result.pkl")
        print(f"\n[{name}] sector_neutral={sn} -> {out_path}", flush=True)

        df = run_strategy_from_config(STRATEGY, tmp_path, out_path)

        s = _summary(df)
        s["name"] = name
        results.append(s)
        d = _regime_diag(df)
        d["name"] = name
        diagnostics.append(d)

        print(
            f"[{name}] years={s['years']:.2f} CAGR={s['CAGR']:.2%} "
            f"Sharpe={s['Sharpe']:.3f} vol={s['ann_vol']:.2%} "
            f"Max_DD={s['Max_DD']:.2%} final={s['final']:,.0f} "
            f"n_tx={s['n_tx']}",
            flush=True,
        )

    print()
    print("## M21 pooled vs sector-neutral metrics")
    print()
    print("| variant | years | CAGR | ann_vol | Sharpe | Max_DD | n_days | n_tx | final |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        print(
            f"| {r['name']} | {r['years']:.2f} | {r['CAGR']:.2%} | "
            f"{r['ann_vol']:.2%} | {r['Sharpe']:.3f} | {r['Max_DD']:.2%} | "
            f"{r['n_days']} | {r['n_tx']} | {r['final']:,.0f} |"
        )

    print()
    print("## Regime diagnostics")
    print()
    print(
        "| variant | scale=0 | scale=0.5 | scale=1.0 | gap_mean | gap_std | "
        "basket_beta_mean | basket_beta_std | n_universe_mean |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for d in diagnostics:
        s0 = d.get("scale_eq_0.0", float("nan"))
        s5 = d.get("scale_eq_0.5", float("nan"))
        s1 = d.get("scale_eq_1.0", float("nan"))
        gm = d.get("gap_mean", float("nan"))
        gs = d.get("gap_std", float("nan"))
        bbm = d.get("basket_beta_mean", float("nan"))
        bbs = d.get("basket_beta_std", float("nan"))
        nu = d.get("n_universe_mean", float("nan"))
        print(
            f"| {d['name']} | {s0:.1%} | {s5:.1%} | {s1:.1%} | "
            f"{gm:.4f} | {gs:.4f} | {bbm:+.3f} | {bbs:.3f} | {nu:.1f} |"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
