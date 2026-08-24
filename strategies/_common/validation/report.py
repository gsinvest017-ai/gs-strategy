"""Verification report builder — turn a zipline perf frame into the
``validation:`` block promised by strategy-import-spec v1.2 §2.

Reuses the self-written statistics in this package (sharpe.py: PSR/DSR;
see also pbo.py / cpcv.py). The point: a strategy's Sharpe should never be
shown without its *deflated* counterpart once multiple trials were tried.

CLI::

    python -m strategies._common.validation.report PERF.parquet|.pkl \
        [--n-trials N] [--periods-per-year 252] [-o out.json]

Accepts dashboard runner parquet output or a raw zipline perf pickle.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .sharpe import (
    annualized_sharpe,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)

SCHEMA = "validation-report-v1"


def load_perf(path: Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"perf file not found: {path}")
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    return pd.read_pickle(path)


def max_drawdown(returns: pd.Series) -> float:
    equity = (1 + returns.fillna(0)).cumprod()
    return float((equity / equity.cummax() - 1).min())


def cagr(returns: pd.Series, periods_per_year: int = 252) -> float:
    r = returns.fillna(0)
    years = len(r) / periods_per_year
    total = float((1 + r).prod())
    if years <= 0 or total <= 0:
        return float("nan")
    return total ** (1 / years) - 1


def build_report(perf: pd.DataFrame, *, n_trials: int = 1,
                 periods_per_year: int = 252,
                 returns_col: str = "returns") -> dict:
    if returns_col not in perf.columns:
        raise ValueError(
            f"perf frame has no {returns_col!r} column "
            f"(has: {list(perf.columns)[:12]}...)")
    returns = pd.Series(perf[returns_col]).astype(float).replace(
        [np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 20:
        raise ValueError(
            f"too few return observations ({len(returns)}) for validation")

    return {
        "schema": SCHEMA,
        "n_days": int(len(returns)),
        "total_return": float((1 + returns).prod() - 1),
        "cagr": cagr(returns, periods_per_year),
        "annualized_sharpe": annualized_sharpe(returns, periods_per_year),
        "max_drawdown": max_drawdown(returns),
        "psr": probabilistic_sharpe_ratio(returns),
        "dsr": deflated_sharpe_ratio(returns, n_trials=max(int(n_trials), 1)),
        "n_trials": max(int(n_trials), 1),
    }


def write_sidecar_for(perf_path: Path, *, n_trials: int | None = None,
                      periods_per_year: int = 252) -> Path | None:
    """Best-effort: write ``<perf>.validation.json`` next to a perf file.

    Validation must never break a completed backtest, so this swallows all
    errors and returns the sidecar path on success / None on failure.
    """
    try:
        report = build_report(load_perf(Path(perf_path)),
                              n_trials=int(n_trials or 1),
                              periods_per_year=periods_per_year)
        sidecar = Path(perf_path).with_name(
            Path(perf_path).name + ".validation.json")
        sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        return sidecar
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validation.report")
    parser.add_argument("perf", type=Path)
    parser.add_argument("--n-trials", type=int, default=1,
                        help="how many trials produced this backtest "
                             "(deflates SR)")
    parser.add_argument("--periods-per-year", type=int, default=252)
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        report = build_report(load_perf(args.perf),
                              n_trials=args.n_trials,
                              periods_per_year=args.periods_per_year)
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
