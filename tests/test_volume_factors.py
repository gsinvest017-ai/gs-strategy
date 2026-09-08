"""Tests for strategies/_common/factors/volume.py — synthetic series only.

The load-bearing test here is ``test_no_lookahead``: every factor is re-run on
truncated inputs and must reproduce the full-sample values bar for bar. A
factor that peeks at the future passes every other test in this file and fails
that one.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

vol = importlib.import_module("strategies._common.factors.volume")

SEED = 20260828


# --------------------------------------------------------------------------
# fixtures / builders
# --------------------------------------------------------------------------
def _inputs(n: int = 300, seed: int = SEED) -> dict[str, np.ndarray]:
    """A well-behaved OHLCV panel: GBM prices, lognormal volume."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0002, 0.012, n)
    close = 100.0 * np.exp(np.cumsum(rets))
    volume = np.exp(rng.normal(np.log(1e6), 0.4, n))
    high = close * (1.0 + np.abs(rng.normal(0.0, 0.004, n)))
    low = close * (1.0 - np.abs(rng.normal(0.0, 0.004, n)))
    open_ = close * np.exp(rng.normal(0.0, 0.003, n))
    return {
        "open_": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "returns": np.concatenate([[0.0], np.diff(close) / close[:-1]]),
        "dollar_volume": close * volume,
    }


# Each entry maps the input dict to a 1-D float array. Every one of them must
# be strictly causal.
CAUSAL_CASES = [
    ("obv", lambda d: vol.obv(d["close"], d["volume"])),
    ("obv_slope", lambda d: vol.obv_slope(d["close"], d["volume"], window=20)),
    ("excess_volume_log", lambda d: vol.excess_volume(d["volume"], window=20)),
    (
        "excess_volume_raw",
        lambda d: vol.excess_volume(d["volume"], window=20, log=False),
    ),
    (
        "volume_breakout",
        lambda d: np.asarray(
            vol.volume_breakout(d["volume"], window=20, k=1.5), dtype=float
        ),
    ),
    (
        "pv_divergence_spearman",
        lambda d: vol.price_volume_divergence(d["close"], d["volume"], window=20),
    ),
    (
        "pv_divergence_pearson",
        lambda d: vol.price_volume_divergence(
            d["close"], d["volume"], window=20, method="pearson"
        ),
    ),
    (
        "divergence_direction",
        lambda d: vol.divergence_flag(d["close"], d["volume"], window=20).direction,
    ),
    (
        "divergence_flag",
        lambda d: np.asarray(
            vol.divergence_flag(d["close"], d["volume"], window=20).flag, dtype=float
        ),
    ),
    (
        "typical_price",
        lambda d: vol.typical_price(d["high"], d["low"], d["close"]),
    ),
    (
        "rolling_vwap",
        lambda d: vol.rolling_vwap(
            vol.typical_price(d["high"], d["low"], d["close"]), d["volume"], 20
        ),
    ),
    (
        "vwap_deviation",
        lambda d: vol.vwap_deviation(
            d["close"], vol.rolling_vwap(d["close"], d["volume"], 20)
        ),
    ),
    ("twap", lambda d: vol.twap(d["open_"], d["high"], d["low"], d["close"])),
    (
        "amihud",
        lambda d: vol.amihud_illiquidity(d["returns"], d["dollar_volume"], window=20),
    ),
    (
        "standardize_zscore_roll",
        lambda d: vol.standardize(d["volume"], window=30, method="zscore"),
    ),
    (
        "standardize_zscore_expanding",
        lambda d: vol.standardize(d["volume"], method="zscore"),
    ),
    (
        "standardize_rank_roll",
        lambda d: vol.standardize(d["volume"], window=30, method="rank"),
    ),
    (
        "standardize_rank_expanding",
        lambda d: vol.standardize(d["volume"], method="rank"),
    ),
    (
        "standardize_robust_roll",
        lambda d: vol.standardize(d["volume"], window=30, method="robust"),
    ),
    (
        "standardize_robust_expanding",
        lambda d: vol.standardize(d["volume"], method="robust"),
    ),
    ("detrend_diff", lambda d: vol.detrend(d["close"], method="diff")),
    ("detrend_diff_lag5", lambda d: vol.detrend(d["close"], method="diff", window=5)),
    ("detrend_logdiff", lambda d: vol.detrend(d["close"], method="logdiff")),
    (
        "detrend_ols_roll",
        lambda d: vol.detrend(d["close"], method="ols", window=30),
    ),
    (
        "detrend_ols_expanding",
        lambda d: vol.detrend(d["close"], method="ols"),
    ),
]


# --------------------------------------------------------------------------
# the no-look-ahead property
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name,fn", CAUSAL_CASES, ids=[c[0] for c in CAUSAL_CASES])
def test_no_lookahead(name, fn):
    """Truncating the input must not change any value that was already computed."""
    d = _inputs(n=300)
    full = np.asarray(fn(d), dtype=float)
    assert full.shape == (300,)
    for cut in (150, 200, 250):
        trunc = np.asarray(fn({k: v[:cut] for k, v in d.items()}), dtype=float)
        assert trunc.shape == (cut,), name
        # The last value of the truncated run is the acid test: it is the value
        # a live system would have produced on that bar.
        assert np.allclose(
            trunc[-1], full[cut - 1], equal_nan=True
        ), f"{name}: look-ahead at t={cut - 1}"
        # ... and causality implies the whole prefix matches, not just the tip.
        assert np.allclose(
            trunc, full[:cut], equal_nan=True
        ), f"{name}: prefix mismatch at cut={cut}"


def test_noncausal_registry_is_empty():
    """Nothing in this module is exempt from causality — keep it that way.

    If a centred/full-sample diagnostic is ever added it must be registered in
    NONCAUSAL_FUNCTIONS (and named accordingly), which makes this test fail
    loudly and forces the author to exclude it from CAUSAL_CASES on purpose.
    """
    assert vol.NONCAUSAL_FUNCTIONS == ()
    assert not [n for n in vol.__all__ if n.endswith("_noncausal")]
    # every exported callable is exercised by the causality test above
    covered = {
        "obv",
        "obv_slope",
        "excess_volume",
        "volume_breakout",
        "price_volume_divergence",
        "divergence_flag",
        "typical_price",
        "rolling_vwap",
        "vwap_deviation",
        "twap",
        "amihud_illiquidity",
        "standardize",
        "detrend",
    }
    exported = {
        name
        for name in vol.__all__
        if callable(getattr(vol, name)) and not isinstance(getattr(vol, name), type)
    }
    assert exported == covered, exported.symmetric_difference(covered)


# --------------------------------------------------------------------------
# 1-2. OBV
# --------------------------------------------------------------------------
def test_obv_hand_computed_six_bars():
    """Hand-computed OBV, including the sign(0) = 0 and OBV_0 = 0 conventions.

        bar   close   volume   sign   contribution   OBV
        0     100     10       n/a    0              0
        1     101     20       +1     +20            20
        2     101     30        0       0            20
        3      99     40       -1     -40           -20
        4     102     50       +1     +50            30
        5     102     60        0       0            30
    """
    close = np.array([100.0, 101.0, 101.0, 99.0, 102.0, 102.0])
    volume = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    expected = np.array([0.0, 20.0, 20.0, -20.0, 30.0, 30.0])
    np.testing.assert_allclose(vol.obv(close, volume), expected)


def test_obv_is_a_signed_volume_partial_sum():
    """Increments of OBV are exactly sign(dP) * V — the random-walk framing."""
    d = _inputs(n=100)
    o = vol.obv(d["close"], d["volume"])
    inc = np.diff(o)
    sgn = np.sign(np.diff(d["close"]))
    np.testing.assert_allclose(inc, sgn * d["volume"][1:])


def test_obv_slope_signs_and_scale():
    n = 60
    volume = np.full(n, 1000.0)
    up = 100.0 + np.arange(n, dtype=float)
    down = 100.0 - np.arange(n, dtype=float)
    s_up = vol.obv_slope(up, volume, window=20)
    s_down = vol.obv_slope(down, volume, window=20)
    assert np.isnan(s_up[:19]).all()
    # every bar is an up bar -> OBV rises by exactly one bar's volume per bar,
    # so the volume-normalised slope is +1 (and -1 for the mirror).
    np.testing.assert_allclose(s_up[19:], 1.0)
    np.testing.assert_allclose(s_down[19:], -1.0)


def test_obv_slope_is_scale_free():
    """Doubling volume leaves the normalised slope unchanged."""
    d = _inputs(n=200)
    a = vol.obv_slope(d["close"], d["volume"], window=20)
    b = vol.obv_slope(d["close"], d["volume"] * 1000.0, window=20)
    np.testing.assert_allclose(a, b, equal_nan=True)


# --------------------------------------------------------------------------
# 3-4. excess volume / breakout
# --------------------------------------------------------------------------
@pytest.mark.parametrize("log", [True, False])
def test_excess_volume_constant_series_is_exactly_zero(log):
    """A constant series is 0 sigma from its own mean — not NaN, not inf.

    Note the sample std of N identical doubles is ~1e-16 rather than 0.0
    (the mean carries a rounding error), so this only holds because
    ``_safe_ratio`` treats a relatively-degenerate dispersion as degenerate.
    """
    volume = np.full(60, 1234.0)
    ex = vol.excess_volume(volume, window=20, log=log)
    assert np.isnan(ex[:20]).all(), "warm-up must be NaN"
    assert np.all(ex[20:] == 0.0)
    assert np.isfinite(ex[20:]).all()


def test_excess_volume_spike_out_of_a_perfectly_constant_window_is_nan():
    """The documented cost of the never-inf policy, asserted rather than hidden.

    A non-zero deviation measured against a zero-dispersion window is an
    infinite z-score. ``_safe_ratio`` returns NaN there instead of +inf. This
    only bites on synthetic/degenerate data (a genuinely constant volume
    window), but it is a real behaviour and callers should know it.
    """
    volume = np.concatenate([np.full(20, 1000.0), [5000.0]])
    ex = vol.excess_volume(volume, window=20, log=False)
    assert np.isnan(ex[-1])
    assert not np.isinf(ex).any()
    assert not np.asarray(vol.volume_breakout(volume, window=20, log=False))[-1]


def test_excess_volume_flags_a_real_spike_and_ignores_noise():
    """8-sigma spike -> flagged; 299 ordinary noise bars -> not flagged."""
    rng = np.random.default_rng(11)
    n, w, sigma = 300, 20, 50.0
    volume = 1000.0 + rng.normal(0.0, sigma, n)
    spike = 200
    volume[spike] = 1000.0 + 8.0 * sigma

    ex = vol.excess_volume(volume, window=w, log=False)
    assert ex[spike] > 4.0, ex[spike]

    others = np.delete(ex, spike)
    assert np.nanmax(others) < 4.0, np.nanmax(others)

    flags = np.asarray(vol.volume_breakout(volume, window=w, k=4.0, log=False))
    assert flags[spike]
    assert flags.sum() == 1, np.flatnonzero(flags)
    # warm-up bars are False, never NaN
    assert flags.dtype == bool
    assert not flags[:w].any()


def test_excess_volume_excludes_t_from_its_own_normaliser():
    """The leak this exclusion prevents, made visible.

    Recompute the z-score the naive way (window INCLUDING t) and check it is
    strictly smaller for the spike bar. Same data, same window — the only
    difference is whether the observation normalises itself.
    """
    rng = np.random.default_rng(19)
    w = 20
    volume = np.concatenate([1000.0 + rng.normal(0.0, 50.0, w), [5000.0]])
    ex = vol.excess_volume(volume, window=w, log=False)

    leaky_window = volume[1:]  # the w bars ending AT t, i.e. including t
    leaky = (volume[-1] - leaky_window.mean()) / leaky_window.std(ddof=1)
    assert np.isfinite(ex[-1]) and np.isfinite(leaky)
    assert leaky < ex[-1] / 2.0, (leaky, ex[-1])

    # The docstring's Samuelson-inequality claim, made testable: a self-
    # normalised z-score cannot exceed (w-1)/sqrt(w) however big the spike is.
    ceiling = (w - 1) / np.sqrt(w)
    huge = np.concatenate([1000.0 + rng.normal(0.0, 50.0, w), [1e12]])
    leaky_huge_window = huge[1:]
    leaky_huge = (huge[-1] - leaky_huge_window.mean()) / leaky_huge_window.std(ddof=1)
    assert leaky_huge <= ceiling * (1 + 1e-12)  # bound is attained, not merely approached
    assert vol.excess_volume(huge, window=w, log=False)[-1] > 100 * ceiling


def test_excess_volume_normaliser_sample_is_exactly_the_previous_window():
    """Pin the normaliser sample analytically: it is x[t-w : t], nothing else.

    Worth stating why this test exists alongside ``test_no_lookahead``: the
    truncation property test CANNOT catch a "window includes t" leak, because
    such a window still uses only data at indices <= t and therefore survives
    truncation unchanged (verified by mutation). Look-ahead and self-
    normalisation are two different bugs and need two different tests.
    """
    w = 20
    volume = np.concatenate([np.arange(1.0, w + 1), [100.0]])
    mu = np.arange(1.0, w + 1).mean()          # 10.5
    sigma = np.arange(1.0, w + 1).std(ddof=1)  # 5.9160797831...
    ex = vol.excess_volume(volume, window=w, log=False)
    assert ex[-1] == pytest.approx((100.0 - mu) / sigma)


def test_standardize_rank_sample_is_exactly_the_previous_window():
    """Same pinning for the rank normaliser, ties included."""
    x = np.array([0.0, 1.0, 2.0, 3.0, 2.0])
    r = np.asarray(vol.standardize(x, window=4, method="rank"))
    # at t=4 the trailing sample is [0, 1, 2, 3]: one tie (2), two strictly below
    assert r[-1] == pytest.approx(2.0 * ((2 + 0.5) / 4) - 1.0)


def test_excess_volume_min_periods_controls_warmup():
    rng = np.random.default_rng(3)
    volume = np.exp(rng.normal(13.0, 0.3, 50))
    strict = vol.excess_volume(volume, window=20)
    loose = vol.excess_volume(volume, window=20, min_periods=5)
    assert np.isnan(strict[:20]).all()
    assert np.isnan(loose[:5]).all()
    assert np.isfinite(loose[5:]).all()


# --------------------------------------------------------------------------
# 5. divergence
# --------------------------------------------------------------------------
def _zigzag(n: int, up_move: float, up_vol: float, dn_move: float, dn_vol: float):
    """Alternating bars: odd bars move by ``up_move`` on ``up_vol``, etc."""
    close = np.empty(n)
    volume = np.empty(n)
    price = 100.0
    for t in range(n):
        if t % 2 == 1:
            price += up_move
            volume[t] = up_vol
        else:
            price += dn_move
            volume[t] = dn_vol
        close[t] = price
    return close, volume


def test_divergence_flag_fires_on_price_up_volume_not_confirming():
    """Price grinds up (+1 per 2 bars) but the volume is on the DOWN bars.

    This is what "rising on shrinking volume" has to mean mechanically: a
    monotone price rise on merely-decreasing volume still produces a monotone
    OBV and hence a +1 rank correlation. For OBV to *disagree* with price, the
    down bars must carry the volume — which is exactly the accumulation-
    distribution story the classic divergence is told about.
    """
    n, w = 120, 20
    close, volume = _zigzag(n, up_move=2.0, up_vol=100.0, dn_move=-1.0, dn_vol=500.0)
    assert close[-1] > close[0]  # price really does trend up

    corr = vol.price_volume_divergence(close, volume, window=w)
    res = vol.divergence_flag(close, volume, window=w)
    flag = np.asarray(res.flag)
    direction = np.asarray(res.direction)

    assert np.nanmax(corr[w:]) < 0.0, np.nanmax(corr[w:])
    assert flag[w:].all()
    assert np.all(direction[w:] == -1.0)  # bearish divergence
    assert not flag[: w - 1].any()  # warm-up never fires


def test_divergence_flag_mirrors_the_bullish_case():
    """Price grinds down while the volume sits on the up bars -> direction +1."""
    n, w = 120, 20
    close, volume = _zigzag(n, up_move=1.0, up_vol=500.0, dn_move=-2.0, dn_vol=100.0)
    assert close[-1] < close[0]
    res = vol.divergence_flag(close, volume, window=w)
    assert np.asarray(res.flag)[w:].all()
    assert np.all(np.asarray(res.direction)[w:] == 1.0)


def test_divergence_flag_silent_when_volume_confirms():
    """Price rises on expanding volume -> OBV confirms -> no flag anywhere."""
    n, w = 120, 20
    close = 100.0 + 0.5 * np.arange(n, dtype=float)
    volume = 1000.0 + 10.0 * np.arange(n, dtype=float)
    corr = vol.price_volume_divergence(close, volume, window=w)
    np.testing.assert_allclose(corr[w - 1 :], 1.0)
    res = vol.divergence_flag(close, volume, window=w)
    assert not np.asarray(res.flag).any()
    assert np.all(np.asarray(res.direction) == 0.0)


def test_price_volume_divergence_bounds_and_degenerate_windows():
    d = _inputs(n=200)
    corr = vol.price_volume_divergence(d["close"], d["volume"], window=20)
    finite = corr[np.isfinite(corr)]
    assert finite.size > 100
    assert finite.min() >= -1.0 and finite.max() <= 1.0
    # flat price -> no rank variance -> undefined, not 0.0
    flat = np.full(60, 50.0)
    corr_flat = vol.price_volume_divergence(flat, np.full(60, 10.0), window=20)
    assert np.isnan(corr_flat).all()


def test_price_volume_divergence_rejects_unknown_method():
    d = _inputs(n=60)
    with pytest.raises(ValueError):
        vol.price_volume_divergence(d["close"], d["volume"], window=20, method="kendall")


# --------------------------------------------------------------------------
# 6. price benchmarks
# --------------------------------------------------------------------------
def test_typical_price_and_twap_arithmetic():
    o = np.array([10.0, 20.0])
    h = np.array([12.0, 24.0])
    lo = np.array([8.0, 16.0])
    c = np.array([11.0, 20.0])
    np.testing.assert_allclose(vol.typical_price(h, lo, c), [(12 + 8 + 11) / 3, (24 + 16 + 20) / 3])
    np.testing.assert_allclose(vol.twap(o, h, lo, c), [(10 + 12 + 8 + 11) / 4, 20.0])


def test_rolling_vwap_hand_computed():
    price = np.array([10.0, 20.0, 30.0])
    volume = np.array([1.0, 1.0, 2.0])
    out = vol.rolling_vwap(price, volume, 3)
    assert np.isnan(out[:2]).all()
    np.testing.assert_allclose(out[2], (10 * 1 + 20 * 1 + 30 * 2) / 4.0)


def test_rolling_vwap_zero_volume_window_is_nan_not_inf():
    price = np.array([10.0, 11.0, 12.0, 13.0])
    volume = np.zeros(4)
    out = vol.rolling_vwap(price, volume, 2)
    assert np.isnan(out).all()


def test_vwap_deviation_is_relative_and_guards_zero():
    close = np.array([110.0, 90.0, 100.0])
    vwap = np.array([100.0, 100.0, 0.0])
    out = vol.vwap_deviation(close, vwap)
    np.testing.assert_allclose(out[:2], [0.1, -0.1])
    assert np.isnan(out[2])
    assert np.isfinite(out[:2]).all()


# --------------------------------------------------------------------------
# 7. Amihud
# --------------------------------------------------------------------------
def test_amihud_hand_computed():
    r = np.array([0.01, -0.02, 0.03])
    dv = np.array([100.0, 100.0, 100.0])
    out = vol.amihud_illiquidity(r, dv, window=3)
    assert np.isnan(out[:2]).all()
    np.testing.assert_allclose(out[2], (0.01 + 0.02 + 0.03) / 100.0 / 3.0)


def test_amihud_zero_dollar_volume_is_nan_never_inf():
    rng = np.random.default_rng(SEED)
    r = rng.normal(0.0, 0.01, 100)
    out_all_zero = vol.amihud_illiquidity(r, np.zeros(100), window=20)
    assert np.isnan(out_all_zero).all()
    assert not np.isinf(out_all_zero).any()

    dv = np.full(100, 1e6)
    dv[50] = 0.0  # a single halted / untraded bar
    out = vol.amihud_illiquidity(r, dv, window=20)
    assert not np.isinf(out).any()
    assert np.isfinite(out[19:]).all()  # the bad bar is skipped, not fatal


def test_amihud_is_higher_for_thinner_markets():
    rng = np.random.default_rng(5)
    r = rng.normal(0.0, 0.01, 200)
    thick = vol.amihud_illiquidity(r, np.full(200, 1e8), window=20)
    thin = vol.amihud_illiquidity(r, np.full(200, 1e6), window=20)
    assert np.nanmean(thin) > np.nanmean(thick)


# --------------------------------------------------------------------------
# 8. standardize
# --------------------------------------------------------------------------
def test_standardize_zscore_recovers_unit_moments():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(2000)
    z = np.asarray(vol.standardize(x, window=250, method="zscore"))
    z = z[np.isfinite(z)]
    assert z.size > 1500
    assert abs(z.mean()) < 0.15, z.mean()
    assert 0.8 <= z.std(ddof=1) <= 1.25, z.std(ddof=1)


def test_standardize_zscore_expanding_recovers_unit_moments():
    rng = np.random.default_rng(SEED + 1)
    x = rng.standard_normal(2000)
    z = np.asarray(vol.standardize(x, method="zscore"))
    z = z[np.isfinite(z)]
    assert abs(z.mean()) < 0.15, z.mean()
    assert 0.8 <= z.std(ddof=1) <= 1.25, z.std(ddof=1)


def test_standardize_rank_is_bounded_and_uniform():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(1000)
    r = np.asarray(vol.standardize(x, window=100, method="rank"))
    r = r[np.isfinite(r)]
    assert r.min() >= -1.0 and r.max() <= 1.0
    # rank of an iid draw within its own past is uniform on [-1, 1]
    assert abs(r.mean()) < 0.1, r.mean()


def test_standardize_robust_beats_zscore_on_an_outlier():
    """MAD scaling is not inflated by the outlier the way the std is."""
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(400)
    x[300] = 25.0  # one wild print
    z = np.asarray(vol.standardize(x, window=100, method="zscore"))
    rb = np.asarray(vol.standardize(x, window=100, method="robust"))
    # both flag the outlier itself, but afterwards the std stays contaminated
    tail = slice(301, 400)
    assert np.nanstd(z[tail]) < np.nanstd(rb[tail])


def test_standardize_constant_series_is_zero_not_inf():
    x = np.full(50, 7.0)
    for method in ("zscore", "robust"):
        out = np.asarray(vol.standardize(x, window=20, method=method))
        assert np.all(out[2:] == 0.0), method
        assert not np.isinf(out).any(), method


def test_standardize_clip_winsorises():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(500)
    x[400] = 40.0
    z = np.asarray(vol.standardize(x, window=100, method="zscore", clip=3.0))
    finite = z[np.isfinite(z)]
    assert finite.max() <= 3.0 + 1e-12
    assert finite.min() >= -3.0 - 1e-12
    assert z[400] == pytest.approx(3.0)


def test_standardize_rejects_unknown_method():
    with pytest.raises(ValueError):
        vol.standardize(np.arange(10.0), window=5, method="softmax")


# --------------------------------------------------------------------------
# 9. detrend
# --------------------------------------------------------------------------
def test_detrend_diff_and_logdiff():
    x = np.array([1.0, 2.0, 4.0, 8.0])
    d1 = np.asarray(vol.detrend(x, method="diff"))
    assert np.isnan(d1[0])
    np.testing.assert_allclose(d1[1:], [1.0, 2.0, 4.0])
    ld = np.asarray(vol.detrend(x, method="logdiff"))
    np.testing.assert_allclose(ld[1:], np.log(2.0))


def test_detrend_logdiff_nonpositive_is_nan_not_inf():
    x = np.array([1.0, 0.0, -2.0, 4.0])
    out = np.asarray(vol.detrend(x, method="logdiff"))
    assert not np.isinf(out).any()
    assert np.isnan(out[1]) and np.isnan(out[2]) and np.isnan(out[3])


def test_detrend_ols_kills_a_pure_linear_trend():
    x = 3.0 + 2.0 * np.arange(100, dtype=float)
    out = np.asarray(vol.detrend(x, method="ols", window=20))
    assert np.isnan(out[:2]).all()
    np.testing.assert_allclose(out[2:], 0.0, atol=1e-9)


def test_detrend_ols_expanding_is_causal_and_nontrivial():
    rng = np.random.default_rng(SEED)
    x = np.cumsum(rng.normal(0.5, 1.0, 200))
    out = np.asarray(vol.detrend(x, method="ols"))
    assert np.isnan(out[:2]).all()
    assert np.isfinite(out[2:]).all()
    assert np.abs(out[2:]).max() > 0.0


def test_detrend_rejects_unknown_method():
    with pytest.raises(ValueError):
        vol.detrend(np.arange(10.0), method="hp")


# --------------------------------------------------------------------------
# container-type contract
# --------------------------------------------------------------------------
def _series(a: np.ndarray) -> pd.Series:
    idx = pd.date_range("2024-01-01", periods=a.size, freq="B")
    return pd.Series(a, index=idx)


def test_series_in_series_out_on_the_same_index():
    d = _inputs(n=120)
    close = _series(d["close"])
    volume = _series(d["volume"])

    for out in (
        vol.obv(close, volume),
        vol.obv_slope(close, volume, window=20),
        vol.excess_volume(volume, window=20),
        vol.price_volume_divergence(close, volume, window=20),
        vol.rolling_vwap(close, volume, 20),
        vol.standardize(volume, window=20),
        vol.detrend(close, method="ols", window=20),
    ):
        assert isinstance(out, pd.Series)
        assert out.index.equals(close.index)

    flags = vol.volume_breakout(volume, window=20)
    assert isinstance(flags, pd.Series) and flags.dtype == bool

    res = vol.divergence_flag(close, volume, window=20)
    assert isinstance(res.flag, pd.Series) and isinstance(res.direction, pd.Series)
    assert res.flag.dtype == bool


def test_arrays_and_lists_come_back_as_arrays():
    close = [100.0, 101.0, 100.5, 102.0, 103.0]
    volume = [10.0, 20.0, 30.0, 40.0, 50.0]
    out = vol.obv(close, volume)
    assert isinstance(out, np.ndarray)
    # signs: 0, +1, -1, +1, +1 -> contributions 0, +20, -30, +40, +50
    np.testing.assert_allclose(out, [0.0, 20.0, -10.0, 30.0, 80.0])


def test_series_and_array_values_agree():
    d = _inputs(n=120)
    a = np.asarray(vol.excess_volume(d["volume"], window=20))
    b = vol.excess_volume(_series(d["volume"]), window=20).to_numpy()
    np.testing.assert_allclose(a, b, equal_nan=True)


def test_mismatched_pandas_indexes_raise():
    d = _inputs(n=60)
    close = _series(d["close"])
    volume = pd.Series(d["volume"], index=pd.RangeIndex(60))
    with pytest.raises(ValueError):
        vol.obv(close, volume)


def test_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        vol.obv(np.arange(10.0), np.arange(9.0))


# --------------------------------------------------------------------------
# package wiring
# --------------------------------------------------------------------------
def test_factors_package_exports_volume_names():
    pkg = importlib.import_module("strategies._common.factors")
    for name in vol.__all__:
        assert hasattr(pkg, name), name
