"""quantdata REST client — the *fresh* source of Taiwan market data.

Why this module exists
----------------------
There are three copies of QUANTDATA on this network and they do not agree:

* ``~/gs-scraper/QUANTDATA`` (local parquet lakehouse) — last written 2026-06,
  so anything read from it is silently ~3 months stale. It does not error; it
  just answers an old question.
* the gb10 host's own on-disk copy;
* the **REST/SQL service** fronted at ``http://quantdata.lan/api/v1`` (gb10,
  192.168.11.90), which is refreshed daily.

Only the third is current, so backtests read through this module, not through
``pandas.read_parquet``.  ``strategies/_common/quantdata.py`` (the older
adapter) still reads the local lakehouse and is kept for the equity-universe
derivation it already powers; new code should prefer this module.

Network reality (documented because it *will* bite you)
-------------------------------------------------------
``quantdata.lan`` resolves on the Windows side but **not inside WSL** — WSL's
``/etc/resolv.conf`` points at 8.8.8.8/1.1.1.1, which know nothing about the
``.lan`` zone.  Rather than mutate ``/etc/hosts`` (a machine-wide change for a
library's benefit), this client detects the resolution failure and retries
against the host's IP with an explicit ``Host:`` header, which is exactly what
the reverse proxy in front of the service routes on.  Override either half with
``QD_API_BASE`` / ``QD_HOST_IP`` when the topology changes.

Server-side limits
------------------
The ``/sql`` endpoint enforces a **30-second query timeout** server-side and
returns HTTP 400 with ``{"error": "query exceeded 30s timeout"}``.  Aggregations
over the multi-million-row daily tables routinely exceed it.  ``sql_by_year``
therefore splits a ranged query into per-year queries and concatenates; use it
for anything touching a full history.

Point-in-time semantics
-----------------------
Every reader here filters on ``trading_date`` only.  None of these tables carry
a separate announcement/revision timestamp, so a row dated *d* is assumed known
at the close of *d* — true for prices, bars and the TWSE attribute files, but
**not** for anything restated (fundamentals, revenue).  Do not reach for the
fundamentals tables through this module without adding as-of handling first.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
import requests

DEFAULT_BASE = "http://quantdata.lan/api/v1"
DEFAULT_HOST_IP = "192.168.11.90"

#: The server kills a query at 30s. Chunk anything that might approach it.
SERVER_QUERY_TIMEOUT_S = 30

#: Local parquet cache so a re-run of a backtest does not re-hit the service
#: (and so a backtest stays reproducible if the service is down).
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "qd_cache"

_DNS_OK: bool | None = None


def api_base() -> str:
    return os.environ.get("QD_API_BASE", DEFAULT_BASE).rstrip("/")


def host_ip() -> str:
    return os.environ.get("QD_HOST_IP", DEFAULT_HOST_IP)


def _dns_resolves(hostname: str) -> bool:
    global _DNS_OK
    if _DNS_OK is None:
        try:
            socket.getaddrinfo(hostname, 80)
            _DNS_OK = True
        except socket.gaierror:
            _DNS_OK = False
    return _DNS_OK


def _endpoint(path: str) -> tuple[str, dict[str, str]]:
    """Return ``(url, extra_headers)``, falling back to IP+Host when DNS fails."""
    base = api_base()
    from urllib.parse import urlsplit

    parts = urlsplit(base)
    hostname = parts.hostname or ""
    if hostname and not _dns_resolves(hostname):
        ip_base = base.replace(hostname, host_ip(), 1)
        return f"{ip_base}/{path.lstrip('/')}", {"Host": hostname}
    return f"{base}/{path.lstrip('/')}", {}


class QuantdataError(RuntimeError):
    """A quantdata request failed. Carries the server's message verbatim."""


def _post_sql(query: str, *, timeout: int, retries: int) -> dict[str, Any]:
    url, extra = _endpoint("sql")
    headers = {"Content-Type": "application/json", **extra}
    payload = json.dumps({"sql": query})
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, data=payload, headers=headers, timeout=timeout)
        except requests.RequestException as exc:  # network flake -> retry
            last = exc
            time.sleep(1.5 * (attempt + 1))
            continue
        if resp.status_code == 200:
            return resp.json()
        # The service reports its own errors as JSON with HTTP 400; surface the
        # message rather than a bare status code, because "query exceeded 30s
        # timeout" tells you to chunk and "Binder Error" tells you to fix SQL.
        try:
            msg = resp.json().get("error", resp.text[:400])
        except ValueError:
            msg = resp.text[:400]
        raise QuantdataError(f"HTTP {resp.status_code}: {msg}\nquery: {query[:300]}")
    raise QuantdataError(f"request failed after {retries + 1} attempts: {last}")


def sql(query: str, *, timeout: int = 120, retries: int = 2) -> pd.DataFrame:
    """Run a read-only SELECT and return a DataFrame.

    ``timeout`` is the *client* socket timeout; the server independently caps a
    query at :data:`SERVER_QUERY_TIMEOUT_S`, so raising this will not let a slow
    aggregate finish — chunk it with :func:`sql_by_year` instead.
    """
    data = _post_sql(query, timeout=timeout, retries=retries)
    cols = data.get("columns", [])
    rows = data.get("rows", [])
    return pd.DataFrame(rows, columns=cols)


def sql_by_year(
    template: str,
    start: str,
    end: str,
    *,
    timeout: int = 120,
    retries: int = 2,
) -> pd.DataFrame:
    """Run ``template`` once per calendar year and concatenate.

    ``template`` must contain the literal placeholders ``{start}`` and ``{end}``
    which are substituted with per-year ISO date bounds, e.g.::

        sql_by_year(
            "SELECT * FROM tw_stock_bars "
            "WHERE trading_date BETWEEN '{start}' AND '{end}'",
            "2015-01-01", "2026-08-27")

    This is the standard way around the server's 30-second cap.  Years that
    return nothing contribute nothing; a year that *errors* aborts the whole
    call rather than silently yielding a short panel — a partial history that
    looks complete is the worst possible outcome for a backtest.
    """
    if "{start}" not in template or "{end}" not in template:
        raise ValueError("template must contain {start} and {end} placeholders")
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    if s > e:
        raise ValueError(f"start {start} is after end {end}")
    frames: list[pd.DataFrame] = []
    for year in range(s.year, e.year + 1):
        lo = max(s, pd.Timestamp(year=year, month=1, day=1)).date().isoformat()
        hi = min(e, pd.Timestamp(year=year, month=12, day=31)).date().isoformat()
        frag = sql(
            template.format(start=lo, end=hi), timeout=timeout, retries=retries
        )
        if not frag.empty:
            frames.append(frag)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return out


# --------------------------------------------------------------------------
# caching
# --------------------------------------------------------------------------

def cache_dir() -> Path:
    d = Path(os.environ.get("QD_CACHE_DIR", str(DEFAULT_CACHE_DIR)))
    d.mkdir(parents=True, exist_ok=True)
    return d


def cached_sql(
    query_or_template: str,
    *,
    start: str | None = None,
    end: str | None = None,
    refresh: bool = False,
    tag: str = "",
) -> pd.DataFrame:
    """Cache a query's result to parquet keyed by a hash of the query text.

    Pass ``start``/``end`` to route through :func:`sql_by_year`.  Set
    ``refresh=True`` to bypass a stored copy.  The cache is *content*-addressed,
    so editing the SQL by one character produces a different file — there is no
    way to get a stale answer to a changed question.
    """
    key_src = f"{query_or_template}|{start}|{end}"
    key = hashlib.sha1(key_src.encode("utf-8")).hexdigest()[:16]
    name = f"{tag + '_' if tag else ''}{key}.parquet"
    path = cache_dir() / name
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    if start is not None and end is not None:
        df = sql_by_year(query_or_template, start, end)
    else:
        df = sql(query_or_template)
    df.to_parquet(path, index=False)
    return df


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _sql_str_list(values: Iterable[str]) -> str:
    escaped = [str(v).replace("'", "''") for v in values]
    return ", ".join(f"'{v}'" for v in escaped)


def _coerce_dates(df: pd.DataFrame, cols: Sequence[str] = ("trading_date",)) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c])
    return df


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------

def list_tables() -> list[str]:
    df = sql("SELECT table_name FROM information_schema.tables ORDER BY 1")
    return df["table_name"].tolist()


def table_columns(table: str) -> pd.DataFrame:
    return sql(
        "SELECT column_name, data_type, ordinal_position "
        f"FROM information_schema.columns WHERE table_name = '{table}' "
        "ORDER BY ordinal_position"
    )


def coverage(table: str, key: str = "trading_date") -> dict[str, Any]:
    """Min/max of the date key for a table — cheap enough to survive the 30s cap."""
    df = sql(
        f"SELECT min({key})::VARCHAR AS lo, max({key})::VARCHAR AS hi FROM {table}"
    )
    return {"table": table, "min": df.iloc[0]["lo"], "max": df.iloc[0]["hi"]}


def stock_bars(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    adjusted: bool = True,
    refresh: bool = False,
) -> pd.DataFrame:
    """Daily TW equity bars from ``tw_stock_bars`` (2010-01-04 onward).

    ``adjusted=True`` returns the ``adj_*`` columns renamed to plain OHLC — use
    it for any return calculation.  The unadjusted ``close`` is what you compare
    against a price-limit or a disposition threshold, so both are returned.
    """
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"symbol IN ({_sql_str_list(symbols)})")
    tmpl = (
        "SELECT trading_date, symbol, open, high, low, close, volume, vwap, "
        "adj_open, adj_high, adj_low, adj_close, adj_factor "
        "FROM tw_stock_bars WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, symbol"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag="stock_bars")
    df = _coerce_dates(df)
    if adjusted and not df.empty:
        for c in ("open", "high", "low", "close"):
            df[f"raw_{c}"] = df[c]
            df[c] = df[f"adj_{c}"]
    return df


def futures_continuous(
    root: str,
    start: str,
    end: str,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Front-month continuous futures series (``TX`` or ``MTX``), 2016 onward.

    Note the coverage floor: ``tx_continuous_d`` / ``mtx_continuous_d`` start at
    **2016-01-04**, five years later than the equity panel.  A study that wants
    a common window across both must start in 2016.
    """
    table = {"TX": "tx_continuous_d", "MTX": "mtx_continuous_d"}.get(root.upper())
    if table is None:
        raise ValueError(f"unknown futures root {root!r}; expected TX or MTX")
    tmpl = (
        "SELECT trading_date, contract_code, open, high, low, close, settle, "
        "volume, oi_2 AS open_interest, basis, roi "
        f"FROM {table} WHERE trading_date BETWEEN '{{start}}' AND '{{end}}' "
        "ORDER BY trading_date"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag=f"fut_{root.lower()}")
    return _coerce_dates(df)


def attrs_status(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    events_only: bool = False,
    refresh: bool = False,
) -> pd.DataFrame:
    """Per-stock daily trading attributes from ``stock_attrs_status``.

    This is the table that makes disposition-stock ("處置股") event trading
    possible without scraping TWSE announcements.  Columns of interest:

    ``is_attention_bool``      注意股 — disclosure only, no trading restriction
    ``is_disposition_bool``    處置股 — call-auction matching, the "入獄" regime
    ``is_no_daytrade_bool``    現股當沖禁止 — the binding constraint on the
                               popular "short it on day one" trade
    ``is_full_settle_bool``    全額交割 (pre-payment required)
    ``attention_count_30d`` / ``disposition_count_30d`` — repeat-offender counts,
                               which is how you separate a first disposition
                               (10 sessions, 5-minute matching) from a second
                               (20 sessions, 20-minute matching + pre-payment).

    ``events_only=True`` returns only rows where at least one of the attention /
    disposition / no-daytrade flags is set, which is ~2 orders of magnitude
    smaller than the full 5.6M-row panel.
    """
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"stock_id IN ({_sql_str_list(symbols)})")
    if events_only:
        where.append(
            "(is_attention_bool OR is_disposition_bool OR is_no_daytrade_bool "
            "OR is_full_settle_bool)"
        )
    tmpl = (
        "SELECT trading_date, stock_id, market, is_attention_bool, "
        "is_disposition_bool, is_suspended_bool, is_full_settle_bool, "
        "is_no_daytrade_bool, attention_count_30d, disposition_count_30d "
        "FROM stock_attrs_status WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, stock_id"
    )
    tag = "attrs_ev" if events_only else "attrs_all"
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag=tag)
    return _coerce_dates(df)


def trading_attrs_detail(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """``tw_stock_trading_attrs_daily`` — adds ``match_interval_sec``.

    ``match_interval_sec`` is the call-auction interval imposed during a
    disposition: ~300s for a first offence and ~1200s for a repeat.  It is the
    cleanest available proxy for disposition *severity*, and unlike the boolean
    flags it distinguishes the two regimes directly.
    """
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"stock_id IN ({_sql_str_list(symbols)})")
    tmpl = (
        "SELECT trading_date, stock_id, is_attention, is_disposition, "
        "match_interval_sec, is_suspended, is_full_settle, "
        "no_daytrade_buy_first, no_daytrade_sell_first "
        "FROM tw_stock_trading_attrs_daily WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, stock_id"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag="attrs_detail")
    return _coerce_dates(df)


def margin_daily(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """``tw_margin_daily`` — margin & short-sale balances.

    ``short_balance_lot`` going to zero while a stock is in disposition is the
    empirical signature of 停券 (securities lending suspended), which is what
    makes the textbook "short the disposition" trade unimplementable.  Check it
    before believing any short-side backtest on this event.
    """
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"stock_id IN ({_sql_str_list(symbols)})")
    tmpl = (
        "SELECT trading_date, stock_id, margin_balance_lot, short_balance_lot, "
        "short_sell_lot, short_buy_lot, margin_util_pct, short_util_pct, "
        "short_to_margin_pct "
        "FROM tw_margin_daily WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, stock_id"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag="margin")
    return _coerce_dates(df)


def inst_stock_daily(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """``tw_inst_stock_daily`` — foreign / SITC / dealer net lots per stock."""
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"stock_id IN ({_sql_str_list(symbols)})")
    tmpl = (
        "SELECT trading_date, stock_id, foreign_net_lot, sitc_net_lot, "
        "dealer_net_lot, total_net_lot, foreign_hold_pct "
        "FROM tw_inst_stock_daily WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, stock_id"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag="inst")
    return _coerce_dates(df)


def factor_daily(
    start: str,
    end: str,
    symbols: Sequence[str] | None = None,
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """``stock_factor_daily`` — precomputed returns / momentum / vol / turnover."""
    where = ["trading_date BETWEEN '{start}' AND '{end}'"]
    if symbols:
        where.append(f"symbol IN ({_sql_str_list(symbols)})")
    tmpl = (
        "SELECT trading_date, symbol, ret_1d, ret_5d, ret_20d, ret_60d, "
        "ret_120d, mom_12_1, vol_20d, vol_60d, turnover_20d "
        "FROM stock_factor_daily WHERE " + " AND ".join(where) +
        " ORDER BY trading_date, symbol"
    )
    df = cached_sql(tmpl, start=start, end=end, refresh=refresh, tag="factors")
    return _coerce_dates(df)


def liquid_universe(
    as_of: str,
    *,
    top_n: int = 300,
    window: int = 60,
    min_price: float = 10.0,
) -> list[str]:
    """Top-N symbols by trailing median turnover as of ``as_of`` (PIT-safe).

    Uses ``close * volume`` as the turnover proxy because ``tw_stock_bars`` has
    no ``amount_twd`` column (the local-lakehouse adapter in ``quantdata.py``
    does, and uses it).  Only rows with ``trading_date <= as_of`` are read, so
    the ranking cannot see the future.
    """
    lo = (pd.Timestamp(as_of) - pd.Timedelta(days=int(window * 2.2))).date().isoformat()
    q = (
        "SELECT symbol, median(close * volume) AS turnover, "
        "       max(close) FILTER (WHERE trading_date = mx) AS last_close "
        "FROM ("
        "  SELECT symbol, trading_date, close, volume, "
        "         max(trading_date) OVER (PARTITION BY symbol) AS mx "
        "  FROM tw_stock_bars "
        f"  WHERE trading_date BETWEEN '{lo}' AND '{as_of}'"
        ") GROUP BY symbol "
        f"HAVING count(*) >= {max(5, window // 3)} "
        f"   AND any_value(last_close) IS NOT NULL "
        "ORDER BY turnover DESC "
        f"LIMIT {top_n}"
    )
    df = sql(q)
    if df.empty:
        return []
    df = df[pd.to_numeric(df["last_close"], errors="coerce") >= min_price]
    return df["symbol"].astype(str).tolist()


__all__ = [
    "QuantdataError",
    "api_base",
    "attrs_status",
    "cached_sql",
    "coverage",
    "factor_daily",
    "futures_continuous",
    "inst_stock_daily",
    "list_tables",
    "liquid_universe",
    "margin_daily",
    "sql",
    "sql_by_year",
    "stock_bars",
    "table_columns",
    "trading_attrs_detail",
]
