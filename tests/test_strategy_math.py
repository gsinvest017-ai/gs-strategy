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


if __name__ == "__main__":
    test_vgrsi_extreme_cases()
    test_cubic_signal_shape()
    test_rmt_gap_iid_vs_one_factor()
    print("ALL MATH TESTS PASS")
