"""Tests for strategies/_common/risk/drawdown.py — synthetic data only.

Every stochastic test seeds its RNG explicitly and picks a tolerance that holds
for that seed with margin; nothing here is allowed to be flaky.
"""
from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

dd = importlib.import_module("strategies._common.risk.drawdown")
risk_pkg = importlib.import_module("strategies._common.risk")

SEED = 0


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _equity(seed=SEED, n=300, drift=0.0005, vol=0.01):
    rng = np.random.default_rng(seed)
    r = rng.normal(drift, vol, n)
    return np.cumprod(1.0 + r)


# --------------------------------------------------------------------------
# Part A - geometry
# --------------------------------------------------------------------------
def test_drawdown_series_monotone_increasing_is_all_zero():
    equity = np.array([1.0, 1.1, 1.1, 1.2, 5.0, 5.0, 9.0])
    d = dd.drawdown_series(equity)
    assert np.allclose(d, 0.0)
    assert dd.max_drawdown(equity) == 0.0
    assert dd.time_under_water(equity) == 0
    assert dd.ulcer_index(equity) == 0.0


def test_max_drawdown_hand_built_curve_is_exactly_a_quarter():
    equity = [100.0, 120.0, 90.0, 150.0]
    # peak 120 -> trough 90 => 1 - 90/120 = 0.25 exactly
    assert dd.max_drawdown(equity) == 0.25
    d = dd.drawdown_series(equity)
    assert np.allclose(d, [0.0, 0.0, 0.25, 0.0])


def test_drawdown_series_preserves_series_index():
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    s = pd.Series([100.0, 120.0, 90.0, 150.0], index=idx)
    out = dd.drawdown_series(s)
    assert isinstance(out, pd.Series)
    assert out.index.equals(idx)


def test_drawdown_series_rejects_nonpositive_equity():
    with pytest.raises(ValueError):
        dd.drawdown_series([1.0, 0.0, 2.0])


def test_drawdown_table_two_episodes():
    idx = pd.date_range("2024-01-01", periods=8, freq="D")
    #            0      1      2     3      4      5      6     7
    equity = [100.0, 110.0, 99.0, 110.0, 121.0, 100.0, 90.0, 130.0]
    s = pd.Series(equity, index=idx)
    table = dd.drawdown_table(s, top_n=5)

    assert len(table) == 2
    # deepest first: peak 121 (i=4) -> trough 90 (i=6) -> recovery 130 (i=7)
    deep = table.iloc[0]
    assert deep["peak_date"] == idx[4]
    assert deep["trough_date"] == idx[6]
    assert deep["recovery_date"] == idx[7]
    assert deep["depth"] == pytest.approx(1.0 - 90.0 / 121.0)
    assert deep["drawdown_days"] == 2
    assert deep["recovery_days"] == 1

    # shallower: peak 110 (i=1) -> trough 99 (i=2) -> recovery 110 (i=3)
    shallow = table.iloc[1]
    assert shallow["peak_date"] == idx[1]
    assert shallow["trough_date"] == idx[2]
    assert shallow["recovery_date"] == idx[3]
    assert shallow["depth"] == pytest.approx(0.10)
    assert shallow["drawdown_days"] == 1
    assert shallow["recovery_days"] == 1


def test_drawdown_table_unrecovered_episode_has_nat_recovery():
    idx = pd.date_range("2024-01-01", periods=4, freq="D")
    s = pd.Series([100.0, 120.0, 90.0, 95.0], index=idx)
    table = dd.drawdown_table(s)
    assert len(table) == 1
    assert pd.isna(table.iloc[0]["recovery_date"])
    assert math.isnan(table.iloc[0]["recovery_days"])
    assert table.iloc[0]["trough_date"] == idx[2]


def test_drawdown_table_top_n_and_empty_case():
    equity = [100.0, 110.0, 99.0, 110.0, 121.0, 100.0, 90.0, 130.0]
    assert len(dd.drawdown_table(equity, top_n=1)) == 1
    empty = dd.drawdown_table([1.0, 2.0, 3.0])
    assert empty.empty
    assert list(empty.columns) == [
        "peak_date", "trough_date", "recovery_date",
        "depth", "drawdown_days", "recovery_days",
    ]


def test_time_under_water_counts_longest_run():
    #        0    1    2    3    4    5    6    7    8
    equity = [10., 12., 11., 12., 20., 19., 18., 17., 21.]
    # run 1: index 2 only              -> 1 bar
    # run 2: indices 5,6,7             -> 3 bars
    assert dd.time_under_water(equity) == 3


def test_ulcer_index_matches_manual_formula():
    equity = [100.0, 120.0, 90.0, 150.0]
    d = np.array([0.0, 0.0, 0.25, 0.0])
    assert dd.ulcer_index(equity) == pytest.approx(math.sqrt(np.mean(d**2)))


def test_martin_ratio_is_cagr_over_ulcer():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0005, 0.01, 300)
    eq = dd.equity_from_returns(r)
    expected = dd.cagr(r, 252) / dd.ulcer_index(eq)
    assert dd.martin_ratio(r, eq, 252) == pytest.approx(expected)


# --------------------------------------------------------------------------
# Part B - ratios
# --------------------------------------------------------------------------
def test_sortino_full_vs_downside_specific_relationship():
    """'full' divides by N, 'downside' by the downside count only.

    Since N_downside <= N, the 'full' denominator is the SMALLER downside
    deviation, hence the LARGER ratio. Assert the exact algebraic relationship,
    not merely inequality: the two deviations differ by sqrt(N_down / N).
    """
    # Asymmetric on purpose: many small gains, few large losses. The mean must
    # be strictly positive, otherwise both ratios are 0 and the comparison is
    # vacuous (0 > 0 is false).
    r = np.array([0.01] * 8 + [-0.05, -0.02], dtype=float)
    n = r.size
    n_down = int(np.sum(r < 0.0))
    assert 0 < n_down < n                      # the case actually is asymmetric

    full = dd.sortino_ratio(r, mar=0.0, periods_per_year=252, denominator="full")
    down = dd.sortino_ratio(r, mar=0.0, periods_per_year=252, denominator="downside")

    ssq = float(np.sum(np.minimum(r, 0.0) ** 2))
    dd_full = math.sqrt(ssq / n)
    dd_down = math.sqrt(ssq / n_down)
    assert dd_full < dd_down                   # 'full' is the smaller denominator
    assert full > down                         # therefore the larger ratio
    # exact relationship: ratio_full / ratio_down == dd_down / dd_full == sqrt(N/N_down)
    assert full / down == pytest.approx(math.sqrt(n / n_down))
    assert full == pytest.approx(
        np.mean(r) * 252 / (dd_full * math.sqrt(252))
    )


def test_sortino_rejects_unknown_denominator():
    with pytest.raises(ValueError):
        dd.sortino_ratio(np.array([0.01, -0.01, 0.02]), denominator="semi")


def test_sterling_raises_on_unknown_variant():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0005, 0.01, 600)
    with pytest.raises(ValueError):
        dd.sterling_ratio(r, variant="modified")
    # both documented variants work and are genuinely different numbers
    orig = dd.sterling_ratio(r, variant="original")
    avg3 = dd.sterling_ratio(r, variant="avg_n", n_largest=3)
    assert math.isfinite(orig) and math.isfinite(avg3)
    assert orig != avg3


def test_sterling_original_includes_the_ten_percent_constant():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0006, 0.01, 756)          # 3 chunks of 252
    annual_mdds = dd._annual_max_drawdowns(r, 252)
    assert len(annual_mdds) == 3
    expected = dd.cagr(r, 252) / (float(np.mean(annual_mdds)) + 0.10)
    assert dd.sterling_ratio(r, variant="original") == pytest.approx(expected)


def test_calmar_default_window_refuses_short_samples():
    rng = np.random.default_rng(SEED)
    short = rng.normal(0.0005, 0.01, 126)      # six months
    with pytest.raises(ValueError, match="trailing"):
        dd.calmar_ratio(short, periods_per_year=252)          # default 3y window
    # the full-sample variant is available, and explicitly not called a Calmar
    full = dd.calmar_ratio(short, periods_per_year=252, window_years=None)
    assert math.isfinite(full)


def test_calmar_window_uses_only_the_trailing_window():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0005, 0.01, 1260)         # five years
    windowed = dd.calmar_ratio(r, 252, window_years=3.0)
    manual = dd.calmar_ratio(r[-756:], 252, window_years=None)
    assert windowed == pytest.approx(manual)


def test_ratio_report_keys_conventions_and_short_sample_honesty():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0006, 0.01, 1260)
    rep = dd.ratio_report(r, 252)
    for key in (
        "cagr", "vol", "sharpe", "max_drawdown", "ulcer_index",
        "time_under_water", "calmar", "sterling_original", "sterling_avg3",
        "sortino_full", "sortino_downside", "martin", "n_obs",
    ):
        assert key in rep, key
        assert isinstance(rep[key], float), key
    assert isinstance(rep["conventions"], dict)
    for key in ("calmar", "sterling_original", "sortino_full", "sortino_downside"):
        assert key in rep["conventions"]
    assert "3-year" in rep["conventions"]["calmar"]
    assert rep["sortino_full"] > rep["sortino_downside"]

    # a short sample must be flagged, not silently mislabelled as a Calmar
    short = dd.ratio_report(rng.normal(0.0006, 0.01, 200), 252)
    assert "NOT Young's Calmar" in short["conventions"]["calmar"]


# --------------------------------------------------------------------------
# Part C - expected maximum drawdown
# --------------------------------------------------------------------------
def test_expected_max_drawdown_zero_drift_exact_and_monte_carlo():
    sigma, T = 0.2, 1.0
    exact = dd.expected_max_drawdown(0.0, sigma, T)         # auto -> exact form
    assert exact == pytest.approx(math.sqrt(math.pi / 2.0) * sigma * math.sqrt(T),
                                  abs=1e-12)
    # "1.2533" is sqrt(pi/2) rounded to 5 significant figures, so it differs
    # from the exact constant by 1.4e-5 -> 2.8e-6 once scaled by sigma=0.2.
    # Demanding a 1e-6 match to the rounded constant is arithmetically
    # impossible; 1e-5 is the tightest tolerance it actually supports. The
    # exact identity is asserted above at 1e-12.
    assert exact == pytest.approx(1.2533 * 0.2, abs=1e-5)

    mc = dd.expected_max_drawdown(
        0.0, sigma, T, method="mc", n_paths=20_000, seed=SEED, n_steps=2000
    )
    # discrete monitoring biases MC downward by ~2%, MC noise adds <1%
    assert abs(mc / exact - 1.0) < 0.05


def test_expected_max_drawdown_growth_laws():
    """sqrt(T) with no edge, log(T) with an edge, linear T against you."""
    sigma = 0.2
    # no edge: quadrupling T doubles E[MDD]
    a = dd.expected_max_drawdown(0.0, sigma, 1.0)
    b = dd.expected_max_drawdown(0.0, sigma, 4.0)
    assert b / a == pytest.approx(2.0, rel=1e-12)

    # positive edge, deep in the asymptotic regime: growth is logarithmic, so
    # a 10x horizon adds a constant, it does not multiply by sqrt(10)
    mu = 0.5
    t1, t2 = 10.0, 100.0
    e1 = dd.expected_max_drawdown(mu, sigma, t1, method="asymptotic")
    e2 = dd.expected_max_drawdown(mu, sigma, t2, method="asymptotic")
    assert e2 - e1 == pytest.approx((sigma**2 / (2 * mu)) * math.log(10.0))
    assert e2 / e1 < math.sqrt(t2 / t1)

    # negative drift: linear in T
    n1 = dd.expected_max_drawdown(-0.5, sigma, t1, method="asymptotic")
    n2 = dd.expected_max_drawdown(-0.5, sigma, t2, method="asymptotic")
    assert n2 / n1 == pytest.approx(t2 / t1)


def test_expected_max_drawdown_refuses_invalid_asymptotic_and_falls_back():
    """Outside its regime the asymptotic is negative; auto must simulate."""
    mu, sigma, T = 0.05, 0.2, 1.0
    tau = 2 * mu**2 * T / sigma**2
    assert tau < dd.EMDD_ASYMPTOTIC_THRESHOLD
    with pytest.raises(ValueError, match="non-positive"):
        dd.expected_max_drawdown(mu, sigma, T, method="asymptotic")
    auto = dd.expected_max_drawdown(
        mu, sigma, T, method="auto", n_paths=4000, seed=SEED, n_steps=1000
    )
    assert auto > 0.0
    # with a nearly negligible edge over one unit of time it should sit close to
    # the driftless answer rather than to the broken asymptotic
    assert 0.5 < auto / (math.sqrt(math.pi / 2) * sigma) < 1.05


def test_expected_max_drawdown_argument_validation():
    with pytest.raises(ValueError):
        dd.expected_max_drawdown(0.0, 0.2, 1.0, method="closed-form")
    with pytest.raises(ValueError):
        dd.expected_max_drawdown(0.0, -0.2, 1.0)
    with pytest.raises(ValueError):
        dd.expected_max_drawdown(0.0, 0.2, 0.0)
    with pytest.raises(ValueError, match="exact closed form"):
        dd.expected_max_drawdown(0.1, 0.2, 1.0, method="exact")
    with pytest.raises(ValueError, match="asymptotic is not defined"):
        dd.expected_max_drawdown(0.0, 0.2, 1.0, method="asymptotic")


def test_mdd_scaling_check_frame():
    frame = dd.mdd_scaling_check(
        0.5, 0.2, [1.0, 10.0], n_paths=1000, seed=SEED, steps_per_unit_time=200
    )
    assert list(frame.columns) == [
        "T", "tau", "regime_ok", "closed_form", "monte_carlo", "rel_error"
    ]
    assert len(frame) == 2
    assert frame["tau"].iloc[0] == pytest.approx(2 * 0.25 * 1.0 / 0.04)
    assert bool(frame["regime_ok"].iloc[0]) is True
    assert (frame["monte_carlo"] > 0).all()
    # deep in the regime (tau = 125 and 1250) the asymptotic should be within
    # ~25% of simulation; this is a diagnostic, not a precision claim
    assert (frame["rel_error"].abs() < 0.25).all()


# --------------------------------------------------------------------------
# Part D - MDD-constrained leverage
# --------------------------------------------------------------------------
def test_merton_fraction_reduces_to_kelly_at_log_utility():
    assert dd.merton_fraction(0.10, 0.20, r=0.02, gamma=1.0) == pytest.approx(
        0.08 / 0.04
    )
    assert dd.merton_fraction(0.10, 0.20, r=0.0, gamma=2.0) == pytest.approx(
        0.10 / (2 * 0.04)
    )


def test_grossman_zhou_sanity_properties():
    alpha, pi_m = 0.8, 2.0

    # 1) pi = pi_M at d = 0
    assert dd.grossman_zhou_leverage(0.0, alpha, pi_m) == pytest.approx(pi_m)

    # 2) pi = 0 at the floor d = 1 - alpha
    assert dd.grossman_zhou_leverage(1.0 - alpha, alpha, pi_m) == pytest.approx(
        0.0, abs=1e-12
    )

    # 3) strictly decreasing in d on [0, 1-alpha], checked on a grid
    grid = np.linspace(0.0, 1.0 - alpha, 51)
    pi = np.asarray(dd.grossman_zhou_leverage(grid, alpha, pi_m))
    assert np.all(np.diff(pi) < 0.0)
    assert pi[0] == pytest.approx(pi_m)
    assert pi[-1] == pytest.approx(0.0, abs=1e-12)

    # clipped at zero past the floor, never short
    beyond = np.asarray(dd.grossman_zhou_leverage(
        np.linspace(1.0 - alpha, 0.99, 20), alpha, pi_m
    ))
    assert np.all(beyond >= 0.0)
    assert beyond[-1] == 0.0


def test_grossman_zhou_is_concave_in_drawdown_not_convex():
    """The docstring claims concavity in depth; verify it numerically."""
    alpha, pi_m = 0.75, 1.5
    grid = np.linspace(0.0, 1.0 - alpha - 1e-6, 200)
    pi = np.asarray(dd.grossman_zhou_leverage(grid, alpha, pi_m))
    second = np.diff(pi, 2)
    assert np.all(second < 0.0)                # concave: de-risking accelerates


def test_grossman_zhou_types_and_validation():
    idx = pd.date_range("2024-01-01", periods=3, freq="D")
    s = pd.Series([0.0, 0.05, 0.10], index=idx)
    out = dd.grossman_zhou_leverage(s, 0.8, 2.0)
    assert isinstance(out, pd.Series) and out.index.equals(idx)
    assert isinstance(dd.grossman_zhou_leverage(0.1, 0.8, 2.0), float)
    with pytest.raises(ValueError):
        dd.grossman_zhou_leverage(0.1, 1.0, 2.0)          # alpha must be < 1
    with pytest.raises(ValueError):
        dd.grossman_zhou_leverage(-0.1, 0.8, 2.0)         # drawdown in [0,1)


def _breach_prob(res: dict, mu: float, sigma: float, dd_cap: float, r: float = 0.0):
    """P(all-time log drawdown > x) at the returned leverage, from the model."""
    L = res["leverage"]
    nu = L * (mu - r) - 0.5 * L**2 * sigma**2
    s2 = (L * sigma) ** 2
    x = -math.log(1.0 - dd_cap)
    return math.exp(-2.0 * nu * x / s2)


def test_kelly_dd_cap_monotone_in_the_cap():
    mu, sigma, prob = 0.10, 0.20, 0.05
    caps = np.linspace(0.05, 0.50, 20)         # all binding for these parameters
    levs = [dd.kelly_leverage_with_dd_cap(mu, sigma, c, prob)["leverage"] for c in caps]
    assert all(r["binding"] for r in
               [dd.kelly_leverage_with_dd_cap(mu, sigma, c, prob) for c in caps])
    assert np.all(np.diff(levs) > 0.0)         # looser cap -> more leverage
    # i.e. a TIGHTER cap yields strictly LOWER leverage
    assert levs[0] < levs[-1]


def test_kelly_dd_cap_returned_leverage_satisfies_the_constraint():
    mu, sigma, prob = 0.10, 0.20, 0.05
    for cap in (0.05, 0.10, 0.20, 0.40, 0.60):
        res = dd.kelly_leverage_with_dd_cap(mu, sigma, cap, prob)
        p = _breach_prob(res, mu, sigma, cap)
        assert p <= prob + 1e-9, (cap, p)
        # the numeric brentq solve agrees with the closed form
        assert res["max_admissible_leverage"] == pytest.approx(
            res["closed_form_leverage"], rel=1e-9
        )
        assert res["fraction_of_kelly"] == pytest.approx(
            res["leverage"] / res["full_kelly"]
        )
        assert res["nu"] == pytest.approx(
            res["leverage"] * mu - 0.5 * res["leverage"] ** 2 * sigma**2
        )


def test_kelly_dd_cap_not_binding_when_cap_is_loose():
    mu, sigma = 0.10, 0.20
    # binding iff -log(1-dd_cap) < log(1/prob); with prob=0.05 the crossover is
    # dd_cap = 1 - 0.05 = 0.95
    loose = dd.kelly_leverage_with_dd_cap(mu, sigma, 0.99, prob=0.05)
    assert loose["binding"] is False
    assert loose["leverage"] == pytest.approx(loose["full_kelly"])
    assert loose["fraction_of_kelly"] == pytest.approx(1.0)
    assert "does NOT bind" in loose["note"]

    tight = dd.kelly_leverage_with_dd_cap(mu, sigma, 0.20, prob=0.05)
    assert tight["binding"] is True
    assert tight["leverage"] < tight["full_kelly"]


def test_kelly_dd_cap_no_edge_is_infeasible_and_says_so():
    res = dd.kelly_leverage_with_dd_cap(0.0, 0.20, 0.20, prob=0.05)
    assert res["leverage"] == 0.0
    assert res["binding"] is True
    assert "no edge" in res["note"]


def test_kelly_dd_cap_argument_validation():
    with pytest.raises(ValueError):
        dd.kelly_leverage_with_dd_cap(0.1, 0.2, 1.0)
    with pytest.raises(ValueError):
        dd.kelly_leverage_with_dd_cap(0.1, 0.2, 0.2, prob=0.0)
    with pytest.raises(ValueError):
        dd.kelly_leverage_with_dd_cap(0.1, 0.0, 0.2)


def test_complexity_budget_inverse_square_law():
    base = dd.complexity_budget(1.0, 0.20, 1000, growth_loss_tolerance=0.001, k=1.0)
    doubled = dd.complexity_budget(2.0, 0.20, 1000, growth_loss_tolerance=0.001, k=1.0)
    # doubling leverage quarters the admissible parameter count, exactly
    assert doubled["max_parameters"] == pytest.approx(
        base["max_parameters"] / 4.0, rel=1e-12
    )
    quadrupled = dd.complexity_budget(4.0, 0.20, 1000, growth_loss_tolerance=0.001)
    assert quadrupled["max_parameters"] == pytest.approx(
        base["max_parameters"] / 16.0, rel=1e-12
    )
    # closed form
    assert base["max_parameters"] == pytest.approx(
        2 * 0.001 * 1000 / (1.0 * 0.20**2 * 1.0**2)
    )
    # p_max * loss_per_parameter == the tolerance, by construction
    assert base["max_parameters"] * base["loss_per_parameter"] == pytest.approx(0.001)
    assert "HEURISTIC" in base["assumptions"]


def test_complexity_budget_validation():
    with pytest.raises(ValueError):
        dd.complexity_budget(0.0, 0.2, 100)
    with pytest.raises(ValueError):
        dd.complexity_budget(1.0, 0.2, 0)
    with pytest.raises(ValueError):
        dd.complexity_budget(1.0, 0.2, 100, k=0.0)


# --------------------------------------------------------------------------
# causality: no look-ahead in the time-series -> time-series maps
# --------------------------------------------------------------------------
def test_no_lookahead_drawdown_series():
    rng = np.random.default_rng(0)
    x = np.cumprod(1.0 + rng.normal(0.0003, 0.012, 300))
    full = np.asarray(dd.drawdown_series(x))
    for cut in (150, 200, 250):
        trunc = np.asarray(dd.drawdown_series(x[:cut]))
        assert np.allclose(trunc[-1], full[cut - 1], equal_nan=True)
        # stronger: the whole truncated series must match, not just its last bar
        assert np.allclose(trunc, full[:cut], equal_nan=True)


def test_no_lookahead_grossman_zhou_leverage():
    rng = np.random.default_rng(0)
    x = np.cumprod(1.0 + rng.normal(0.0003, 0.012, 300))

    def fn(equity):
        d = np.asarray(dd.drawdown_series(equity))
        return np.asarray(dd.grossman_zhou_leverage(d, alpha=0.8, merton_fraction=2.0))

    full = fn(x)
    for cut in (150, 200, 250):
        trunc = fn(x[:cut])
        assert np.allclose(trunc[-1], full[cut - 1], equal_nan=True)
        assert np.allclose(trunc, full[:cut], equal_nan=True)


def test_no_lookahead_time_under_water_is_monotone_in_sample_length():
    """A scalar summary, but it must never shrink as data is appended."""
    rng = np.random.default_rng(0)
    x = np.cumprod(1.0 + rng.normal(0.0003, 0.012, 300))
    values = [dd.time_under_water(x[:cut]) for cut in (150, 200, 250, 300)]
    assert all(b >= a for a, b in zip(values, values[1:]))


# --------------------------------------------------------------------------
# package wiring
# --------------------------------------------------------------------------
def test_package_exports_public_names():
    for name in dd.__all__:
        assert hasattr(risk_pkg, name), name
        assert name in risk_pkg.__all__, name
    assert risk_pkg.max_drawdown is dd.max_drawdown
