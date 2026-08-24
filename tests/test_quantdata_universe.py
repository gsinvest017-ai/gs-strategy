"""Tests for strategies/_common/quantdata.py universe derivation.

Uses a synthetic price-canonical parquet so no lakehouse is needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from strategies._common.quantdata import derive_universe  # noqa: E402


def _make_panel() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=30)
    rows = []
    for code in ("2330", "1111", "2222", "3333", "4444"):
        base = {"2330": 50.0, "1111": 5.0, "2222": 100.0, "3333": 30.0,
                "4444": 80.0}[code]
        amount = {"2330": 5e8, "1111": 9e8, "2222": 1e6,
                  "3333": 3e8, "4444": 7e8}[code]
        for i, d in enumerate(dates):
            # 4444 的巨額成交只出現在「未來」——PIT 正確的實作在早期
            # as_of 絕不能看到它。
            amt = 0.0 if (code == "4444" and i < 12) else amount
            rows.append({"trading_date": d, "stock_id": code,
                         "close": base, "amount_twd": amt})
    # 大盤/類指列（非數字 stock_id）必須被過濾掉
    for name in ("TAIEX", "Electronics"):
        for d in dates:
            rows.append({"trading_date": d, "stock_id": name,
                         "close": 20000.0, "amount_twd": 9e12})
    return pd.DataFrame(rows)


@pytest.fixture
def qd_root(tmp_path):
    root = tmp_path / "QUANTDATA"
    (root / "gold/features").mkdir(parents=True)
    _make_panel().to_parquet(root / "gold/features/finmind_price_canonical.parquet",
                             index=False)
    return root


def test_derive_ranks_by_amount_and_applies_floors(qd_root):
    codes = derive_universe("2024-01-15", top_n=10,
                            liquidity_floor_ntd=1e8, min_price=10.0,
                            root=qd_root)
    # 1111 has huge amount but price 5 < floor; 2222 amount below floor;
    # 4444's visible amounts are all 0 at this as_of (PIT); 2330 & 3333
    # qualify, ranked by median amount desc.
    assert codes == ["2330", "3333"]


def test_top_n_caps_results(qd_root):
    codes = derive_universe("2024-02-15", top_n=1,
                            liquidity_floor_ntd=0, min_price=0.0,
                            root=qd_root)
    assert len(codes) == 1
    assert codes[0] == "1111"          # largest amount wins


def test_as_of_cuts_future_rows(qd_root):
    # 4444 的 7e8 巨額成交只存在於第 12 個交易日之後；在早期 as_of
    # （只看得到 amount=0）它絕不能入選——否則就是未來資料洩漏。
    codes = derive_universe("2024-01-15", top_n=10,
                            liquidity_floor_ntd=1e8, min_price=0.0,
                            root=qd_root)
    assert "4444" not in codes
    assert "2330" in codes


def test_missing_panel_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        derive_universe("2024-01-15", root=tmp_path / "nope")
