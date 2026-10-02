"""Tests for strategies/_common/factors/multiscale.py — synthetic data only.

Every stochastic case seeds ``np.random.default_rng`` explicitly and the
tolerances below hold for those seeds with several sigma of margin; nothing
here is allowed to be flaky.
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

ms = importlib.import_module("strategies._common.factors.multiscale")

SEED = 0
WAVELETS = ("haar", "d4")


# --------------------------------------------------------------------------
# MODWT core properties
# --------------------------------------------------------------------------
@pytest.mark.parametrize("wavelet", WAVELETS)
def test_mra_reconstruction_is_exact(wavelet):
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(256) * 3.0 + 1.5
    D, S = ms.modwt_mra(x, wavelet=wavelet, levels=4)
    assert D.shape == (4, 256)
    assert S.shape == (256,)
    assert np.allclose(D.sum(0) + S, x, atol=1e-10)


@pytest.mark.parametrize("wavelet", WAVELETS)
def test_circular_modwt_preserves_energy(wavelet):
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(256)
    W, V = ms.modwt(x, wavelet=wavelet, levels=4, mode="circular")
    total = float((W**2).sum() + (V**2).sum())
    assert total == pytest.approx(float((x**2).sum()), abs=1e-8)


@pytest.mark.parametrize("wavelet", WAVELETS)
def test_circular_modwt_is_shift_invariant(wavelet):
    """A one-bar shift of the input must shift the coefficients, not change them."""
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(128)
    W, V = ms.modwt(x, wavelet=wavelet, levels=3, mode="circular")
    Ws, Vs = ms.modwt(np.roll(x, 5), wavelet=wavelet, levels=3, mode="circular")
    assert np.allclose(Ws, np.roll(W, 5, axis=1), atol=1e-12)
    assert np.allclose(Vs, np.roll(V, 5), atol=1e-12)


def test_max_level_and_unknown_wavelet():
    assert ms.max_level(256, "haar") == 8
    with pytest.raises(ValueError):
        ms.modwt(np.zeros(64), wavelet="not-a-wavelet")
    with pytest.raises(ValueError):
        ms.modwt(np.zeros(64), mode="reflect")


def test_mra_refuses_causal_mode():
    """An additive MRA is inherently non-causal; we must not fake one."""
    with pytest.raises(ValueError, match="circular"):
        ms.modwt_mra(np.zeros(64), mode="causal")


# --------------------------------------------------------------------------
# scale_energy
# --------------------------------------------------------------------------
def test_scale_energy_of_high_frequency_signal_lives_at_level_one():
    # Nyquist-rate alternation: all the variance is at the finest scale.
    x = (-1.0) ** np.arange(512)
    e = ms.scale_energy(x, wavelet="haar", levels=4)
    assert e.size == 5
    assert e.sum() == pytest.approx(1.0, abs=1e-10)
    assert e[0] > 0.99


@pytest.mark.parametrize("wavelet", WAVELETS)
def test_scale_energy_of_slow_ramp_lives_in_the_smooth(wavelet):
    x = np.linspace(0.0, 1.0, 512)
    e = ms.scale_energy(x, wavelet=wavelet, levels=4)
    assert e.sum() == pytest.approx(1.0, abs=1e-10)
    assert e[-1] > 0.9  # the smooth, not any detail level
    assert e[:-1].max() < 0.1


# --------------------------------------------------------------------------
# cross_scale_resonance
# --------------------------------------------------------------------------
def test_resonance_is_plus_one_on_a_monotone_ramp():
    x = np.linspace(0.0, 1.0, 512)
    r = ms.cross_scale_resonance(x, scales=(1, 2, 3))
    valid = ~np.isnan(r)
    assert valid.sum() > 400
    assert np.allclose(r[valid], 1.0, atol=1e-12)
    # warm-up is (2^3 - 1) * (L-1) = 7 samples for haar
    assert np.isnan(r[:7]).all()


def test_resonance_is_near_zero_on_white_noise():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(4000)
    r = ms.cross_scale_resonance(x, scales=(1, 2, 3))
    assert abs(float(np.nanmean(r))) < 0.05
    assert np.nanmax(r) <= 1.0 + 1e-12
    assert np.nanmin(r) >= -1.0 - 1e-12


def test_resonance_rejects_bad_arguments():
    x = np.linspace(0.0, 1.0, 64)
    with pytest.raises(ValueError):
        ms.cross_scale_resonance(x, scales=())
    with pytest.raises(ValueError):
        ms.cross_scale_resonance(x, scales=(0, 1))
    with pytest.raises(ValueError):
        ms.cross_scale_resonance(x, scales=(1, 2), weights=(1.0,))


# --------------------------------------------------------------------------
# Causality
# --------------------------------------------------------------------------
def test_no_lookahead_modwt_causal():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(300)
    full, full_v = ms.modwt(x, levels=3, mode="causal")
    for cut in (150, 200, 250):
        trunc, trunc_v = ms.modwt(x[:cut], levels=3, mode="causal")
        assert np.allclose(trunc[:, -1], full[:, cut - 1], equal_nan=True)
        assert np.allclose(trunc_v[-1], full_v[cut - 1], equal_nan=True)


def test_no_lookahead_cross_scale_resonance():
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(300)
    full = ms.cross_scale_resonance(x, scales=(1, 2, 3))
    for cut in (150, 200, 250):
        trunc = ms.cross_scale_resonance(x[:cut], scales=(1, 2, 3))
        assert np.allclose(trunc[-1], full[cut - 1], equal_nan=True)


def test_circular_modwt_really_does_look_ahead():
    """Guard the guard: prove the non-causal mode is genuinely non-causal.

    The circular boundary's leak is concentrated at the *start* of the sample
    (that is where the filter support wraps around to the end), so the way to
    expose it is to perturb the last observation and watch the first
    coefficients move. If this ever stops failing, the causal tests above have
    stopped testing anything.
    """
    rng = np.random.default_rng(SEED)
    x = rng.standard_normal(300)
    y = x.copy()
    y[-1] += 10.0  # perturb the future only

    circ, _ = ms.modwt(x, levels=3, mode="circular")
    circ_y, _ = ms.modwt(y, levels=3, mode="circular")
    assert not np.allclose(circ[:, :7], circ_y[:, :7])

    causal, _ = ms.modwt(x, levels=3, mode="causal")
    causal_y, _ = ms.modwt(y, levels=3, mode="causal")
    assert np.allclose(causal[:, :-1], causal_y[:, :-1], equal_nan=True)

    r = ms.cross_scale_resonance(x, scales=(1, 2, 3))
    r_y = ms.cross_scale_resonance(y, scales=(1, 2, 3))
    assert np.allclose(r[:-1], r_y[:-1], equal_nan=True)


def test_signal_entry_points_are_the_causal_ones():
    """The exported signal generator must be built on the causal transform."""
    assert "modwt_mra" in ms.NONCAUSAL
    assert "modwt(mode='circular')" in ms.NONCAUSAL
    assert "scale_energy" in ms.NONCAUSAL
    assert "cross_scale_resonance" in ms.CAUSAL
    assert "cross_scale_resonance" not in ms.NONCAUSAL

    # ...and prove it, rather than trusting the constant: with flat weights the
    # resonance must equal the mean sign of the *causal* details.
    rng = np.random.default_rng(SEED)
    x = np.cumsum(rng.standard_normal(400))
    r = ms.cross_scale_resonance(x, scales=(1, 2, 3), weights=(1.0, 1.0, 1.0))
    w_causal, _ = ms.modwt(x, levels=3, mode="causal")
    expected = np.sign(w_causal).mean(axis=0)
    valid = ~np.isnan(r)
    assert np.allclose(r[valid], expected[valid], atol=1e-12)

    # The circular transform would have handed back a finite (but
    # future-contaminated) value throughout the warm-up; the causal one refuses.
    w_circ, _ = ms.modwt(x, levels=3, mode="circular")
    assert np.isfinite(w_circ[:, :7]).all()
    assert np.isnan(w_causal[:, :7]).any(axis=0).all()
    assert np.isnan(r[:7]).all()


# --------------------------------------------------------------------------
# mtf_align
# --------------------------------------------------------------------------
def _weekly_fixture():
    # Monday-labelled weekly bars: bar k covers [label_k, label_{k+1}).
    weeks = pd.date_range("2020-01-06", periods=6, freq="W-MON")
    weekly = pd.DataFrame({"close": np.arange(1.0, 7.0)}, index=weeks)
    target = pd.date_range("2020-01-06", periods=45, freq="D")
    return weekly, weeks, target


@pytest.mark.parametrize(
    "label,lag_bars", [("open", 0), ("close", 1)]
)
def test_mtf_align_hides_a_week_until_it_closes(label, lag_bars):
    """A value dated inside week k must be invisible before week k's close."""
    weekly, weeks, target = _weekly_fixture()
    aligned = ms.mtf_align({"W": weekly}, target, label=label, lag_bars=lag_bars)
    assert list(aligned.columns) == ["W_close"]
    assert aligned.index.equals(target)

    col = aligned["W_close"]
    for k in range(len(weeks) - 1):
        value = weekly["close"].iloc[k]
        close_ts = weeks[k + 1]  # the instant week k is complete
        before = col[target < close_ts]
        assert not (before == value).any(), (
            f"week {k} value {value} leaked before its close {close_ts}"
        )
        # ...and it *is* visible from the close onwards (until superseded).
        assert col[target >= close_ts].iloc[0] == value


def test_mtf_align_lag_bars_adds_exactly_one_more_bar():
    weekly, weeks, target = _weekly_fixture()
    fast = ms.mtf_align({"W": weekly}, target, label="open", lag_bars=0)["W_close"]
    slow = ms.mtf_align({"W": weekly}, target, label="open", lag_bars=1)["W_close"]
    # slow is fast delayed by one whole coarse bar
    first_close = weeks[1]
    assert np.isnan(slow[target < weeks[2]]).all()
    assert fast[target >= first_close].iloc[0] == 1.0
    assert slow[target >= weeks[2]].iloc[0] == 1.0


def test_mtf_align_multiple_frames_and_series():
    weekly, _weeks, target = _weekly_fixture()
    daily = pd.Series(
        np.arange(float(len(target))), index=target, name="ignored"
    )
    out = ms.mtf_align(
        {"W": weekly, "D": daily}, target, label="close", lag_bars=1
    )
    assert list(out.columns) == ["W_close", "D_D"]
    # daily shifted by one of its own bars -> yesterday's value, never today's
    assert np.isnan(out["D_D"].iloc[0])
    assert out["D_D"].iloc[5] == 4.0


def test_mtf_align_rejects_bad_arguments():
    weekly, _weeks, target = _weekly_fixture()
    with pytest.raises(ValueError):
        ms.mtf_align({"W": weekly}, target, label="middle")
    with pytest.raises(ValueError):
        ms.mtf_align({"W": weekly}, target, lag_bars=-1)
    with pytest.raises(TypeError):
        ms.mtf_align({"W": weekly.reset_index(drop=True)}, target)


# --------------------------------------------------------------------------
# conditional_lift
# --------------------------------------------------------------------------
def _lift_sample(seed: int, n: int, p_win_cond: float, p_win_not: float):
    rng = np.random.default_rng(seed)
    signal = rng.random(n) < 0.5
    condition = rng.random(n) < 0.25
    win_p = np.where(condition, p_win_cond, p_win_not)
    fwd = np.where(rng.random(n) < win_p, 1.0, -1.0)
    return signal, condition, fwd


def test_conditional_lift_detects_a_real_doubling():
    # P(win|cond)=0.6, P(win|~cond)=0.2, P(cond)=0.25
    #   -> p_uncond = 0.25*0.6 + 0.75*0.2 = 0.30, so the true lift is exactly 2.
    signal, condition, fwd = _lift_sample(11, 6000, 0.6, 0.2)
    res = ms.conditional_lift(signal, condition, fwd)
    assert res["lift"] == pytest.approx(2.0, abs=0.25)
    assert res["p_cond"] == pytest.approx(0.6, abs=0.05)
    assert res["p_uncond"] == pytest.approx(0.3, abs=0.05)
    assert res["p_value"] < 0.05
    assert res["n_cond"] > 600
    assert res["ci_cond"][0] < res["p_cond"] < res["ci_cond"][1]
    assert res["power_warning"] is False


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4, 5])
def test_conditional_lift_on_an_independent_condition(seed):
    # The condition carries no information: same win rate either way.
    signal, condition, fwd = _lift_sample(seed, 6000, 0.4, 0.4)
    res = ms.conditional_lift(signal, condition, fwd)
    assert res["lift"] == pytest.approx(1.0, abs=0.15)
    assert res["p_value"] > 0.05
    # "the filter does nothing" is still a comfortable explanation -> warn
    assert res["power_warning"] is True
    assert res["ci_cond"][0] <= res["p_uncond"] <= res["ci_cond"][1]


def test_conditional_lift_warns_when_the_filter_starves_the_sample():
    """The headline point: high lift on a tiny sample is not evidence."""
    n = 400
    rng = np.random.default_rng(3)
    signal = np.ones(n, dtype=bool)
    condition = np.zeros(n, dtype=bool)
    condition[:12] = True  # only 12 conditioned observations
    fwd = np.where(rng.random(n) < 0.4, 1.0, -1.0)
    fwd[:12] = 1.0  # a perfect 12-for-12 record
    res = ms.conditional_lift(signal, condition, fwd)
    assert res["n_cond"] == 12
    assert res["p_cond"] == 1.0
    assert res["lift"] > 2.0
    assert res["power_warning"] is True


def test_conditional_lift_drops_nan_forward_returns_and_handles_empties():
    fwd = np.array([1.0, -1.0, np.nan, 2.0])
    signal = np.array([True, True, True, False])
    condition = np.array([True, False, True, True])
    res = ms.conditional_lift(signal, condition, fwd)
    assert res["n_signal"] == 2  # the NaN row is dropped
    assert res["n_cond"] == 1
    assert res["p_cond"] == 1.0

    empty = ms.conditional_lift(
        np.zeros(4, dtype=bool), np.zeros(4, dtype=bool), fwd
    )
    assert empty["n_signal"] == 0
    assert np.isnan(empty["p_cond"])
    assert empty["power_warning"] is True

    with pytest.raises(ValueError):
        ms.conditional_lift(signal[:2], condition, fwd)
