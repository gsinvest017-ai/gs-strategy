#!/usr/bin/env python3
"""Export the TWSE/TPEx disposition-stock event calendar to a bundle sidecar.

Reads ``stock_attrs_status`` from the quantdata service, collapses the daily
``is_disposition_bool`` flag into episodes, and writes one row per tradable
event to ``strategies/disposition_rebound_tw/assets/events.csv``.

Why a CSV sidecar rather than a live query at backtest time: the bundle has to
stay reproducible and runnable without network access to the LAN service, and
strategy-import-spec v1 §3.3 blesses ``assets/`` for exactly this.

Every column written here is knowable at the close of the entry date. The
episode's *length* is deliberately NOT exported as a signal input: a disposition
can be extended, so its realised length is future information. ``severity`` is
derived from the pre-announced call-auction interval instead.

Usage::

    python scripts/export_disposition_events.py                     # 2021-01-01..today
    python scripts/export_disposition_events.py --start 2021-01-01 --end 2026-08-27
    python scripts/export_disposition_events.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from strategies._common import qd  # noqa: E402

DEFAULT_OUT = REPO / "strategies" / "disposition_rebound_tw" / "assets" / "events.csv"

#: The disposition flag is only populated from 2021 onward in stock_attrs_status
#: (verified: 2015-2020 return exactly zero disposition stock-days). Starting a
#: study earlier silently yields an empty sample rather than an error.
FLAG_COVERAGE_START = "2021-01-01"


def build_episodes(attrs: pd.DataFrame, max_gap_days: int = 5) -> pd.DataFrame:
    """Collapse daily disposition flags into contiguous episodes."""
    d = attrs[attrs["is_disposition_bool"].astype(bool)].copy()
    d = d.sort_values(["stock_id", "trading_date"])
    if d.empty:
        return pd.DataFrame()
    gap = d.groupby("stock_id")["trading_date"].diff().dt.days.fillna(9999)
    d["_ep"] = (gap > max_gap_days).astype(int).groupby(d["stock_id"]).cumsum()
    ep = (
        d.groupby(["stock_id", "_ep"])
        .agg(start=("trading_date", "min"),
             end=("trading_date", "max"),
             sessions=("trading_date", "size"))
        .reset_index()
        .drop(columns="_ep")
    )
    return ep.sort_values(["start", "stock_id"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default=FLAG_COVERAGE_START)
    ap.add_argument("--end", default=pd.Timestamp.today().date().isoformat())
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if pd.Timestamp(args.start) < pd.Timestamp(FLAG_COVERAGE_START):
        print(f"warning: is_disposition_bool is empty before {FLAG_COVERAGE_START}; "
              f"rows before that date will simply be absent, not an error",
              file=sys.stderr)

    print(f"pulling stock_attrs_status {args.start}..{args.end}", file=sys.stderr)
    attrs = qd.attrs_status(args.start, args.end, events_only=True)
    for c in ("is_attention_bool", "is_disposition_bool", "is_no_daytrade_bool"):
        if c in attrs.columns:
            attrs[c] = attrs[c].astype("boolean").fillna(False).astype(bool)

    ep = build_episodes(attrs)
    if ep.empty:
        print("no disposition episodes found", file=sys.stderr)
        return 1
    print(f"episodes: {len(ep):,} across {ep['stock_id'].nunique():,} stocks",
          file=sys.stderr)

    # severity from the announced call-auction interval. NOTE: the column is
    # named match_interval_sec but carries MINUTES (values 5 and 20, matching
    # the 5-minute first-disposition and 20-minute repeat-disposition rules).
    try:
        detail = qd.trading_attrs_detail(args.start, args.end)
        det = detail[detail["is_disposition"].astype(str).str.upper().isin(["Y", "TRUE", "1"])]
        sev = (det.groupby(["stock_id", "trading_date"])["match_interval_sec"]
               .first().reset_index()
               .rename(columns={"match_interval_sec": "auction_interval_min"}))
        ep = ep.merge(sev, left_on=["stock_id", "start"],
                      right_on=["stock_id", "trading_date"], how="left") \
               .drop(columns=["trading_date"], errors="ignore")
    except Exception as exc:  # pragma: no cover - service-dependent
        print(f"severity lookup failed ({exc}); auction_interval_min left blank",
              file=sys.stderr)
        ep["auction_interval_min"] = pd.NA

    # pre-event momentum, read at the session BEFORE entry so it is ex-ante
    fac = qd.cached_sql(
        "SELECT trading_date, symbol, ret_20d FROM stock_factor_daily "
        "WHERE trading_date BETWEEN DATE '{start}' AND DATE '{end}'",
        start=args.start, end=args.end, tag="ev_mom",
    )
    fac["trading_date"] = pd.to_datetime(fac["trading_date"])
    fac["symbol"] = fac["symbol"].astype(str)
    sessions = pd.Index(sorted(fac["trading_date"].unique()))
    prev = {d: sessions[i - 1] for i, d in enumerate(sessions) if i > 0}
    ep["_prev"] = ep["start"].map(prev)
    ep = ep.merge(fac.rename(columns={"symbol": "stock_id", "ret_20d": "runup_20d"}),
                  left_on=["stock_id", "_prev"], right_on=["stock_id", "trading_date"],
                  how="left").drop(columns=["_prev", "trading_date"], errors="ignore")

    out = pd.DataFrame({
        "date": ep["start"].dt.date,
        "symbol": ep["stock_id"].astype(str),
        "direction": "long",
        # `strength` is the template's generic gate. Pre-event run-up is the one
        # ex-ante intensity measure available; it is NOT a claim that bigger
        # run-ups pay more -- that is left for the caller to threshold on.
        "strength": ep["runup_20d"].astype(float).round(4),
        "auction_interval_min": ep["auction_interval_min"],
        # FUTURE INFORMATION -- diagnostics only, never a signal input.
        # A disposition's length is announced up front but can be extended, and
        # this table cannot tell the announced length from the realised one. Any
        # rule that reads these two columns at entry time is looking ahead.
        "realised_end": ep["end"].dt.date,
        "realised_sessions": ep["sessions"],
    })
    out = out.dropna(subset=["date", "symbol"]).sort_values(["date", "symbol"])

    print(out.head(8).to_string(index=False), file=sys.stderr)
    print(f"\nrows: {len(out):,}   date range {out['date'].min()}..{out['date'].max()}",
          file=sys.stderr)
    if args.dry_run:
        print("--dry-run: nothing written", file=sys.stderr)
        return 0

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dest, index=False)
    print(f"wrote {dest} ({len(out):,} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
