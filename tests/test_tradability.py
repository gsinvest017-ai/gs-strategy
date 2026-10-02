"""Tests for strategies/_common/validation/tradability.py — synthetic series only.

Every RNG is seeded and every tolerance was chosen with margin against that
seed, so nothing here is flaky by construction.
"""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

tradability = importlib.import_module("strategies._common.validation.tradability")

SEED = 20260828
N = 2000


# --------------------------------------------------------------------------
# synthetic generators
# --------------------------------------------------------------------------

def _iid(n: int = N, seed: int = SEED, sigma: float = 0.01, mu: float = 0.0) -> np.ndarray:
    return np.random.default_rng(seed).normal(mu, sigma, n)


def _ar1(phi: float, n: int = N, seed: int = SEED, sigma: float = 0.01) -> np.ndarray:
    """AR(1) returns r_t = phi * r_{t-1} + eps_t, generated causally."""
    eps = np.random.default_rng(seed).normal(0.0, sigma, n)
    r = np.empty(n)
    r[0] = eps[0]
    for t in range(1, n):
        r[t] = phi * r[t - 1] + eps[t]
    return r


def _prices_from(returns: np.ndarray, p0: float = 100.0) -> np.ndarray:
    return p0 * np.exp(np.cumsum(returns))


# --------------------------------------------------------------------------
# 1-2. variance ratio
# --------------------------------------------------------------------------

@pytest.mark.parametrize("q", [2, 4, 8])
def test_variance_ratio_of_iid_gaussian_is_one(q):
    res = tradability.variance_ratio(_iid(), q)
    assert res["vr"] == pytest.approx(1.0, abs=0.25)
    assert abs(res["z"]) < 2.5
    assert abs(res["z_homoskedastic"]) < 2.5
    assert abs(res["z_heteroskedastic"]) < 2.5
    assert 0.0 <= res["p_value"] <= 1.0


def test_variance_ratio_returns_both_z_statistics():
    hetero = tradability.variance_ratio(_iid(), 4, heteroskedastic=True)
    homo = tradability.variance_ratio(_iid(), 4, heteroskedastic=False)
    # same VR either way; only the standardisation differs
    assert hetero["vr"] == pytest.approx(homo["vr"])
    assert hetero["z"] == hetero["z_heteroskedastic"]
    assert homo["z"] == homo["z_homoskedastic"]
    assert hetero["z_homoskedastic"] == pytest.approx(homo["z_homoskedastic"])
    assert hetero["z_heteroskedastic"] != pytest.approx(hetero["z_homoskedastic"])


def test_variance_ratio_of_trending_ar1_exceeds_one():
    res = tradability.variance_ratio(_ar1(0.3), 4)
    assert res["vr"] > 1.0
    assert res["p_value"] < 0.05
    assert res["p_homoskedastic"] < 0.05


def test_variance_ratio_of_mean_reverting_ar1_is_below_one():
    res = tradability.variance_ratio(_ar1(-0.3), 4)
    assert res["vr"] < 1.0
    assert res["p_value"] < 0.05
    assert res["p_homoskedastic"] < 0.05


def test_variance_ratio_rejects_bad_arguments():
    with pytest.raises(ValueError):
        tradability.variance_ratio(_iid(100), 1)          # q must be >= 2
    with pytest.raises(ValueError):
        tradability.variance_ratio(_iid(10), 8)           # needs 2q observations
    with pytest.raises(ValueError):
        tradability.variance_ratio(np.zeros(200), 2)      # zero variance


def test_variance_ratio_profile_shape_and_agreement():
    qs = (2, 4, 8, 16, 32)
    prof = tradability.variance_ratio_profile(_ar1(0.3), qs)
    assert isinstance(prof, pd.DataFrame)
    assert list(prof["q"]) == list(qs)
    for col in ("vr", "z", "p_value", "z_homoskedastic", "z_heteroskedastic", "n_obs"):
        assert col in prof.columns
    # a positively autocorrelated series trends at every horizon here
    assert (prof["vr"] > 1.0).all()
    # rows must equal the standalone call
    single = tradability.variance_ratio(_ar1(0.3), 8)
    row = prof[prof["q"] == 8].iloc[0]
    assert row["vr"] == pytest.approx(single["vr"])


# --------------------------------------------------------------------------
# 3. Hurst exponents
# --------------------------------------------------------------------------

def test_hurst_dfa_of_a_random_walk_is_one_half():
    walk = np.cumsum(_iid(4000, seed=SEED + 1))
    assert tradability.hurst_dfa(walk) == pytest.approx(0.5, abs=0.15)


def test_hurst_dfa_separates_trending_from_mean_reverting_paths():
    trend = np.cumsum(_ar1(0.3, n=4000, seed=SEED + 2))
    revert = np.cumsum(_ar1(-0.3, n=4000, seed=SEED + 2))
    h_trend = tradability.hurst_dfa(trend)
    h_revert = tradability.hurst_dfa(revert)
    # Only the *ordering* is asserted. DFA is fitted over scales >= 8 bars,
    # and an AR(1) with |phi| = 0.3 has decorrelated long before that, so both
    # exponents sit close to the 0.5 random-walk null (~0.55 vs ~0.47 here).
    # Asserting a hard `h_revert < 0.5 < h_trend` passes on this seed but
    # fails on others — that would be a knife-edge test dressed up as a
    # property, and it would also overstate what DFA can see in short memory.
    assert h_trend > h_revert
    assert h_trend - h_revert > 0.05


def test_hurst_rs_of_a_random_walk_is_near_one_half():
    walk = np.cumsum(_iid(4000, seed=SEED + 3))
    h = tradability.hurst_rs(walk)
    # Deliberately loose: R/S is biased upward on finite samples (see the
    # docstring), so anything tighter than this would be a lie about the
    # estimator rather than a test of the code.
    assert 0.40 < h < 0.65


def test_hurst_estimators_reject_short_series():
    with pytest.raises(ValueError):
        tradability.hurst_rs(np.cumsum(_iid(40)), min_window=64)
    with pytest.raises(ValueError):
        tradability.hurst_dfa(np.cumsum(_iid(40)))


# --------------------------------------------------------------------------
# 4. permutation entropy
# --------------------------------------------------------------------------

def test_permutation_entropy_of_white_noise_is_near_one():
    assert tradability.permutation_entropy(_iid(), m=4) > 0.95


def test_permutation_entropy_of_a_sine_wave_is_low():
    t = np.arange(N)
    sine = np.sin(2 * np.pi * t / 25.0)
    assert tradability.permutation_entropy(sine, m=4) < 0.7


def test_permutation_entropy_is_bounded_and_unnormalised_form_matches():
    x = _iid()
    pe = tradability.permutation_entropy(x, m=4, normalize=True)
    raw = tradability.permutation_entropy(x, m=4, normalize=False)
    assert 0.0 <= pe <= 1.0
    assert pe == pytest.approx(raw / np.log(24))


def test_permutation_entropy_rejects_bad_arguments():
    with pytest.raises(ValueError):
        tradability.permutation_entropy(_iid(100), m=1)
    with pytest.raises(ValueError):
        tradability.permutation_entropy(_iid(100), m=4, tau=0)


# --------------------------------------------------------------------------
# 5. Ljung-Box
# --------------------------------------------------------------------------

def test_ljung_box_does_not_reject_on_iid_noise():
    out = tradability.ljung_box_returns(_iid(), lags=(5, 10, 20))
    assert list(out["lag"]) == [5, 10, 20]
    assert (out["p_value"] > 0.05).all()


def test_ljung_box_rejects_on_ar1():
    out = tradability.ljung_box_returns(_ar1(0.3), lags=(5, 10, 20))
    assert (out["p_value"] < 0.01).all()


def test_ljung_box_abs_returns_sees_volatility_clustering_that_r_does_not():
    """The distinction the module exists to protect: |r| clustering is not
    directional predictability."""
    rng = np.random.default_rng(SEED + 5)
    # GARCH-ish: iid signs, strongly autocorrelated volatility
    n = N
    vol = np.empty(n)
    vol[0] = 0.01
    shocks = rng.normal(0.0, 1.0, n)
    for t in range(1, n):
        vol[t] = np.sqrt(1e-6 + 0.05 * (vol[t - 1] * shocks[t - 1]) ** 2 + 0.90 * vol[t - 1] ** 2)
    r = vol * shocks

    assert (tradability.ljung_box_returns(r)["p_value"] > 0.05).all()
    assert (tradability.ljung_box_abs_returns(r)["p_value"] < 0.01).all()


# --------------------------------------------------------------------------
# 6. runs test
# --------------------------------------------------------------------------

def test_runs_test_on_iid_noise_does_not_reject():
    res = tradability.runs_test(_iid())
    assert set(res) >= {"z", "p_value", "n_runs", "expected_runs"}
    assert res["p_value"] > 0.05
    assert abs(res["z"]) < 2.5
    assert res["n_runs"] == pytest.approx(res["expected_runs"], rel=0.10)


def test_runs_test_detects_sign_clustering():
    res = tradability.runs_test(_ar1(0.3))
    assert res["p_value"] < 0.05
    assert res["z"] < 0                      # too few runs => trending
    assert res["n_runs"] < res["expected_runs"]


def test_runs_test_detects_sign_alternation():
    res = tradability.runs_test(_ar1(-0.3))
    assert res["p_value"] < 0.05
    assert res["z"] > 0                      # too many runs => mean reverting


def test_runs_test_needs_both_signs():
    with pytest.raises(ValueError):
        tradability.runs_test(np.abs(_iid(200)))


# --------------------------------------------------------------------------
# 7. ta_suitability
# --------------------------------------------------------------------------

def test_ta_suitability_on_a_random_walk_is_never_suitable():
    prices = _prices_from(_iid(seed=SEED + 7))
    out = tradability.ta_suitability(prices)
    assert out["verdict"] in ("unsuitable", "marginal")
    assert out["verdict"] != "suitable"
    assert 0.0 <= out["score"] <= 100.0


def test_ta_suitability_on_a_trending_series_is_at_least_marginal():
    prices = _prices_from(_ar1(0.3, seed=SEED + 8))
    out = tradability.ta_suitability(prices)
    assert out["verdict"] in ("suitable", "marginal")


def test_ta_suitability_scores_a_trending_series_above_a_random_walk():
    walk = tradability.ta_suitability(_prices_from(_iid(seed=SEED + 9)))
    trend = tradability.ta_suitability(_prices_from(_ar1(0.3, seed=SEED + 9)))
    assert trend["score"] > walk["score"]


def test_ta_suitability_caveats_are_never_empty():
    """The score must never be presented without its caveats."""
    for prices in (_prices_from(_iid(seed=SEED + 10)),
                   _prices_from(_ar1(0.3, seed=SEED + 10)),
                   _prices_from(_ar1(-0.3, seed=SEED + 10))):
        out = tradability.ta_suitability(prices)
        assert isinstance(out["caveats"], list)
        assert out["caveats"], "ta_suitability returned a score with no caveats"
        assert all(isinstance(c, str) and c for c in out["caveats"])
        joined = " ".join(out["caveats"]).lower()
        assert "heuristic" in joined
        assert "not sufficient" in joined


def test_ta_suitability_shape():
    out = tradability.ta_suitability(_prices_from(_ar1(0.3, seed=SEED + 11)))
    assert set(out) >= {"components", "score", "verdict", "reason", "caveats"}
    comp = out["components"]
    assert isinstance(comp["variance_ratio_profile"], pd.DataFrame)
    assert isinstance(comp["ljung_box_returns"], pd.DataFrame)
    assert isinstance(comp["ljung_box_abs_returns"], pd.DataFrame)
    assert isinstance(comp["runs_test"], dict)
    assert isinstance(out["reason"], str) and out["reason"]
    # volatility clustering is reported but must contribute exactly nothing
    assert out["component_scores"]["ljung_box_abs_returns"] == 0.0


def test_ta_suitability_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        tradability.ta_suitability(np.concatenate([[0.0], _prices_from(_iid(200))]))


# --------------------------------------------------------------------------
# Causality / look-ahead
# --------------------------------------------------------------------------

def test_every_public_function_is_declared_a_whole_sample_diagnostic():
    """Guard against the module quietly growing a per-bar signal function.

    Nothing here maps a series to a series of signals, so the usual strict
    causality property is vacuous — but only for as long as that stays true.
    If someone adds a rolling/streaming function later, this fails and forces
    them to think about causality (and to write the real property test).
    """
    public = {
        name for name, obj in vars(tradability).items()
        if not name.startswith("_")
        and inspect.isfunction(obj)
        and obj.__module__ == tradability.__name__
    }
    assert public == set(tradability.WHOLE_SAMPLE_DIAGNOSTICS)


@pytest.mark.parametrize("cut", [150, 200, 250])
def test_no_lookahead_ta_suitability(cut):
    """A prefix result must depend on the prefix alone.

    Honest scoping: ``ta_suitability`` is a whole-sample statistic, so the
    textbook form of this test (``f(x[:cut])[-1] == f(x)[cut-1]``) has no
    meaning — there is no per-bar output, and the full-sample value legitimately
    differs from the prefix value. What *is* meaningful, and what this asserts,
    is that the prefix answer is identical whether the prefix is handed over as
    a standalone copy or as a view into an array that also holds a wildly
    different future, and that the input array is left untouched. That catches
    in-place mutation, id()-keyed caching, and any accidental read past the
    slice — the mechanisms by which future data actually leaks in practice.
    """
    rng = np.random.default_rng(0)
    head = _prices_from(rng.normal(0.0, 0.01, 300))
    # a violently different future glued on after `cut`
    future = head[cut - 1] * np.exp(np.cumsum(rng.normal(0.05, 0.20, 300)))
    full = np.concatenate([head[:cut], future])
    full_before = full.copy()

    standalone = tradability.ta_suitability(head[:cut].copy(), qs=(2, 5, 10))
    from_view = tradability.ta_suitability(full[:cut], qs=(2, 5, 10))

    assert standalone["score"] == pytest.approx(from_view["score"])
    assert standalone["verdict"] == from_view["verdict"]
    assert np.array_equal(full, full_before), "ta_suitability mutated its input"


@pytest.mark.parametrize("fn,arg", [
    ("variance_ratio", 4),
    ("permutation_entropy", 4),
])
def test_diagnostics_do_not_mutate_their_input(fn, arg):
    x = _iid(500, seed=1)
    before = x.copy()
    getattr(tradability, fn)(x, arg)
    assert np.array_equal(x, before)
