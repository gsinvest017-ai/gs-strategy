"""Pure-numpy maths smoke tests for each Taiwan-futures strategy.

These tests stub out ``zipline`` so they run without TQuant-Lab installed.
They verify only the *signal calculations* — not the full backtest harness.
"""
from __future__ import annotations

import importlib.util as iu
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
STRAT = REPO / "strategies"


class _Stub:
    def __getattr__(self, n):
        return _Stub()

    def __call__(self, *a, **k):
        return _Stub()


_STUB_MODULES = [
    "zipline",
    "zipline.api",
    "zipline.finance",
    "zipline.finance.commission",
    "zipline.finance.slippage",
    "zipline.utils",
    "zipline.utils.events",
    "zipline.utils.calendar_utils",
    "zipline.TQresearch",
    "zipline.TQresearch.futures_package",
]


def _stub_zipline() -> None:
    for name in _STUB_MODULES:
        sys.modules.setdefault(name, _Stub())


def _load(path: Path):
    # Mirror the dashboard's driver: sys.path[0] = bundle dir so sibling
    # files (futures_setup.py) resolve. Pop after load so other tests stay
    # isolated.
    bundle_dir = str(path.parent.resolve())
    added = False
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
        added = True
    try:
        spec = iu.spec_from_file_location(path.stem, path)
        module = iu.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if added:
            sys.path.remove(bundle_dir)


def test_vgrsi_extreme_cases() -> None:
    _stub_zipline()
    m = _load(STRAT / "vgrsi_tx" / "strategy.py")
    assert abs(m.vgrsi_value(np.linspace(100, 130, 30)) - 100.0) < 1e-9
    assert abs(m.vgrsi_value(np.linspace(130, 100, 30)) - 0.0) < 1e-9
    assert abs(m.vgrsi_value(np.full(30, 100.0)) - 50.0) < 1e-9


def test_cubic_signal_shape() -> None:
    _stub_zipline()
    m = _load(STRAT / "cubic_momentum_tx" / "strategy.py")
    assert abs(m._cubic_signal(0.0, 1.5)) < 1e-12
    assert abs(m._cubic_signal(1.5, 1.5) - 1.0) < 1e-9
    assert m._cubic_signal(3.0, 1.5) < 0    # cubic flip


def test_rmt_gap_iid_vs_one_factor() -> None:
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")
    rng = np.random.default_rng(42)

    common = rng.standard_normal(60)
    R_one = np.tile(common, (50, 1)).T + 0.001 * rng.standard_normal((60, 50))
    R_iid = rng.standard_normal((60, 50))

    g_one = m._complexity_gap(R_one)
    g_iid = m._complexity_gap(R_iid)
    # IID universe should produce a wider gap than a 1-factor collapse.
    assert g_iid > g_one


def test_ols_beta_recovers_known_slope() -> None:
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")
    rng = np.random.default_rng(7)
    market = rng.standard_normal(200) * 0.01
    # Construct asset with true beta = 1.5 and small idiosyncratic noise.
    asset = 1.5 * market + 0.0005 * rng.standard_normal(200)
    beta = m._ols_beta(asset, market)
    assert abs(beta - 1.5) < 0.05


def test_ols_beta_nan_guards() -> None:
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")
    # Too few points
    assert not np.isfinite(m._ols_beta(np.arange(5.0), np.arange(5.0)))
    # Zero-variance market
    flat = np.zeros(30)
    asset = np.linspace(-0.01, 0.01, 30)
    assert not np.isfinite(m._ols_beta(asset, flat))


def test_basket_beta_linearity() -> None:
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")
    weights = {"A": 0.25, "B": 0.25, "C": -0.5}
    betas = {"A": 1.0, "B": 0.5, "C": 1.2}
    # 0.25 * 1.0 + 0.25 * 0.5 + (-0.5) * 1.2 = 0.25 + 0.125 - 0.6 = -0.225
    assert abs(m._basket_beta(weights, betas) - (-0.225)) < 1e-12
    # NaN beta on one asset should be dropped, not poison the sum.
    betas_with_nan = {"A": 1.0, "B": float("nan"), "C": 1.2}
    assert abs(m._basket_beta(weights, betas_with_nan) - (0.25 - 0.6)) < 1e-12


def test_select_by_sector_balanced() -> None:
    """Sector-neutral selection picks ≥1 long + ≥1 short per non-empty sector."""
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")

    # 4 sectors, each with 4 roots. With decile=0.25 we expect exactly
    # 1 long + 1 short per sector = 4 longs total, 4 shorts total.
    scores = {
        "T1": 0.10, "T2": 0.05, "T3": -0.05, "T4": -0.10,
        "F1": 0.20, "F2": 0.10, "F3": -0.10, "F4": -0.20,
        "R1": 0.04, "R2": 0.02, "R3": -0.02, "R4": -0.04,
        "X1": 0.30, "X2": 0.20, "X3": -0.20, "X4": -0.30,
    }
    sector_map = {
        "T1": "TECH", "T2": "TECH", "T3": "TECH", "T4": "TECH",
        "F1": "FIN",  "F2": "FIN",  "F3": "FIN",  "F4": "FIN",
        "R1": "TRAD", "R2": "TRAD", "R3": "TRAD", "R4": "TRAD",
        "X1": "X",    "X2": "X",    "X3": "X",    "X4": "X",
    }
    longs, shorts = m._select_by_sector(
        scores, sector_map, long_decile=0.25, short_decile=0.25,
        reverse_momentum=False, long_only=False,
    )
    # 4 sectors × 1 long each = 4 longs; same for shorts. Top score per
    # sector wins long: T1, F1, R1, X1. Bottom wins short: T4, F4, R4, X4.
    assert set(longs) == {"T1", "F1", "R1", "X1"}
    assert set(shorts) == {"T4", "F4", "R4", "X4"}


def test_select_by_sector_min_one_per_sector() -> None:
    """A 1-root sector still contributes 1 long (and 1 short unless long_only)."""
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")

    scores = {"A": 0.1, "B": -0.2}
    sector_map = {"A": "TECH", "B": "FIN"}
    longs, shorts = m._select_by_sector(
        scores, sector_map, 0.1, 0.1, False, False
    )
    # max(1, round(1*0.1)) == 1 -> each 1-root sector contributes its sole
    # member to both long and short legs.
    assert set(longs) == {"A", "B"}
    assert set(shorts) == {"A", "B"}


def test_select_by_sector_reverse_and_long_only() -> None:
    """`reverse_momentum` swaps L/S; `long_only` empties shorts post-swap."""
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")

    scores = {"A": 0.5, "B": 0.1, "C": -0.1, "D": -0.5}
    sector_map = {k: "TECH" for k in scores}

    longs, shorts = m._select_by_sector(
        scores, sector_map, 0.25, 0.25, reverse_momentum=True, long_only=False
    )
    # Reverse: longs come from bottom, shorts from top.
    assert longs == ["D"]
    assert shorts == ["A"]

    longs_lo, shorts_lo = m._select_by_sector(
        scores, sector_map, 0.25, 0.25, reverse_momentum=False, long_only=True
    )
    assert longs_lo == ["A"]
    assert shorts_lo == []


def test_select_by_sector_drops_unmapped_roots() -> None:
    """Roots missing from sector_map are silently excluded from selection."""
    _stub_zipline()
    m = _load(STRAT / "xsmom_stkfut_rmt" / "strategy.py")

    scores = {"A": 0.5, "B": 0.1, "UNMAPPED": 0.9}
    sector_map = {"A": "TECH", "B": "TECH"}  # UNMAPPED deliberately absent
    longs, shorts = m._select_by_sector(
        scores, sector_map, 0.5, 0.5, False, False
    )
    # UNMAPPED is dropped even though its score is highest.
    assert "UNMAPPED" not in longs and "UNMAPPED" not in shorts
    assert set(longs) == {"A"}
    assert set(shorts) == {"B"}


if __name__ == "__main__":
    test_vgrsi_extreme_cases()
    test_cubic_signal_shape()
    test_rmt_gap_iid_vs_one_factor()
    test_ols_beta_recovers_known_slope()
    test_ols_beta_nan_guards()
    test_basket_beta_linearity()
    test_select_by_sector_balanced()
    test_select_by_sector_min_one_per_sector()
    test_select_by_sector_reverse_and_long_only()
    test_select_by_sector_drops_unmapped_roots()
    print("ALL MATH TESTS PASS")
