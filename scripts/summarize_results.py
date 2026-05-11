"""Summarize one or more zipline result pickles into a metrics table.

Usage:
    .venv-bt/bin/python scripts/summarize_results.py /tmp/*_result.pkl
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Auto-load .env so that pickle.load() can import zipline (which transitively
# requires TEJAPI_KEY at module-import time via exchange_calendars).
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

TRADING_DAYS_PER_YEAR = 252


def summarize(path: Path) -> dict:
    df = pd.read_pickle(path)
    pv = df["portfolio_value"]
    daily_ret = df["returns"]
    years = (df.index[-1] - df.index[0]).days / 365.25
    total_ret = pv.iloc[-1] / pv.iloc[0] - 1
    cagr = (1 + total_ret) ** (1 / years) - 1 if years > 0 else float("nan")
    sharpe = (
        daily_ret.mean() / daily_ret.std() * np.sqrt(TRADING_DAYS_PER_YEAR)
        if daily_ret.std() > 0
        else float("nan")
    )
    n_tx = sum(len(t) for t in df["transactions"] if isinstance(t, list))
    return {
        "name": path.stem.replace("_result", ""),
        "start": df.index[0].date(),
        "end": df.index[-1].date(),
        "years": round(years, 2),
        "capital_base": int(pv.iloc[0]),
        "final": int(pv.iloc[-1]),
        "total_return": f"{total_ret:.2%}",
        "CAGR": f"{cagr:.2%}",
        "ann_vol": f"{daily_ret.std() * np.sqrt(TRADING_DAYS_PER_YEAR):.2%}",
        "Sharpe": f"{sharpe:.3f}",
        "Max_DD": f"{df['max_drawdown'].min():.2%}",
        "n_tx": n_tx,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pickles", nargs="+", type=Path)
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Emit a markdown table instead of plain dataframe",
    )
    args = parser.parse_args()

    rows = [summarize(p) for p in args.pickles]
    df = pd.DataFrame(rows)
    if args.markdown:
        print(df.to_markdown(index=False))
    else:
        print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
