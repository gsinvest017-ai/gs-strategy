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
    spec = iu.spec_from_file_location(path.stem, path)
    module = iu.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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


if __name__ == "__main__":
    test_vgrsi_extreme_cases()
    test_cubic_signal_shape()
    test_rmt_gap_iid_vs_one_factor()
    test_ols_beta_recovers_known_slope()
    test_ols_beta_nan_guards()
    test_basket_beta_linearity()
    print("ALL MATH TESTS PASS")
