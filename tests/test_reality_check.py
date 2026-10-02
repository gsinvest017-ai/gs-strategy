"""Tests for strategies/_common/validation/reality_check.py.

Every RNG is seeded and every tolerance is chosen with margin for that seed:
these are deterministic assertions about a fixed Monte-Carlo draw, not flaky
distributional hopes.

The headline test is :func:`test_size_rc_large_p_while_naive_t_rejects` - it
computes the naive per-strategy t-test *in the test itself* so the contrast
between "the best of 50 coin flips looks significant" and "the reality check
knows better" is explicit rather than asserted on faith.
"""
from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

rc_mod = importlib.import_module("strategies._common.validation.reality_check")

SEED = 0
T_OBS = 500
N_MODELS = 50
PLANTED = 7  # column index of the one strategy with genuine skill
PLANTED_MEAN = 0.25  # in units of sigma


# --------------------------------------------------------------------------- #
# fixtures / builders
# --------------------------------------------------------------------------- #
def _all_noise(seed: int = SEED) -> np.ndarray:
    """(T, M) panel of pure-noise performance differentials: iid N(0, 1)."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal((T_OBS, N_MODELS))


def _one_planted(seed: int = SEED) -> np.ndarray:
    """Same panel, but column ``PLANTED`` has a genuine mean of 0.25 sigma."""
    perf = _all_noise(seed)
    perf[:, PLANTED] += PLANTED_MEAN
    return perf


def _naive_one_sided_p(column: np.ndarray) -> float:
    """The p-value an unwary researcher would quote: a plain one-sided t-test.

    H0: mean <= 0. No correction whatsoever for the fact that this column was
    picked as the best of many.
    """
    t_stat = column.mean() / (column.std(ddof=1) / np.sqrt(column.size))
    return float(stats.t.sf(t_stat, df=column.size - 1))


# --------------------------------------------------------------------------- #
# bootstrap index generators
# --------------------------------------------------------------------------- #
def test_stationary_bootstrap_shape_and_range():
    rng = np.random.default_rng(SEED)
    idx = rc_mod.stationary_bootstrap_indices(200, 10.0, 64, rng)
    assert idx.shape == (64, 200)
    assert idx.dtype.kind == "i"
    assert idx.min() >= 0
    assert idx.max() <= 199


def test_stationary_bootstrap_marginal_is_uniform():
    """The defining property of Politis-Romano: every index is equally likely.

    A chi-square goodness-of-fit on the pooled index histogram, plus a loose
    max-deviation bound so a failure is readable rather than just "p small".
    """
    n, n_boot = 50, 4000
    rng = np.random.default_rng(SEED)
    idx = rc_mod.stationary_bootstrap_indices(n, 8.0, n_boot, rng)

    counts = np.bincount(idx.ravel(), minlength=n)
    expected = idx.size / n
    # Draws inside a block are highly dependent, so the chi-square statistic is
    # over-dispersed relative to its nominal df. Use a deliberately loose
    # threshold: this test is here to catch a *biased* scheme (e.g. forgetting
    # the wrap-around, which starves the tail indices), not to certify the
    # exact null distribution of the statistic.
    chi2 = float(((counts - expected) ** 2 / expected).sum())
    assert chi2 < 10.0 * n, f"index histogram far from uniform: chi2={chi2:.1f}"

    max_dev = float(np.abs(counts / expected - 1.0).max())
    assert max_dev < 0.15, f"worst index is off by {max_dev:.1%} of uniform"

    # Wrap-around specifically: the last index must be reachable as often as
    # a middle one. Without wrapping, counts[-1] collapses.
    assert counts[-1] / expected > 0.85
    assert counts[0] / expected > 0.85


def test_stationary_bootstrap_mean_block_length():
    """Geometric(1/mean_block) block lengths => observed runs average ~mean_block."""
    n, mean_block = 400, 20.0
    rng = np.random.default_rng(SEED)
    idx = rc_mod.stationary_bootstrap_indices(n, mean_block, 200, rng)
    # A "continuation" step is one where the index advanced by exactly +1 mod n.
    steps = (np.diff(idx, axis=1) % n) == 1
    # Some continuations happen by chance when a fresh draw lands on prev+1;
    # that inflates the estimate slightly, hence the asymmetric window.
    observed_mean_block = 1.0 / (1.0 - steps.mean())
    assert 0.75 * mean_block < observed_mean_block < 1.45 * mean_block


def test_circular_block_bootstrap_shape_and_range():
    rng = np.random.default_rng(SEED)
    idx = rc_mod.circular_block_bootstrap_indices(200, 15, 64, rng)
    assert idx.shape == (64, 200)
    assert idx.min() >= 0
    assert idx.max() <= 199


def test_circular_block_bootstrap_blocks_are_contiguous_mod_n():
    n, block = 100, 10
    rng = np.random.default_rng(SEED)
    idx = rc_mod.circular_block_bootstrap_indices(n, block, 32, rng)
    for b in range(idx.shape[0]):
        for start in range(0, n - block + 1, block):
            chunk = idx[b, start : start + block]
            assert np.array_equal(chunk, (chunk[0] + np.arange(block)) % n)


def test_bootstrap_generators_reject_bad_arguments():
    rng = np.random.default_rng(SEED)
    with pytest.raises(ValueError):
        rc_mod.stationary_bootstrap_indices(1, 10.0, 4, rng)
    with pytest.raises(ValueError):
        rc_mod.stationary_bootstrap_indices(50, 0.5, 4, rng)
    with pytest.raises(ValueError):
        rc_mod.circular_block_bootstrap_indices(50, 0, 4, rng)
    with pytest.raises(ValueError):
        rc_mod.circular_block_bootstrap_indices(50, 51, 4, rng)


# --------------------------------------------------------------------------- #
# size: the correction earns its keep
# --------------------------------------------------------------------------- #
def test_size_rc_large_p_while_naive_t_rejects():
    """50 coin-flip strategies: the naive t-test on the winner rejects, RC does not.

    This is the whole reason the module exists. Under a pure-noise panel the
    best-of-50 sample mean is ~2.2 standard errors from zero, so an uncorrected
    one-sided t-test hands you a p-value below 5% and you go live with a
    strategy that is literally noise. White's RC compares that same maximum
    against the bootstrap distribution of the *maximum*, and correctly shrugs.
    """
    perf = _all_noise()
    best = int(np.argmax(perf.mean(axis=0)))

    naive_p = _naive_one_sided_p(perf[:, best])
    assert naive_p < 0.05, (
        f"the seeded fixture is supposed to produce a spuriously significant "
        f"winner; got naive p={naive_p:.4f}"
    )

    out = rc_mod.whites_reality_check(perf, n_boot=1000, mean_block=10.0, seed=SEED)
    assert out["best_index"] == best
    assert out["n_models"] == N_MODELS
    assert out["n_obs"] == T_OBS
    assert out["bootstrap_dist"].shape == (1000,)
    assert out["p_value"] > 0.10, (
        f"reality check should not reject on pure noise; got p={out['p_value']:.4f} "
        f"(naive p was {naive_p:.4f})"
    )


def test_size_spa_also_does_not_reject_on_noise():
    perf = _all_noise()
    spa = rc_mod.hansens_spa(perf, n_boot=1000, mean_block=10.0, seed=SEED)
    assert spa["p_consistent"] > 0.05
    assert spa["p_lower"] <= spa["p_consistent"] <= spa["p_upper"]


# --------------------------------------------------------------------------- #
# power: a real edge is found, and SPA is no less powerful than RC
# --------------------------------------------------------------------------- #
def test_power_rc_detects_planted_edge():
    perf = _one_planted()
    out = rc_mod.whites_reality_check(perf, n_boot=1000, mean_block=10.0, seed=SEED)
    assert out["best_index"] == PLANTED
    assert out["p_value"] < 0.05, f"RC missed a 0.25-sigma edge: p={out['p_value']}"


def test_power_spa_no_less_powerful_than_rc():
    perf = _one_planted()
    rc = rc_mod.whites_reality_check(perf, n_boot=1000, mean_block=10.0, seed=SEED)
    spa = rc_mod.hansens_spa(perf, n_boot=1000, mean_block=10.0, seed=SEED)
    assert spa["best_index"] == PLANTED
    assert spa["p_consistent"] <= rc["p_value"]
    assert spa["p_lower"] <= spa["p_consistent"] <= spa["p_upper"]


def test_spa_recentring_rules_are_ordered_on_a_junk_heavy_panel():
    """Add obviously-bad models and the three rules must separate.

    With half the zoo carrying a large negative mean, Hansen's consistent rule
    drops them from the recentring set while White's RC (== p_upper) keeps
    them, which is exactly the situation where the RC loses power.
    """
    perf = _one_planted()
    junk = perf[:, :20] - 1.0  # 20 hopeless models, mean ~= -1
    panel = np.hstack([perf, junk])
    spa = rc_mod.hansens_spa(panel, n_boot=1000, mean_block=10.0, seed=SEED)
    assert spa["p_lower"] <= spa["p_consistent"] <= spa["p_upper"]
    # The junk models must be excluded from the consistent recentring set.
    assert spa["n_recentred_consistent"] <= panel.shape[1] - 20


# --------------------------------------------------------------------------- #
# StepM
# --------------------------------------------------------------------------- #
def test_stepm_selects_the_planted_model():
    perf = _one_planted()
    out = rc_mod.stepwise_multiple_testing(
        perf, alpha=0.05, n_boot=1000, mean_block=10.0, seed=SEED
    )
    assert PLANTED in out["rejected"]
    assert len(out["rejected"]) <= 3, (
        f"StepM controls FWER at 5%, so it should name the planted model and "
        f"almost nothing else; got {out['rejected']}"
    )
    assert out["steps"] >= 1
    assert len(out["critical_values"]) == out["steps"]
    assert out["n_models"] == N_MODELS


def test_stepm_rejects_nothing_on_pure_noise():
    perf = _all_noise()
    out = rc_mod.stepwise_multiple_testing(
        perf, alpha=0.05, n_boot=1000, mean_block=10.0, seed=SEED
    )
    assert out["rejected"] == []
    assert out["steps"] == 1  # one pass, no rejection, stop
    assert len(out["critical_values"]) == 1


def test_stepm_respects_max_steps_and_validates_alpha():
    perf = _one_planted()
    out = rc_mod.stepwise_multiple_testing(
        perf, alpha=0.05, n_boot=200, mean_block=10.0, seed=SEED, max_steps=1
    )
    assert out["steps"] == 1
    with pytest.raises(ValueError):
        rc_mod.stepwise_multiple_testing(perf, alpha=0.0)
    with pytest.raises(ValueError):
        rc_mod.stepwise_multiple_testing(perf, alpha=1.0)


# --------------------------------------------------------------------------- #
# combined report
# --------------------------------------------------------------------------- #
def test_snooping_report_on_planted_panel():
    perf = _one_planted()
    names = [f"strat_{i:02d}" for i in range(N_MODELS)]
    rep = rc_mod.snooping_report(perf, names=names, n_boot=500, seed=SEED)
    assert rep["best_name"] == names[PLANTED]
    assert names[PLANTED] in rep["rejected_names"]
    assert rep["verdict"].startswith("SURVIVES")
    for key in ("reality_check", "spa", "stepm", "verdict", "n_models", "n_obs"):
        assert key in rep


def test_snooping_report_on_noise_panel_says_data_snooping():
    perf = _all_noise()
    rep = rc_mod.snooping_report(perf, n_boot=500, seed=SEED)
    assert rep["verdict"].startswith("DATA SNOOPING")
    assert rep["rejected_names"] == []
    assert rep["best_name"] == f"model_{rep['best_index']}"


def test_snooping_report_rejects_mismatched_names():
    perf = _all_noise()
    with pytest.raises(ValueError):
        rc_mod.snooping_report(perf, names=["only_one"], n_boot=100, seed=SEED)


# --------------------------------------------------------------------------- #
# degenerate inputs
# --------------------------------------------------------------------------- #
def test_single_model_panel_works():
    rng = np.random.default_rng(SEED)
    one = rng.standard_normal((200, 1)) + 0.3
    rc = rc_mod.whites_reality_check(one, n_boot=500, seed=SEED)
    assert rc["n_models"] == 1
    assert rc["best_index"] == 0
    assert rc["p_value"] < 0.05

    spa = rc_mod.hansens_spa(one, n_boot=500, seed=SEED)
    assert spa["n_models"] == 1
    stepm = rc_mod.stepwise_multiple_testing(one, n_boot=500, seed=SEED)
    assert stepm["rejected"] == [0]


def test_one_dimensional_input_is_treated_as_one_model():
    rng = np.random.default_rng(SEED)
    flat = rng.standard_normal(200) + 0.3
    out = rc_mod.whites_reality_check(flat, n_boot=200, seed=SEED)
    assert out["n_models"] == 1
    assert out["n_obs"] == 200


@pytest.mark.parametrize("t_obs", [0, 1, 5, 19])
def test_too_few_observations_raises_clear_value_error(t_obs):
    rng = np.random.default_rng(SEED)
    perf = rng.standard_normal((t_obs, 4))
    for fn in (
        rc_mod.whites_reality_check,
        rc_mod.hansens_spa,
        rc_mod.stepwise_multiple_testing,
        rc_mod.snooping_report,
    ):
        with pytest.raises(ValueError, match="at least 20 observations"):
            fn(perf)


def test_non_finite_input_raises():
    perf = _all_noise()[:, :4].copy()
    perf[3, 1] = np.nan
    with pytest.raises(ValueError, match="NaN"):
        rc_mod.whites_reality_check(perf)


def test_constant_column_does_not_blow_up():
    """A candidate that never traded has zero variance; omega must be floored."""
    perf = _all_noise()[:, :5].copy()
    perf[:, 2] = 0.0
    spa = rc_mod.hansens_spa(perf, n_boot=300, seed=SEED)
    assert np.all(np.isfinite(spa["omega"]))
    assert np.isfinite(spa["statistic"])


# --------------------------------------------------------------------------- #
# causality contract
# --------------------------------------------------------------------------- #
def test_ex_post_only_contract():
    """These are full-sample post-mortems, not signal generators.

    There is no causal wrapper to prefer here because nothing in this module
    maps a time series to a time series: every entry point collapses the whole
    ``(T, M)`` panel to scalars. Rather than fake a look-ahead test, this
    asserts the contract that makes the look-ahead question moot - no returned
    value is a per-timestamp series a caller could mistake for a signal - and
    that the warning is actually written in the docstrings.
    """
    assert rc_mod.EX_POST_ONLY == {
        "whites_reality_check",
        "hansens_spa",
        "stepwise_multiple_testing",
        "snooping_report",
    }

    perf = _one_planted()
    n_boot = 137  # deliberately != T_OBS and != N_MODELS so a length clash is real
    results = {
        "whites_reality_check": rc_mod.whites_reality_check(
            perf, n_boot=n_boot, seed=SEED
        ),
        "hansens_spa": rc_mod.hansens_spa(perf, n_boot=n_boot, seed=SEED),
        "stepwise_multiple_testing": rc_mod.stepwise_multiple_testing(
            perf, n_boot=n_boot, seed=SEED
        ),
    }
    for name, out in results.items():
        doc = inspect.getdoc(getattr(rc_mod, name)) or ""
        assert "Ex-post diagnostic only" in doc, f"{name} is missing the warning"
        for key, value in out.items():
            arr = np.asarray(value, dtype=object)
            assert arr.ndim <= 1
            if arr.ndim == 1:
                assert arr.shape[0] != T_OBS, (
                    f"{name}['{key}'] has length T={T_OBS} and could be mistaken "
                    f"for a per-timestamp signal"
                )

    doc = inspect.getdoc(rc_mod.snooping_report) or ""
    assert "Ex-post diagnostic only" in doc


def test_results_are_deterministic_for_a_fixed_seed():
    perf = _one_planted()
    a = rc_mod.whites_reality_check(perf, n_boot=300, seed=42)
    b = rc_mod.whites_reality_check(perf, n_boot=300, seed=42)
    assert a["p_value"] == b["p_value"]
    c = rc_mod.whites_reality_check(perf, n_boot=300, seed=43)
    # Different seed -> a different bootstrap draw; the statistic (which is not
    # bootstrapped) must be identical regardless.
    assert a["statistic"] == c["statistic"]
