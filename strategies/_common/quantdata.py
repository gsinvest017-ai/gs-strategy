"""quantdata adapter — derive a tradable equity universe from QUANTDATA.

Data source (Phase-3 wiring, 2026-08): the medallion lakehouse at
``~/gs-scraper/QUANTDATA``. ``gold/universe/`` is not populated yet, so we
derive the universe from ``gold/features/finmind_price_canonical.parquet``
(10M+ rows of per-stock daily OHLCV + ``amount_twd`` turnover). When the
official gold/universe layer lands, point ``universe_source`` at it and
this module gains a reader — derivation stays as fallback.

PIT semantics: only rows with ``trading_date <= as_of`` are used; ranking
features (median dollar-volume over the trailing window) are computed
per-stock from that slice, so an as-of date can never leak future data.

Symbol convention: plain TW codes ("2330"), matching zipline ``symbol()``.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

DEFAULT_QD_ROOT = Path.home() / "gs-scraper" / "QUANTDATA"
DEFAULT_PRICE_CANONICAL = "gold/features/finmind_price_canonical.parquet"

_REQUIRED_COLS = {"trading_date", "stock_id", "close", "amount_twd"}


def qd_root() -> Path:
    """Resolve the lakehouse root (env override for tests / other hosts)."""
    return Path(os.environ.get("QD_ROOT", str(DEFAULT_QD_ROOT)))


def load_price_canonical(root: Path | None = None,
                         rel: str = DEFAULT_PRICE_CANONICAL,
                         *, min_date: str | None = None) -> pd.DataFrame:
    """Load (and lightly cache) the canonical daily price panel."""
    path = Path(root) if root else qd_root()
    path = path / rel
    if not path.exists():
        raise FileNotFoundError(
            f"quantdata price panel not found: {path} "
            "(set QD_ROOT or populate the lakehouse)")
    df = pd.read_parquet(path, columns=list(_REQUIRED_COLS))
    df["trading_date"] = pd.to_datetime(df["trading_date"])
    if min_date is not None:
        df = df[df["trading_date"] >= pd.Timestamp(min_date)]
    return df


def derive_universe(as_of: str | pd.Timestamp, *, top_n: int = 200,
                    liquidity_floor_ntd: float = 20_000_000,
                    min_price: float = 10.0, window: int = 20,
                    root: Path | None = None) -> list[str]:
    """Return top-N codes by trailing median dollar-volume as of ``as_of``.

    A stock qualifies when, within its last ``window`` sessions up to
    ``as_of`` (at least ``max(5, window // 2)`` observations):
      * last close >= ``min_price``
      * median(close * volume-ish turnover) >= ``liquidity_floor_ntd``
    Here turnover proxy = ``amount_twd`` (NT$ traded), which is exactly
    what a liquidity floor wants.
    """
    as_of_ts = pd.Timestamp(as_of)
    df = load_price_canonical(root=root)
    df["stock_id"] = df["stock_id"].astype(str)
    # FinMind 面板混有大盤/類指（TAIEX、Electronics…）與非個股列，
    # 只保留全數字代碼（個股＋ETF）。
    df = df[df["stock_id"].str.isdigit()]
    df = df[df["trading_date"] <= as_of_ts]
    if df.empty:
        raise ValueError(f"no price rows on/before {as_of.date()}")

    need = max(5, window // 2)
    picked: dict[str, float] = {}
    for code, g in df.sort_values("trading_date").groupby("stock_id"):
        tail = g.tail(window)
        if len(tail) < need:
            continue
        last_close = float(tail["close"].iloc[-1])
        if last_close < min_price:
            continue
        med_amount = float(tail["amount_twd"].median())
        if med_amount >= liquidity_floor_ntd:
            picked[str(code)] = med_amount

    ranked = sorted(picked, key=picked.get, reverse=True)
    return ranked[:top_n]
