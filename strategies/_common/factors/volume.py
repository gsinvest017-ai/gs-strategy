"""Price-volume factor library — classic volume technical analysis, made testable.

Every factor here is a *strictly causal* map from a time series to a time series:
the value at index ``t`` depends only on inputs at indices ``<= t``, and every
normaliser (mean/std/median/rank) is fitted on the window ending at ``t-1``.
Including ``t`` in its own normaliser is the single most common leak in a
volume-factor pipeline: it shrinks the statistic exactly on the bars you care
about (a spike partly normalises itself away), so it is forbidden here.

Design rule (mirrors ``strategies/_common/validation``): this module consumes
only price/volume arrays, imports nothing from zipline or the rest of
gs-strategy, and is therefore lift-ready into ``gs_common.quant.factors``.

Inputs may be 1-D numpy arrays, pandas Series (typically DatetimeIndex), or
plain sequences. The return type follows the *first pandas Series among the
inputs* — if you pass Series you get a Series back on the same index; if you
pass arrays/lists you get a numpy array back.

Performance note: ``standardize`` and ``detrend(method='ols')`` are written as
an explicit per-bar loop over the causal comparison sample. That is O(n*window)
(O(n^2) for the expanding case) rather than a vectorised rolling kernel. The
choice is deliberate: at daily research scale the cost is irrelevant and the
loop makes the "sample ends at t-1" invariant visually checkable, which is the
property that actually breaks backtests.
"""
from __future__ import annotations

import warnings
from typing import NamedTuple, Sequence, Union

import numpy as np
import pandas as pd

try:
    from scipy.stats import rankdata  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required for factors.volume: pip install scipy"
    ) from exc


SeriesLike = Union[np.ndarray, "pd.Series", Sequence[float]]

# Every public factor in this module is strictly causal and safe for signal
# generation. Nothing is listed here. If a deliberately non-causal (centred /
# full-sample) diagnostic is ever added, its name MUST be appended here and its
# docstring must say loudly that it may not be used to generate trading signals.
NONCAUSAL_FUNCTIONS: tuple[str, ...] = ()

# Relative tolerance used to decide that a dispersion estimate is degenerate
# (a constant window). Absolute zero is not usable: the sample std of N
# identical doubles is ~1e-16, not 0.0, because the mean carries a rounding
# error. See ``_safe_ratio``.
_EPS = 1e-12

__all__ = [
    "NONCAUSAL_FUNCTIONS",
    "DivergenceFlags",
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
]


# --------------------------------------------------------------------------
# plumbing: type preservation, causal windows, degenerate-denominator policy
# --------------------------------------------------------------------------
def _to_array(x: SeriesLike, name: str = "x") -> np.ndarray:
    """Coerce a Series/array/sequence to a 1-D float ndarray (no copy of index)."""
    if isinstance(x, pd.Series):
        a = x.to_numpy(dtype=float)
    else:
        a = np.asarray(x, dtype=float)
    if a.ndim != 1:
        raise ValueError(f"{name} must be 1-D, got shape {a.shape}")
    return a


def _template(*inputs: SeriesLike) -> "pd.Series | None":
    """Return the first pandas Series among ``inputs`` (the output template).

    Raises if two Series arguments carry different indexes: silently aligning
    them (or silently picking one) is how a factor ends up quietly shifted
    relative to its own inputs.
    """
    found: "pd.Series | None" = None
    for obj in inputs:
        if isinstance(obj, pd.Series):
            if found is None:
                found = obj
            elif not found.index.equals(obj.index):
                raise ValueError(
                    "pandas inputs must share an index; align them before "
                    "calling this factor"
                )
    return found


def _like(template: "pd.Series | None", values: np.ndarray, name: str | None = None):
    """Wrap ``values`` back into the caller's container type."""
    if template is None:
        return values
    return pd.Series(values, index=template.index, name=name)


def _check_same_length(**arrays: np.ndarray) -> int:
    sizes = {k: v.size for k, v in arrays.items()}
    if len(set(sizes.values())) > 1:
        raise ValueError(f"inputs must have equal length, got {sizes}")
    return next(iter(sizes.values()))


def _trailing_matrix(x: np.ndarray, window: int, lag: int = 0) -> np.ndarray:
    """Row ``t`` = the ``window`` values of ``x`` ending at index ``t - lag``.

    NaN-padded at the front, so row ``t`` is always length ``window`` and the
    warm-up rows are partly NaN. With ``lag=0`` the row includes ``x[t]``
    (legitimate for a window statistic *of* the series); with ``lag=1`` it
    stops at ``x[t-1]`` (required for anything used to normalise ``x[t]``).
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    if lag < 0:
        raise ValueError("lag must be >= 0")
    n = x.size
    if n == 0:
        return np.empty((0, window), dtype=float)
    padded = np.concatenate([np.full(window + lag - 1, np.nan), x])
    mat = np.lib.stride_tricks.sliding_window_view(padded, window)
    return mat[:n]


def _nan_rows(mat: np.ndarray, reducer) -> np.ndarray:
    """Apply a nan-aware row reducer, silencing the all-NaN-slice warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return reducer(mat, axis=1)


def _safe_ratio(num: float, disp: float, scale: float) -> float:
    """``num / disp`` with an explicit degenerate-denominator policy.

    A window with (numerically) zero dispersion is not an infinite z-score, it
    is an undefined one. Policy: if ``disp`` is at or below ``_EPS * scale``
    then return 0.0 when the numerator is also at or below that tolerance
    (a genuinely constant series is 0 standard deviations from its own mean),
    and NaN otherwise. Never +/-inf.

    The side effect — and it is a real one — is that a series with a true but
    astronomically small variance is reported as 0 rather than as a huge
    z-score. That is the intended trade: infinities poison downstream
    aggregation silently, zeros do not.
    """
    tol = _EPS * scale
    if not np.isfinite(disp) or disp <= tol:
        return 0.0 if abs(num) <= tol else np.nan
    return num / disp


def _row_pearson(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Row-wise Pearson correlation of two (n, window) matrices, in [-1, 1]."""
    a0 = a - a.mean(axis=1, keepdims=True)
    b0 = b - b.mean(axis=1, keepdims=True)
    num = (a0 * b0).sum(axis=1)
    den = np.sqrt((a0**2).sum(axis=1) * (b0**2).sum(axis=1))
    out = np.full(a.shape[0], np.nan)
    ok = np.isfinite(den) & (den > 0)
    out[ok] = num[ok] / den[ok]
    return np.clip(out, -1.0, 1.0)


def _rolling_ols_slope(mat: np.ndarray) -> np.ndarray:
    """OLS slope of each row against 0, 1, ..., window-1.

    slope = sum_i (i - ibar) * (y_i - ybar) / sum_i (i - ibar)^2. Rows that
    contain any non-finite value yield NaN (no partial-window fitting: a
    volume series with holes should be cleaned, not quietly interpolated).
    """
    window = mat.shape[1]
    if window < 2:
        raise ValueError("window must be >= 2 to fit a slope")
    t = np.arange(window, dtype=float)
    tc = t - t.mean()
    denom = float((tc**2).sum())
    full = np.isfinite(mat).all(axis=1)
    out = np.full(mat.shape[0], np.nan)
    if full.any():
        rows = mat[full]
        out[full] = ((rows - rows.mean(axis=1, keepdims=True)) @ tc) / denom
    return out


# --------------------------------------------------------------------------
# 1-2. On-Balance Volume and its trend
# --------------------------------------------------------------------------
def _obv_array(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    d = np.diff(close, prepend=close[0] if close.size else np.nan)
    return np.cumsum(np.sign(d) * volume)


def obv(close: SeriesLike, volume: SeriesLike):
    """On-Balance Volume (Granville 1963).

    OBV_t = sum_{s<=t} sign(close_s - close_{s-1}) * volume_s, with
    ``sign(0) = 0`` and the undefined first difference treated as 0, so
    ``OBV_0 = 0`` always.

    Read it as a *signed-volume partial sum*. Under the null that volume
    carries no directional information — signs iid and independent of volume —
    OBV is a driftless random walk. That framing is what makes OBV testable at
    all: any claim about OBV is a claim that its increments are not sign-iid,
    and it is the reason the derived factors below are trend/correlation
    statistics on OBV rather than OBV levels (a random-walk level has no
    meaningful scale and is not comparable across instruments or epochs).

    NaN policy: OBV is a cumulative sum, so a NaN in ``close`` or ``volume``
    propagates to every later value. That is deliberate — the alternative
    (treating a missing bar as a zero increment) fabricates data.
    """
    tpl = _template(close, volume)
    c = _to_array(close, "close")
    v = _to_array(volume, "volume")
    _check_same_length(close=c, volume=v)
    return _like(tpl, _obv_array(c, v), name="obv")


def obv_slope(close: SeriesLike, volume: SeriesLike, window: int = 20):
    """Trailing OLS slope of OBV, normalised by trailing mean volume.

    slope_t = OLS slope of (OBV_{t-window+1}, ..., OBV_t) against 0..window-1,
    then factor_t = slope_t / mean(volume_{t-window+1..t}).

    The normalisation is what makes this comparable across instruments and
    across time: the raw slope is in shares (or contracts) per bar, so a
    large-cap and a small-cap are on incomparable scales and the same name is
    incomparable with itself after a volume regime shift. Dividing by the
    contemporaneous mean volume gives a dimensionless number: "OBV accumulates
    this fraction of a typical bar's volume per bar". It equals exactly +1 when
    every bar in the window is an up bar of constant volume (-1 for the
    mirror), and in practice sits well inside [-1, +1] — but it is NOT bounded
    there: a window whose volume itself trends steeply can push |factor| above
    1, because the OLS slope weights late bars more heavily than the flat mean
    in the denominator does.

    Causal: the window ends at ``t`` and contains no future bars. Returns NaN
    for the first ``window - 1`` bars, for any window containing a non-finite
    value, and where trailing mean volume is not strictly positive.
    """
    tpl = _template(close, volume)
    c = _to_array(close, "close")
    v = _to_array(volume, "volume")
    _check_same_length(close=c, volume=v)
    window = int(window)
    if window < 2:
        raise ValueError("window must be >= 2")
    o = _obv_array(c, v)
    slope = _rolling_ols_slope(_trailing_matrix(o, window, lag=0))
    vbar = _nan_rows(_trailing_matrix(v, window, lag=0), np.nanmean)
    out = np.full(c.size, np.nan)
    ok = np.isfinite(slope) & np.isfinite(vbar) & (vbar > 0)
    out[ok] = slope[ok] / vbar[ok]
    return _like(tpl, out, name="obv_slope")


# --------------------------------------------------------------------------
# 3-4. Excess (abnormal) volume and volume breakouts
# --------------------------------------------------------------------------
def excess_volume(
    volume: SeriesLike,
    window: int = 20,
    log: bool = True,
    min_periods: int | None = None,
):
    """Abnormal trading volume as a strictly-lagged z-score.

    v_t = log(1 + V_t) if ``log`` else V_t, and

        Excess_t = (v_t - mu_{t-1}) / sigma_{t-1}

    where mu and sigma are the mean and sample std (ddof=1) over the ``window``
    observations ENDING AT t-1 — index ``t`` is excluded from its own
    normaliser. That exclusion is the whole point of the statistic. If ``t`` is
    inside the window, a spike inflates both the mean and the std it is being
    measured against, so the statistic shrinks toward zero — and it shrinks
    most for exactly the observations the factor was built to detect. (With
    ``t`` inside a window of length W the z-score is in fact algebraically
    capped at (W-1)/sqrt(W) — Samuelson's inequality, ~4.25 for W=20 — no
    matter how large the spike; excluding ``t`` removes that ceiling entirely.)

    The log transform (default) follows the abnormal-volume literature
    (Ajinkya & Jain 1989, *J. Accounting and Economics*): raw share volume is
    strongly right-skewed, and log volume is far closer to normal, which is
    what makes a z-score interpretable in sigma units at all. ``log1p`` is used
    rather than ``log`` so that zero-volume bars are 0 instead of -inf.

    There is no single canonical definition of "abnormal volume" in the
    literature — window length, log vs. raw, and mean vs. median centring all
    vary by author. This is one defensible operationalisation, not *the* one.

    ``min_periods`` defaults to ``window`` (a full trailing window required);
    lower it to trade warm-up length for a noisier normaliser. Constant-volume
    windows give exactly 0.0, never inf — see ``_safe_ratio``.
    """
    tpl = _template(volume)
    v = _to_array(volume, "volume")
    window = int(window)
    if window < 2:
        raise ValueError("window must be >= 2")
    mp = window if min_periods is None else int(min_periods)
    if mp < 2:
        raise ValueError("min_periods must be >= 2 (a std needs two points)")
    if log:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            v = np.log1p(v)
        v = np.where(np.isfinite(v), v, np.nan)
    out = _standardize_core(v, window=window, method="zscore", min_periods=mp)
    return _like(tpl, out, name="excess_volume")


def volume_breakout(
    volume: SeriesLike,
    window: int = 20,
    k: float = 2.0,
    log: bool = True,
    min_periods: int | None = None,
):
    """Boolean volume-breakout flag: ``excess_volume(...) > k``.

    ``k`` is in units of the trailing standard deviation of (log) volume, so
    ``k=2`` is "roughly the 97.7th percentile of the trailing distribution if
    log volume were normal" — the normality caveat is real and the empirical
    tail is fatter than that, which is why the default is deliberately
    unambitious.

    Warm-up bars and undefined z-scores are False, not NaN: this returns a
    boolean mask meant to be used directly as a selector, and a three-valued
    mask is a bug factory. If you need to distinguish "no breakout" from "not
    yet computable", use ``excess_volume`` and test for NaN yourself.
    """
    tpl = _template(volume)
    ex = _to_array(
        excess_volume(volume, window=window, log=log, min_periods=min_periods)
    )
    flag = np.isfinite(ex) & (ex > float(k))
    return _like(tpl, flag, name="volume_breakout")


# --------------------------------------------------------------------------
# 5. Price-volume divergence
# --------------------------------------------------------------------------
class DivergenceFlags(NamedTuple):
    """Result of :func:`divergence_flag`: ``flag`` (bool) and ``direction``."""

    flag: SeriesLike
    direction: SeriesLike


def price_volume_divergence(
    close: SeriesLike,
    volume: SeriesLike,
    window: int = 20,
    method: str = "spearman",
):
    """Trailing rank correlation between the price path and the OBV path.

    Over the ``window`` bars ending at ``t`` (inclusive — this is a statistic
    *of* the window, not a normaliser of ``t``), compute

        rho_t = corr(rank(close_{t-window+1..t}), rank(OBV_{t-window+1..t}))

    with ``method='spearman'`` (average ranks, Spearman 1904) or the plain
    Pearson correlation of the levels with ``method='pearson'``. Returned in
    [-1, 1]; NaN during warm-up, on windows containing non-finite values, and
    on degenerate windows (a flat price or flat OBV path has no rank variance,
    so the correlation is undefined rather than zero).

    rho near +1 means volume confirms the price path; rho at or below zero is
    the classic "divergence" of technical analysis. Note this is a *path*
    correlation over a window, not a correlation of increments: it answers
    "did OBV go where price went", which is the question the chartists'
    divergence is actually about.
    """
    tpl = _template(close, volume)
    c = _to_array(close, "close")
    v = _to_array(volume, "volume")
    _check_same_length(close=c, volume=v)
    window = int(window)
    if window < 3:
        raise ValueError("window must be >= 3 for a meaningful rank correlation")
    if method not in ("spearman", "pearson"):
        raise ValueError("method must be 'spearman' or 'pearson'")

    o = _obv_array(c, v)
    mp = _trailing_matrix(c, window, lag=0)
    mo = _trailing_matrix(o, window, lag=0)
    good = np.isfinite(mp).all(axis=1) & np.isfinite(mo).all(axis=1)

    out = np.full(c.size, np.nan)
    if good.any():
        a = mp[good]
        b = mo[good]
        if method == "spearman":
            a = rankdata(a, axis=1)
            b = rankdata(b, axis=1)
        out[good] = _row_pearson(a, b)
    return _like(tpl, out, name=f"pv_divergence_{method}")


def divergence_flag(
    close: SeriesLike,
    volume: SeriesLike,
    window: int = 20,
    corr_threshold: float = 0.0,
    method: str = "spearman",
) -> DivergenceFlags:
    """Unconfirmed-price-move flag, with a signed direction.

    Over the trailing ``window`` ending at ``t``:

      * ``direction = -1`` (bearish divergence) when the OLS slope of price is
        > 0 but ``price_volume_divergence < corr_threshold`` — price makes
        progress that OBV does not confirm.
      * ``direction = +1`` (bullish divergence) is the mirror image: the price
        slope is < 0 while the correlation is still below the threshold, i.e.
        price falls but OBV does not fall with it (accumulation into weakness).
      * ``direction = 0`` otherwise, including every warm-up / undefined bar.

    ``flag`` is simply ``direction != 0``.

    Honest caveat: "divergence" is a chart-reading heuristic (Granville 1963;
    Murphy 1999) with no agreed formal definition — practitioners eyeball
    swing highs, not window correlations. The slope-plus-rank-correlation rule
    above is *an* operationalisation chosen because it is unambiguous, causal
    and testable. Do not treat agreement with a chartist's annotation as a
    correctness criterion for it.
    """
    tpl = _template(close, volume)
    c = _to_array(close, "close")
    v = _to_array(volume, "volume")
    _check_same_length(close=c, volume=v)
    window = int(window)

    corr = _to_array(
        price_volume_divergence(c, v, window=window, method=method)
    )
    slope = _rolling_ols_slope(_trailing_matrix(c, window, lag=0))

    ok = np.isfinite(corr) & np.isfinite(slope)
    unconfirmed = ok & (corr < float(corr_threshold))
    direction = np.zeros(c.size, dtype=float)
    direction[unconfirmed & (slope > 0)] = -1.0
    direction[unconfirmed & (slope < 0)] = 1.0
    flag = direction != 0.0
    return DivergenceFlags(
        flag=_like(tpl, flag, name="divergence_flag"),
        direction=_like(tpl, direction, name="divergence_direction"),
    )


# --------------------------------------------------------------------------
# 6. Price benchmarks: typical price, VWAP, TWAP
# --------------------------------------------------------------------------
def typical_price(high: SeriesLike, low: SeriesLike, close: SeriesLike):
    """Typical price, TP_t = (H_t + L_t + C_t) / 3.

    The standard input to Money Flow Index / CCI (Lambert 1980). Purely
    contemporaneous, hence trivially causal.
    """
    tpl = _template(high, low, close)
    h = _to_array(high, "high")
    lo = _to_array(low, "low")
    c = _to_array(close, "close")
    _check_same_length(high=h, low=lo, close=c)
    return _like(tpl, (h + lo + c) / 3.0, name="typical_price")


def rolling_vwap(price: SeriesLike, volume: SeriesLike, window: int):
    """Trailing volume-weighted average price over ``window`` bars.

    VWAP_t = sum_{s=t-window+1}^{t} p_s v_s / sum_{s=t-window+1}^{t} v_s
    (Berkowitz, Logue & Noser 1988, who introduced VWAP as an execution
    benchmark). Causal: the window ends at ``t``.

    NaN for the first ``window - 1`` bars and wherever the window's total
    volume is not strictly positive. Bars where either input is non-finite are
    dropped from both sums, so the weights stay consistent.

    Accuracy caveat: a VWAP computed from daily bars weights one price per day
    and is therefore an approximation of the true intraday VWAP. Feed it
    intraday bars (or ``typical_price`` of them) if you need the real thing.
    """
    tpl = _template(price, volume)
    p = _to_array(price, "price")
    v = _to_array(volume, "volume")
    _check_same_length(price=p, volume=v)
    window = int(window)
    if window < 1:
        raise ValueError("window must be >= 1")

    valid = np.isfinite(p) & np.isfinite(v)
    pv = np.where(valid, p * v, 0.0)
    vv = np.where(valid, v, 0.0)
    num = _trailing_matrix(pv, window, lag=0)
    den = _trailing_matrix(vv, window, lag=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        num_s = np.nansum(num, axis=1)
        den_s = np.nansum(den, axis=1)
    out = np.full(p.size, np.nan)
    ok = np.isfinite(den_s) & (den_s > 0)
    out[ok] = num_s[ok] / den_s[ok]
    out[: window - 1] = np.nan  # warm-up: not a full window yet
    return _like(tpl, out, name="rolling_vwap")


def vwap_deviation(close: SeriesLike, vwap: SeriesLike):
    """Relative distance of price from VWAP: close_t / vwap_t - 1.

    A dimensionless "how far above/below the volume-weighted fair value are we"
    measure. NaN (never inf) where VWAP is non-positive or undefined.
    """
    tpl = _template(close, vwap)
    c = _to_array(close, "close")
    w = _to_array(vwap, "vwap")
    _check_same_length(close=c, vwap=w)
    out = np.full(c.size, np.nan)
    ok = np.isfinite(c) & np.isfinite(w) & (w > 0)
    out[ok] = c[ok] / w[ok] - 1.0
    return _like(tpl, out, name="vwap_deviation")


def twap(
    open_: SeriesLike, high: SeriesLike, low: SeriesLike, close: SeriesLike
):
    """OHLC average, (O + H + L + C) / 4, used as a daily TWAP *proxy*.

    This is an APPROXIMATION, not a TWAP. The true time-weighted average price
    is the average of prices sampled on an even time grid within the bar, which
    requires intraday data. The OHLC average instead weights four order
    statistics of the session equally, over-weighting the extremes (H and L are
    each a single instant, yet get 25% each) and ignoring how long price spent
    anywhere. On a trending day it is biased toward the midpoint of the range
    and away from the time-weighted mean.

    Use it as a smoother, low-noise stand-in for "the day's price" when only
    daily OHLC is available; do not report it as a TWAP execution benchmark.
    """
    tpl = _template(open_, high, low, close)
    o = _to_array(open_, "open_")
    h = _to_array(high, "high")
    lo = _to_array(low, "low")
    c = _to_array(close, "close")
    _check_same_length(open_=o, high=h, low=lo, close=c)
    return _like(tpl, (o + h + lo + c) / 4.0, name="twap_proxy")


# --------------------------------------------------------------------------
# 7. Amihud illiquidity
# --------------------------------------------------------------------------
def amihud_illiquidity(
    returns: SeriesLike, dollar_volume: SeriesLike, window: int = 20
):
    """Amihud (2002) illiquidity: trailing mean of |return| per unit of turnover.

    ILLIQ_t = (1 / W) * sum_{s=t-W+1}^{t} |r_s| / DVOL_s

    i.e. the average absolute price response per dollar (or per TWD) traded —
    Amihud's "price impact" proxy (Amihud 2002, *Journal of Financial Markets*,
    "Illiquidity and stock returns: cross-section and time-series effects").

    Two deviations from the original paper, both deliberate:
      * Amihud averages over a *year* of daily observations; here the window is
        a parameter and defaults to 20 bars, which is noisier but usable as a
        time-varying factor.
      * No 1e6 (or any other) scaling constant is applied. The level therefore
        depends on the currency unit of ``dollar_volume``; it is only
        comparable across instruments quoted in the same unit.

    Bars with non-positive or non-finite ``dollar_volume`` contribute NaN and
    are skipped by the average — never +inf, which would poison every window
    it touches and every cross-sectional aggregate downstream. A window with
    no usable bar at all is NaN. The first ``window - 1`` bars are NaN.
    """
    tpl = _template(returns, dollar_volume)
    r = _to_array(returns, "returns")
    dv = _to_array(dollar_volume, "dollar_volume")
    _check_same_length(returns=r, dollar_volume=dv)
    window = int(window)
    if window < 1:
        raise ValueError("window must be >= 1")

    ratio = np.full(r.size, np.nan)
    ok = np.isfinite(r) & np.isfinite(dv) & (dv > 0)
    ratio[ok] = np.abs(r[ok]) / dv[ok]

    mat = _trailing_matrix(ratio, window, lag=0)
    out = _nan_rows(mat, np.nanmean)
    out[: window - 1] = np.nan  # warm-up: not a full window yet
    return _like(tpl, out, name="amihud_illiquidity")


# --------------------------------------------------------------------------
# 8-9. The quant SOP: detrend -> standardise
# --------------------------------------------------------------------------
def _standardize_core(
    x: np.ndarray,
    window: int | None,
    method: str,
    min_periods: int,
) -> np.ndarray:
    """Per-bar standardisation against the causal sample ``x[t-window : t]``.

    The comparison sample ALWAYS ends at ``t-1``; ``x[t]`` never participates
    in its own location/scale estimate. ``window=None`` means expanding
    (``x[0:t]``).
    """
    if method not in ("zscore", "rank", "robust"):
        raise ValueError("method must be one of 'zscore', 'rank', 'robust'")
    n = x.size
    out = np.full(n, np.nan)
    for t in range(n):
        xt = x[t]
        if not np.isfinite(xt):
            continue
        lo = 0 if window is None else max(0, t - window)
        s = x[lo:t]
        s = s[np.isfinite(s)]
        if s.size < min_periods:
            continue
        if method == "rank":
            # fraction of the trailing sample strictly below x_t, ties at half
            # weight, mapped from [0, 1] to [-1, 1].
            below = int(np.count_nonzero(s < xt))
            equal = int(np.count_nonzero(s == xt))
            out[t] = 2.0 * ((below + 0.5 * equal) / s.size) - 1.0
        elif method == "zscore":
            center = float(s.mean())
            disp = float(s.std(ddof=1))
            out[t] = _safe_ratio(xt - center, disp, max(abs(center), 1.0))
        else:  # robust
            center = float(np.median(s))
            # 1.4826 makes MAD a consistent estimator of sigma for Gaussian
            # data (Hampel 1974; Rousseeuw & Croux 1993).
            disp = 1.4826 * float(np.median(np.abs(s - center)))
            out[t] = _safe_ratio(xt - center, disp, max(abs(center), 1.0))
    return out


def standardize(
    x: SeriesLike,
    window: int | None = None,
    method: str = "zscore",
    clip: float | None = None,
    min_periods: int = 2,
):
    """Causal standardisation of a factor — the "z-score it" step of the SOP.

    Methods (mu/sigma/median/rank are all estimated on the sample ENDING AT
    ``t-1``; ``window=None`` uses an expanding sample ``x[0:t]``):

      * ``'zscore'``  : (x_t - mean_{t-1}) / std_{t-1}, std with ddof=1.
      * ``'rank'``    : time-series (not cross-sectional) rank of x_t inside
        the trailing sample, mapped to [-1, 1] as
        ``2 * (#{s < x_t} + 0.5 * #{s == x_t}) / N - 1``. Bounded and
        outlier-proof by construction, at the cost of discarding magnitude.
      * ``'robust'``  : (x_t - median_{t-1}) / (1.4826 * MAD_{t-1}).

    Why the sample must end at ``t-1``: a normaliser that sees ``x_t`` leaks
    information about ``x_t`` into its own scaling. For the z-score the effect
    is mechanical shrinkage of exactly the extreme values the factor exists to
    surface; for the rank it is worse, because ``x_t``'s own presence bounds
    its rank away from the extremes. It is a small leak per bar and it survives
    every backtest you run, which is what makes it dangerous.

    ``clip`` winsorises the OUTPUT to +/- clip (applied after standardisation,
    so NaN stays NaN). Note this clips, it does not drop: the winsorised bars
    keep their sign and their flag-ness.

    ``min_periods`` (default 2, the minimum for a sample std) is the number of
    finite trailing observations required before a value is produced.
    """
    tpl = _template(x)
    a = _to_array(x, "x")
    w = None if window is None else int(window)
    if w is not None and w < 2:
        raise ValueError("window must be >= 2 (or None for expanding)")
    mp = int(min_periods)
    if mp < 2:
        raise ValueError("min_periods must be >= 2")
    out = _standardize_core(a, window=w, method=method, min_periods=mp)
    if clip is not None:
        c = abs(float(clip))
        out = np.clip(out, -c, c)
    return _like(tpl, out, name=f"standardize_{method}")


def detrend(x: SeriesLike, method: str = "diff", window: int | None = None):
    """Remove the level/trend from a series, causally.

    Methods:
      * ``'diff'``    : x_t - x_{t-k}, k = ``window`` or 1 if None.
      * ``'logdiff'`` : log(x_t) - log(x_{t-k}), same k. Non-positive inputs
        give NaN (a log return of a non-positive price is undefined, not -inf).
      * ``'ols'``     : residual of x_t from a linear-in-time OLS fit on the
        trailing sample ``x[t-window+1 : t+1]`` (or the expanding sample
        ``x[0 : t+1]`` when ``window is None``). The fit includes ``x_t``,
        which is fine and necessary — a residual needs its own observation —
        and uses no data after ``t``, so it stays strictly causal. At least
        3 finite points are required (with 2 the residual is identically 0).

    Note the deliberate absence of a full-sample OLS detrend. Fitting a trend
    on the whole sample and taking residuals is the standard textbook detrend,
    and it is look-ahead: the residual at bar 10 depends on prices from bar
    5000. Use the expanding fit above instead; it converges to the same thing
    and is tradable.
    """
    tpl = _template(x)
    a = _to_array(x, "x")
    n = a.size
    if method in ("diff", "logdiff"):
        k = 1 if window is None else int(window)
        if k < 1:
            raise ValueError("window (lag) must be >= 1 for diff/logdiff")
        if method == "logdiff":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                a = np.where(a > 0, np.log(np.where(a > 0, a, 1.0)), np.nan)
        out = np.full(n, np.nan)
        if k < n:
            out[k:] = a[k:] - a[:-k]
        return _like(tpl, out, name=f"detrend_{method}")

    if method != "ols":
        raise ValueError("method must be one of 'diff', 'logdiff', 'ols'")

    w = None if window is None else int(window)
    if w is not None and w < 3:
        raise ValueError("window must be >= 3 for an OLS detrend")
    out = np.full(n, np.nan)
    for t in range(n):
        if not np.isfinite(a[t]):
            continue
        lo = 0 if w is None else max(0, t - w + 1)
        s = a[lo : t + 1]
        mask = np.isfinite(s)
        if int(mask.sum()) < 3:
            continue
        idx = np.arange(s.size, dtype=float)[mask]
        y = s[mask]
        xbar = float(idx.mean())
        denom = float(((idx - xbar) ** 2).sum())
        if denom <= 0:
            continue
        slope = float(((idx - xbar) * (y - y.mean())).sum()) / denom
        fitted = float(y.mean()) + slope * ((s.size - 1) - xbar)
        out[t] = a[t] - fitted
    return _like(tpl, out, name="detrend_ols")
