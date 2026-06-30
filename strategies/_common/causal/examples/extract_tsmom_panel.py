"""Extract a REAL TSMOM factor panel from the tquant_future bundle.

Runs a minimal zipline algo that, each month-start, records for TX & MTX:
  * mom   — signed 12-1 momentum factor (the treatment under test)
  * vol   — EWMA annualised vol            (confounder)
  * rev   — last-month log return          (confounder: short-term reversal)
  * px    — back-adjusted continuous close  (to build forward returns)

Post-processes the recorded results into a long panel with the NEXT-month
forward return as outcome, and writes data/causal/tsmom_panel.parquet — the
input to the DoubleML + DoWhy causal de-overfitting loop.

Run (zipline env):
    cd /home/kevin/gs-strategy
    .venv/bin/python -m strategies._common.causal.examples.extract_tsmom_panel
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from zipline import run_algorithm
from zipline.api import date_rules, record, schedule_function, time_rules
from zipline.utils.calendar_utils import get_calendar

from strategies._common.futures_setup import (
    apply_taiwan_futures_costs,
    make_continuous_taiwan_futures,
)

ROOTS = ["TX", "MTX"]
LOOKBACK, SKIP, VOL_COM = 252, 21, 60
OUT = Path("data/causal/tsmom_panel.parquet")


def _signed_momentum(closes, lookback, skip):
    if len(closes) < lookback + skip + 1:
        return np.nan
    end = closes[-skip - 1] if skip > 0 else closes[-1]
    start = closes[-skip - 1 - lookback]
    if start <= 0 or end <= 0:
        return np.nan
    return float(np.log(end) - np.log(start))


def _ewma_vol(log_returns, com):
    if len(log_returns) < 2:
        return np.nan
    w = np.exp(-np.arange(len(log_returns))[::-1] / com)
    w /= w.sum()
    mu = float((w * log_returns).sum())
    var = float((w * (log_returns - mu) ** 2).sum())
    return float(np.sqrt(max(var, 0.0) * 252.0))


def initialize(context):
    apply_taiwan_futures_costs()
    context.cont = dict(zip(ROOTS, make_continuous_taiwan_futures(ROOTS)))
    schedule_function(_record, date_rules.month_start(), time_rules.market_close())


def _record(context, data):
    n_needed = LOOKBACK + SKIP + 5
    rec = {}
    for root, cont in context.cont.items():
        closes = data.history(cont, "close", n_needed, "1d").dropna().values
        if len(closes) < n_needed - 5:
            continue
        log_ret = np.diff(np.log(closes))
        rec[f"mom_{root}"] = _signed_momentum(closes, LOOKBACK, SKIP)
        rec[f"vol_{root}"] = _ewma_vol(log_ret[-VOL_COM * 4:], VOL_COM)
        rec[f"rev_{root}"] = float(np.sum(log_ret[-21:]))
        rec[f"px_{root}"] = float(closes[-1])
    if rec:
        record(**rec)


def handle_data(context, data):
    return


def _to_panel(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for root in ROOTS:
        cols = [f"mom_{root}", f"vol_{root}", f"rev_{root}", f"px_{root}"]
        if not set(cols).issubset(results.columns):
            continue
        sub = results[cols].dropna().copy()
        sub.columns = ["mom", "vol", "rev", "px"]
        # monthly observations only (record fires at month start)
        sub = sub[~sub.index.to_period("M").duplicated(keep="first")]
        sub["fwd_ret"] = np.log(sub["px"].shift(-1) / sub["px"])
        other = "MTX" if root == "TX" else "TX"
        sub["root"] = root
        sub["other_mom"] = np.nan  # filled below after both roots built
        rows.append((root, sub))
    # cross-fill other_mom by date
    by_date_mom = {}
    for root, sub in rows:
        for ts, v in sub["mom"].items():
            by_date_mom.setdefault(ts, {})[root] = v
    panels = []
    for root, sub in rows:
        other = "MTX" if root == "TX" else "TX"
        sub = sub.copy()
        sub["other_mom"] = [by_date_mom.get(ts, {}).get(other, np.nan) for ts in sub.index]
        panels.append(sub.reset_index().rename(columns={"index": "date"}))
    panel = pd.concat(panels, ignore_index=True)
    return panel.dropna(subset=["mom", "fwd_ret", "vol", "rev"])


def main():
    cal = get_calendar("TEJ_morning_future")
    results = run_algorithm(
        start=pd.Timestamp("2019-01-01", tz="UTC"),
        end=pd.Timestamp("2026-04-30", tz="UTC"),
        initialize=initialize,
        handle_data=handle_data,
        capital_base=10_000_000,
        bundle="tquant_future",
        trading_calendar=cal,
        data_frequency="daily",
    )
    panel = _to_panel(results)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT, index=False)
    print(f"wrote {OUT}  rows={len(panel)}  roots={panel['root'].unique().tolist()}")
    print(panel.head(8).to_string())


if __name__ == "__main__":
    main()
