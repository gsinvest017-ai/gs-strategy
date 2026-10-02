"""Calibration tests for strategies/_common/validation — synthetic data only.

These pin down the failure modes found in the 2026-09 independent reviews:
PBO scored by mean return is fooled by volatility differences, CPCV test paths
are not evidence for parameter-free strategies, and DSR's SR variance must not
fall below its sampling floor.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

V = importlib.import_module("strategies._common.validation")


def _levered_configs(seed: int = 0, T: int = 240, n: int = 8) -> np.ndarray:
    """Configs = L_j x (common drift + own noise): identical expected Sharpe, different volatility."""
    rng = np.random.default_rng(seed)
    common = 0.004 + 0.03 * rng.standard_normal(T)
    lev = np.linspace(0.5, 3.0, n)
    return np.column_stack([L * (common + 0.006 * rng.standard_normal(T)) for L in lev])


def test_pbo_mean_metric_is_fooled_by_leverage_but_sharpe_is_not():
    perf = _levered_configs()
    pbo_mean = V.pbo(perf, metric="mean")
    pbo_sharpe = V.pbo(perf, metric="sharpe")
    # mean scoring always picks the most levered config, so the IS-best stays on top OOS
    assert pbo_mean < 0.2
    # with leverage removed, choosing among equal-Sharpe configs is a coin flip
    assert pbo_sharpe > 0.3
    assert V.pbo(perf) == pbo_sharpe  # sharpe is the default


def test_pbo_rejects_unknown_metric():
    with pytest.raises(ValueError):
        V.pbo(_levered_configs(), metric="sortino")


def test_pbo_skips_zero_variance_configs():
    perf = _levered_configs()
    perf[:, 0] = 0.0
    assert 0.0 <= V.pbo(perf) <= 1.0


def test_block_sharpes_are_disjoint_blocks():
    rng = np.random.default_rng(3)
    good = 0.02 + 0.01 * rng.standard_normal(60)
    bad = -0.02 + 0.01 * rng.standard_normal(60)
    out = V.block_sharpes(np.r_[good, bad, good], n_blocks=3)
    assert len(out) == 3
    assert out[0] > 0 and out[1] < 0 and out[2] > 0
    annual = V.block_sharpes(np.r_[good, bad, good], n_blocks=3, periods_per_year=12)
    assert annual[0] == pytest.approx(out[0] * np.sqrt(12))


def test_dsr_sr_variance_floor_and_pass_through():
    assert V.dsr_sr_variance([0.10, 0.1001, 0.0999], n_obs=180) == pytest.approx(1 / 179)
    wide = [-0.3, 0.0, 0.3, 0.6]
    assert V.dsr_sr_variance(wide, n_obs=180) == pytest.approx(np.var(wide, ddof=1))
    assert V.dsr_sr_variance([0.1], n_obs=100) == pytest.approx(1 / 99)


def test_min_track_record_length():
    rng = np.random.default_rng(5)
    strong = 0.02 + 0.02 * rng.standard_normal(500)
    weak = 0.004 + 0.02 * rng.standard_normal(500)
    assert V.min_track_record_length(strong) < V.min_track_record_length(weak)
    assert V.min_track_record_length(-strong) == float("inf")


def test_effective_n_trials_bounds():
    rng = np.random.default_rng(9)
    base = rng.standard_normal(2000)
    identical = np.column_stack([base] * 6)
    independent = rng.standard_normal((2000, 6))
    assert V.effective_n_trials(identical) == pytest.approx(1.0, abs=1e-6)
    assert V.effective_n_trials(independent) > 5.5
