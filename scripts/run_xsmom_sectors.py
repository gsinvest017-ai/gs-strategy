"""Run xsmom_stkfut_rmt on sector-split sub-universes of the M14 60-root bundle.

M11-M19 confirmed the strategy has no alpha on the **pooled** 60-root universe
across 2020-2026 (HAC t = -7.6, p < 1e-14). One open question from M19's
"後續方向": is the null result driven by an aggregate cross-section that
*mixes* sectors with very different momentum behaviour? If e.g. Taiwan
semiconductor stock-futures *do* exhibit profitable cross-sectional momentum
but financial stock-futures mean-revert, the pooled signal averages out.

This script splits the 60-root universe into three sector buckets and reruns
the M17-canonical config (60-root bundle, calibrated commission, beta-neutral
hedge, RMT thresholds 0.049/0.037) restricted to each bucket:

  * TECH  — semis (2330/2303/2337/2408/2454/2448), EMS/ODM
            (2317/2382/3231/2324/2353), display (2409/3481/2352),
            PC OEM (2357), memory niche (2337/2408)
  * FIN   — 12 financial holdings + banks (2881/2880/2882/2886/2887/2891
            /2801/2888/2890/2884/2885/2892)
  * TRAD  — everything else: petrochem, steel, food, telco, shipping,
            cement, textile, auto-parts, machinery, etc.

min_universe is lowered to 10 so each sector can fully participate (FIN has
12 names; TECH has 16; TRAD has 32). All other params held identical to
M17 canonical for an apples-to-apples comparison.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_sectors.py
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


# Sector partition of the M14 60-root universe.
# Classification is based on TWSE industry code + plain-English business
# description from public filings (no proprietary mapping). Borderline
# cases (e.g. CUF 2323 中環 optical media — IT-adjacent but legacy)
# go to TRAD to keep TECH "modern semiconductor + downstream" pure.
SECTORS: dict[str, list[str]] = {
    "TECH": [
        "QFF",  # 2330 TSMC          — foundry
        "CCF",  # 2303 UMC           — foundry
        "DIF",  # 2337 Macronix      — memory (NOR/NAND)
        "CYF",  # 2408 Nanya Tech    — DRAM
        "PUF",  # 2454 MediaTek      — fabless
        "DUF",  # 2448 Epistar       — LED chips
        "DHF",  # 2317 Hon Hai       — EMS
        "DKF",  # 2382 Quanta        — laptop ODM
        "DXF",  # 3231 Wistron       — ODM
        "CGF",  # 2324 Compal        — NB ODM
        "DSF",  # 2353 Acer          — PC
        "CHF",  # 2409 AUO           — display
        "DQF",  # 3481 Innolux       — display
        "CWF",  # 2352 BenQ/Qisda    — display + medical electronics
        "QRF",  # 2357 ASUS          — PC/laptop OEM
    ],
    "FIN": [
        "CEF",  # 2881 Fubon FHC
        "CJF",  # 2880 Hua Nan FHC
        "CKF",  # 2882 Cathay FHC
        "CLF",  # 2886 Mega FHC
        "CMF",  # 2887 Taishin FHC
        "CNF",  # 2891 CTBC FHC
        "DCF",  # 2801 Chang Hwa Bank
        "DDF",  # 2888 Shin Kong FHC
        "DEF",  # 2890 SinoPac FHC
        "DNF",  # 2884 E.Sun FHC
        "DOF",  # 2885 Yuanta FHC
        "DPF",  # 2892 First FHC
    ],
    "TRAD": [
        "CAF",  # 1303 Nan Ya Plastics
        "CBF",  # 2002 China Steel
        "CFF",  # 1301 Formosa Plastics
        "CQF",  # 1216 Uni-President
        "CRF",  # 1402 Far Eastern New Century — textile
        "CSF",  # 1605 Walsin — wire
        "CUF",  # 2323 Microelectronics Tech — optical media (legacy)
        "CXF",  # 2371 Tatung — legacy electrical conglomerate
        "CZF",  # 2603 Evergreen Marine
        "DAF",  # 2609 Yang Ming Marine
        "DBF",  # 2610 China Airlines
        "DFF",  # 1101 Taiwan Cement
        "DGF",  # 1326 Formosa Chemicals & Fibre
        "DLF",  # 2412 Chunghwa Telecom
        "DWF",  # 2915 Ruentex Industries
        "DYF",  # 1102 Asia Cement
        "DZF",  # 1210 Great Wall Enterprise (food)
        "EEF",  # 1312 USI Corp (petrochem)
        "EGF",  # 1314 China Petrochemical Development
        "EHF",  # 1319 Tung Yang Group (auto parts)
        "EKF",  # 1440 South Asia Textile
        "EMF",  # 1504 Teco Electric
        "EOF",  # 1560 Kinik (abrasives)
        "EPF",  # 1590 Airtac International
        "ERF",  # 1702 Namchow Group (food)
        "EYF",  # 1718 China Man-Made Fiber
        "EZF",  # 1722 Taiwan Fertilizer
        "FBF",  # 2006 Tung Ho Steel
        "FCF",  # 2014 Chung Hung Steel
        "FEF",  # 2027 Ta Chen Stainless
        "QMF",  # 2049 HIWIN — precision machinery
        "SVF",  # 2059 Chuan Hwa (server rails — borderline tech, kept TRAD)
        "FKF",  # 2105 Cheng Shin Rubber (tires)
    ],
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
    n_tx = int(df.get("orders", pd.Series(dtype=object)).map(lambda x: len(x) if isinstance(x, list) else 0).sum())
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

    # Sanity: ensure all sector roots are in the base universe (the bundle).
    base_set = set(base["params"]["universe_roots"])
    for sector, roots in SECTORS.items():
        missing = [r for r in roots if r not in base_set]
        if missing:
            print(f"WARN: {sector} roots not in base universe: {missing}", flush=True)
    total = sum(len(v) for v in SECTORS.values())
    print(f"Sector partition: TECH={len(SECTORS['TECH'])} FIN={len(SECTORS['FIN'])} "
          f"TRAD={len(SECTORS['TRAD'])} total={total} (base={len(base_set)})",
          flush=True)

    results = []
    diagnostics = []
    for sector, roots in SECTORS.items():
        cfg = yaml.safe_load(yaml.safe_dump(base))  # deep copy
        cfg["params"]["universe_roots"] = list(roots)
        # FIN has only 12 names — lower min_universe so the strategy can still
        # rebalance even if 1-2 roots are temporarily untradeable.
        cfg["params"]["min_universe"] = 10

        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(cfg, tmp)
            tmp_path = tmp.name
        out_path = Path(f"/tmp/xsmom_m20_sector_{sector}_result.pkl")
        print(f"\n[{sector}] roots={len(roots)} -> {out_path}", flush=True)

        df = run_strategy_from_config(STRATEGY, tmp_path, out_path)

        s = _summary(df)
        s["name"] = sector
        s["n_roots"] = len(roots)
        results.append(s)

        d = _regime_diag(df)
        d["name"] = sector
        diagnostics.append(d)

        print(
            f"[{sector}] years={s['years']:.2f} CAGR={s['CAGR']:.2%} "
            f"Sharpe={s['Sharpe']:.3f} vol={s['ann_vol']:.2%} "
            f"Max_DD={s['Max_DD']:.2%} final={s['final']:,.0f}",
            flush=True,
        )

    print()
    print("## Sector-split metrics")
    print()
    print("| sector | roots | years | CAGR | ann_vol | Sharpe | Max_DD | n_days | final |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        print(
            f"| {r['name']} | {r['n_roots']} | {r['years']:.2f} | {r['CAGR']:.2%} | "
            f"{r['ann_vol']:.2%} | {r['Sharpe']:.3f} | {r['Max_DD']:.2%} | "
            f"{r['n_days']} | {r['final']:,.0f} |"
        )

    print()
    print("## Regime diagnostics per sector")
    print()
    print(
        "| sector | scale=0 | scale=0.5 | scale=1.0 | gap_mean | gap_std | basket_beta_mean | basket_beta_std |"
    )
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for d in diagnostics:
        s0 = d.get("scale_eq_0.0", float("nan"))
        s5 = d.get("scale_eq_0.5", float("nan"))
        s1 = d.get("scale_eq_1.0", float("nan"))
        gm = d.get("gap_mean", float("nan"))
        gs = d.get("gap_std", float("nan"))
        bbm = d.get("basket_beta_mean", float("nan"))
        bbs = d.get("basket_beta_std", float("nan"))
        print(
            f"| {d['name']} | {s0:.1%} | {s5:.1%} | {s1:.1%} | "
            f"{gm:.4f} | {gs:.4f} | {bbm:+.3f} | {bbs:.3f} |"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
