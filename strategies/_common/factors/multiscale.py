"""Multi-scale / multi-timeframe signal processing.

Implements the note's two central ideas in a form you can put in front of a
risk committee:

1. *"wavelet transform 偵測各個尺度形態學的 resonance"* -> a hand-rolled MODWT
   plus :func:`cross_scale_resonance`.
2. *"large-scale data as filter, small-scale data as executor"* -> the honest
   as-of alignment in :func:`mtf_align` and the statistical test of whether the
   filter actually buys you anything in :func:`conditional_lift`.

Why MODWT and not the decimated DWT
-----------------------------------
The Maximal Overlap DWT (Percival & Walden 2000, ch. 5; also known as the
undecimated / stationary / a-trous transform) is the right transform for
trading signals for three reasons the decimated DWT does not satisfy:

* **Shift invariance.** Shifting the input by one bar shifts the MODWT
  coefficients by one bar. The decimated DWT's downsampling makes its
  coefficients depend on the *phase* of the sample origin, so a signal built
  on it changes when you add one more bar of history at the front — an
  unacceptable property for anything that runs live.
* **Any sample length N.** No power-of-two padding, hence no padding artefacts
  masquerading as signal.
* **Energy preservation.** ``sum_j ||W_j||^2 + ||V_J||^2 == ||x||^2`` exactly
  (circular boundary), which is what makes :func:`scale_energy` a genuine
  variance decomposition rather than a heuristic.

PyWavelets is deliberately not a dependency; the pyramid algorithm is ~20 lines
of numpy and vendoring it keeps this module lift-ready into ``gs_common``.

Causality
---------
``mode='causal'`` is the ONLY mode that may generate trading signals. The
circular-boundary mode wraps the end of the sample onto the beginning, so
``W_j(0)`` depends on ``x(N-1)``: that is look-ahead of the worst kind, because
it is invisible in a backtest that uses the whole array at once.

Design rule (mirrors ``strategies/_common/validation/``): this module consumes
only arrays / pandas objects, imports nothing from zipline or gs-strategy, and
is therefore lift-ready into ``gs_common.quant.factors``.
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

try:
    from scipy.stats import norm  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required for factors.multiscale: pip install scipy"
    ) from exc


#: Names / call-forms in this module that are NOT causal and must therefore
#: never be used to generate a trading signal. They exist for research and
#: diagnostics only. Anything not listed here is safe for signal generation.
NONCAUSAL: tuple[str, ...] = (
    "modwt_mra",
    "modwt(mode='circular')",
    "scale_energy",
)

#: Entry points that ARE strictly causal (value at t depends only on x[<=t]).
CAUSAL: tuple[str, ...] = (
    "modwt(mode='causal')",
    "cross_scale_resonance",
    "mtf_align",
)

#: Below this many conditioned observations, ``conditional_lift`` refuses to
#: let a lift be read as evidence. 30 is the conventional normal-approximation
#: floor for a proportion; it is a convention, not a theorem, and the Wilson
#: interval returned alongside is the honest quantity.
_MIN_CONDITIONED_OBS = 30

_SQRT2 = math.sqrt(2.0)
_SQRT3 = math.sqrt(3.0)

# DWT scaling ("father") filters, normalised so that sum(g) == sqrt(2) and
# sum(g**2) == 1. The MODWT rescaling by 1/sqrt(2) is applied in _filters().
_SCALING_FILTERS: dict[str, np.ndarray] = {
    # Haar == Daubechies D(2).
    "haar": np.array([1.0 / _SQRT2, 1.0 / _SQRT2]),
    # Daubechies D(4) (``db2`` in PyWavelets' naming). Percival & Walden (2000)
    # table 109.
    "d4": np.array(
        [
            (1.0 + _SQRT3) / (4.0 * _SQRT2),
            (3.0 + _SQRT3) / (4.0 * _SQRT2),
            (3.0 - _SQRT3) / (4.0 * _SQRT2),
            (1.0 - _SQRT3) / (4.0 * _SQRT2),
        ]
    ),
}
_SCALING_FILTERS["d2"] = _SCALING_FILTERS["haar"]


def available_wavelets() -> tuple[str, ...]:
    """Names accepted by the ``wavelet`` argument of every function here."""
    return tuple(sorted(_SCALING_FILTERS))


def _filters(wavelet: str) -> tuple[np.ndarray, np.ndarray]:
    """MODWT-rescaled (g~, h~) filter pair for ``wavelet``.

    Returns the scaling filter ``g~ = g / sqrt(2)`` and the wavelet filter
    ``h~ = h / sqrt(2)``, where ``h_l = (-1)**l * g_{L-1-l}`` is the usual
    quadrature-mirror relation. With this normalisation
    ``sum(g~**2) == sum(h~**2) == 1/2``, which is what makes the MODWT a tight
    frame and hence energy-preserving (Percival & Walden 2000, eq. 96b).
    """
    try:
        g = _SCALING_FILTERS[wavelet]
    except KeyError:
        raise ValueError(
            f"unknown wavelet {wavelet!r}; available: {available_wavelets()}"
        ) from None
    L = g.size
    signs = np.array([(-1.0) ** l for l in range(L)])
    h = signs * g[::-1]
    return g / _SQRT2, h / _SQRT2


def _equivalent_filter_width(level: int, L: int) -> int:
    """Width of the level-``j`` equivalent MODWT filter: ``(2^j - 1)(L-1) + 1``.

    Percival & Walden (2000), eq. 96a. The first index whose level-``j``
    coefficient is computed from real (non-padded) data is ``width - 1``.
    """
    return (2**level - 1) * (L - 1) + 1


def max_level(n: int, wavelet: str = "haar") -> int:
    """Largest level ``J`` whose equivalent filter still fits inside ``n`` samples.

    ``J = max{ j : (2^j - 1)(L-1) + 1 <= n }``, floored at 1.
    """
    L = _SCALING_FILTERS[wavelet].size if wavelet in _SCALING_FILTERS else 2
    j = 1
    while _equivalent_filter_width(j + 1, L) <= n:
        j += 1
    return j


def _circ_conv(v: np.ndarray, f: np.ndarray, step: int) -> np.ndarray:
    """``y(t) = sum_l f_l * v[(t - step*l) mod N]`` (circular, non-causal)."""
    y = np.zeros_like(v)
    for l, fl in enumerate(f):
        y += fl * np.roll(v, step * l)
    return y


def _circ_conv_adj(w: np.ndarray, f: np.ndarray, step: int) -> np.ndarray:
    """Adjoint of :func:`_circ_conv`: ``y(t) = sum_l f_l * w[(t + step*l) mod N]``.

    Because the MODWT is a tight frame, the adjoint *is* the inverse — this is
    what makes the MRA reconstruction exact rather than approximate.
    """
    y = np.zeros_like(w)
    for l, fl in enumerate(f):
        y += fl * np.roll(w, -step * l)
    return y


def _causal_conv(v: np.ndarray, f: np.ndarray, step: int) -> np.ndarray:
    """``y(t) = sum_l f_l * v[t - step*l]`` with zero fill for ``t - step*l < 0``.

    Strictly backward-looking: ``y(t)`` never touches an index above ``t``, and
    the zero fill never wraps around to the end of the sample. The samples
    contaminated by that zero fill are masked to NaN by the caller.
    """
    y = np.zeros_like(v)
    for l, fl in enumerate(f):
        s = step * l
        if s == 0:
            y += fl * v
        elif s < v.size:
            y[s:] += fl * v[:-s]
    return y


def _as_1d(x) -> tuple[np.ndarray, pd.Index | None]:
    if isinstance(x, (pd.Series, pd.DataFrame)):
        if isinstance(x, pd.DataFrame):
            if x.shape[1] != 1:
                raise ValueError("DataFrame input must have exactly one column")
            idx, x = x.index, x.iloc[:, 0]
        else:
            idx = x.index
        return np.asarray(x, dtype=float), idx
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 1:
        raise ValueError("input must be one-dimensional")
    return arr, None


def modwt(
    x,
    wavelet: str = "haar",
    levels: int | None = None,
    mode: str = "causal",
) -> tuple[np.ndarray, np.ndarray]:
    """Maximal Overlap Discrete Wavelet Transform (MODWT) of a 1-D series.

    Computes, for ``j = 1..J``, the detail (band-pass) coefficients

        ``W_j(t) = sum_{l=0}^{L-1} h~_l * V_{j-1}(t - 2^{j-1} l)``

    and the smooth (low-pass) coefficients

        ``V_j(t) = sum_{l=0}^{L-1} g~_l * V_{j-1}(t - 2^{j-1} l)``,

    starting from ``V_0 = x``, where ``g~ = g/sqrt(2)`` and ``h~ = h/sqrt(2)``
    are the MODWT-rescaled scaling and wavelet filters. Reference: Percival &
    Walden, *Wavelet Methods for Time Series Analysis* (2000), section 5.2.

    Scale interpretation: level ``j`` isolates variation with periods roughly in
    ``[2^j, 2^(j+1)]`` sampling intervals, so on daily bars level 1 ~ 2-4 days,
    level 4 ~ 16-32 days.

    Parameters
    ----------
    x
        1-D array / Series.
    wavelet
        ``'haar'`` (== ``'d2'``) or ``'d4'``. See :func:`available_wavelets`.
    levels
        Number of detail levels ``J``. ``None`` picks :func:`max_level`.
        **Pin this explicitly for anything streaming**: with ``None`` the level
        count is a function of ``N``, so appending a bar can change the shape of
        the output (which is not look-ahead, but it is a footgun).
    mode
        ``'causal'`` (default) — the level-``j`` filter looks only at
        ``t, t-1, ..., t-(L_j-1)`` where ``L_j = (2^j - 1)(L-1) + 1``. Indices
        below zero are zero-filled and the whole contaminated warm-up region
        ``t < L_j - 1`` is returned as NaN. **This is the only mode that may be
        used to generate signals.**

        ``'circular'`` — the classic MODWT with a circular (periodic) boundary.
        It is the mode that preserves energy exactly and it is what
        :func:`modwt_mra` and :func:`scale_energy` use, but it is **NOT causal**:
        ``W_j(0)`` is a function of ``x(N-1)``. Research and diagnostics only;
        see the module constant :data:`NONCAUSAL`.

    Returns
    -------
    (W, V)
        ``W`` has shape ``(levels, N)``; ``W[j-1]`` is the level-``j`` detail.
        ``V`` has shape ``(N,)`` and is the level-``J`` smooth.

    Notes
    -----
    Approximation warning: in ``'causal'`` mode the transform is *not* the
    textbook MODWT. Zero-filling the pre-sample region is a boundary choice, not
    a theorem; the reflection / periodic boundaries used in the literature are
    unavailable to a causal filter by construction. Consequently energy is
    **not** exactly preserved in causal mode, and :func:`modwt_mra` refuses to
    run on it. What causal mode does guarantee is the property that matters for
    trading: the value at ``t`` is a fixed linear function of ``x[t-L_j+1..t]``
    only, so recomputing on a truncated history reproduces the same numbers.
    """
    arr, _ = _as_1d(x)
    n = arr.size
    if n == 0:
        raise ValueError("empty input")
    if np.isnan(arr).any():
        raise ValueError("input contains NaN; interpolate or drop before MODWT")
    g, h = _filters(wavelet)
    L = g.size
    if levels is None:
        levels = max_level(n, wavelet)
    if levels < 1:
        raise ValueError("levels must be >= 1")
    if mode not in ("causal", "circular"):
        raise ValueError("mode must be 'causal' or 'circular'")

    conv = _causal_conv if mode == "causal" else _circ_conv
    W = np.empty((levels, n), dtype=float)
    v = arr.copy()
    for j in range(1, levels + 1):
        step = 2 ** (j - 1)
        W[j - 1] = conv(v, h, step)
        v = conv(v, g, step)

    if mode == "causal":
        # Mask every sample whose level-j filter support reached below index 0.
        for j in range(1, levels + 1):
            warm = min(n, _equivalent_filter_width(j, L) - 1)
            W[j - 1, :warm] = np.nan
        warm_v = min(n, _equivalent_filter_width(levels, L) - 1)
        v = v.copy()
        v[:warm_v] = np.nan
    return W, v


def modwt_mra(
    x,
    wavelet: str = "haar",
    levels: int | None = None,
    mode: str = "circular",
) -> tuple[np.ndarray, np.ndarray]:
    """Additive multiresolution analysis (MRA): ``sum_j D_j + S_J == x`` exactly.

    Each ``D_j`` is the part of ``x`` living at scale ``j`` and ``S_J`` is the
    residual trend, all on the original time axis and all summing back to the
    input to machine precision. Obtained by zeroing every MODWT coefficient
    except one band and applying the inverse (== adjoint) transform; Percival &
    Walden (2000), section 5.5.

    .. warning::
       **NON-CAUSAL. Never use this to generate a trading signal.** ``D_j(t)``
       is a function of ``x(t+1), x(t+2), ...`` (and, through the circular
       boundary, of the very end of the sample). Listed in :data:`NONCAUSAL`.
       It is for research: decomposing a realised path to see *which* scale a
       move actually happened on. The causal counterpart usable for signals is
       ``modwt(..., mode='causal')`` and :func:`cross_scale_resonance`.

    Parameters
    ----------
    mode
        Only ``'circular'`` is supported. ``'causal'`` raises: an additive MRA
        with a causal synthesis does not exist — the synthesis filter is the
        time-reverse of the analysis filter, so reconstructing ``x(t)`` from
        band-limited pieces inherently needs coefficients at ``t' > t``. Faking
        it (e.g. by truncating the synthesis) would break the one property the
        MRA is for, namely exact additivity.

    Returns
    -------
    (D, S)
        ``D`` shape ``(levels, N)``, ``S`` shape ``(N,)``.
    """
    if mode != "circular":
        raise ValueError(
            "modwt_mra supports mode='circular' only: an additive MRA is "
            "inherently non-causal (see docstring). For causal use call "
            "modwt(..., mode='causal')."
        )
    arr, _ = _as_1d(x)
    n = arr.size
    g, h = _filters(wavelet)
    if levels is None:
        levels = max_level(n, wavelet)
    W, V = modwt(arr, wavelet=wavelet, levels=levels, mode="circular")

    def _synthesise(coeffs: np.ndarray, start_level: int, is_detail: bool) -> np.ndarray:
        """Push a single band back down to level 0 through the adjoint filters."""
        cur = coeffs
        for j in range(start_level, 0, -1):
            step = 2 ** (j - 1)
            f = h if (is_detail and j == start_level) else g
            cur = _circ_conv_adj(cur, f, step)
        return cur

    D = np.empty((levels, n), dtype=float)
    for j in range(1, levels + 1):
        D[j - 1] = _synthesise(W[j - 1], j, is_detail=True)
    S = _synthesise(V, levels, is_detail=False)
    return D, S


def scale_energy(
    x,
    wavelet: str = "haar",
    levels: int | None = None,
    demean: bool = True,
) -> np.ndarray:
    """Fraction of total variance living at each scale, plus the smooth.

    The "which timeframe does this instrument actually live on" diagnostic.
    Returns an array of length ``levels + 1``: entries ``0..levels-1`` are the
    detail levels ``1..J`` and the last entry is the level-``J`` smooth.

        ``e_j = ||W_j||^2 / (sum_k ||W_k||^2 + ||V_J||^2)``

    Because the circular MODWT is a tight frame, the denominator equals
    ``sum((x - mean)**2)`` exactly (``demean=True``), so the entries are true
    variance shares and sum to 1 to machine precision (Percival & Walden 2000,
    eq. 96b).

    .. warning::
       **NON-CAUSAL / full-sample.** Uses the circular boundary and the whole
       sample's mean. Listed in :data:`NONCAUSAL`. Use it to *describe* an
       instrument, never as an input to a live signal. :func:`cross_scale_resonance`
       therefore does **not** call this for its weights; it recomputes the
       energy share on an expanding window instead.

    Parameters
    ----------
    demean
        Subtract the sample mean first, so the result is a variance rather than
        a raw-energy decomposition. With ``demean=False`` a series with a large
        constant offset dumps almost everything into the smooth simply because
        of its level.
    """
    arr, _ = _as_1d(x)
    if demean:
        arr = arr - arr.mean()
    W, V = modwt(arr, wavelet=wavelet, levels=levels, mode="circular")
    parts = np.append((W**2).sum(axis=1), (V**2).sum())
    total = parts.sum()
    if total <= 0:
        return np.full(parts.size, np.nan)
    return parts / total


def cross_scale_resonance(
    x,
    scales: Sequence[int] = (1, 2, 3),
    wavelet: str = "haar",
    weights: Sequence[float] | None = None,
) -> np.ndarray:
    """Signed agreement of several scales' directions — the note's "resonance".

    With ``s_j(t) = sign(W_j(t))`` taken from the **causal** MODWT details,

        ``R(t) = sum_j w_j * s_j(t) / sum_j w_j``  in ``[-1, 1]``.

    ``|R(t)| ~ 1`` means every requested scale points the same way (a genuine
    multi-scale trend or multi-scale reversal); ``R(t) ~ 0`` means the scales
    disagree and the "trend" you think you see lives on one timeframe only.
    Returns NaN over the warm-up of the deepest requested scale.

    This is our own construction rather than a citable statistic: the wavelet
    literature (e.g. Torrence & Compo 1998 on wavelet coherence, Gencay,
    Selcuk & Whitcher 2002 on multiscale finance) measures cross-*series*
    co-movement at a fixed scale, not cross-*scale* sign agreement within one
    series. Treat the exact functional form as a design choice, not a result.

    Parameters
    ----------
    scales
        Which detail levels to poll, 1-based. ``levels`` for the underlying
        MODWT is ``max(scales)``, so the output shape does not depend on ``N``.
    weights
        Fixed weights, one per entry of ``scales``. If ``None`` (default) the
        weight of scale ``j`` at time ``t`` is its **expanding-window mean
        square** ``mean(W_j(s)**2 : s <= t)``.

        This deliberately deviates from calling :func:`scale_energy`: the
        full-sample energy share would leak the future into every historical
        value of ``R``, which is exactly the kind of leak that makes a backtest
        look better than the live system. The expanding-window version uses only
        data up to ``t`` and is therefore reproducible bar by bar. Early in the
        sample it is a noisy estimate of the same quantity — that is the honest
        price of causality, not a bug.

    Returns
    -------
    np.ndarray
        Shape ``(N,)``, values in ``[-1, 1]``, NaN in the warm-up.
    """
    arr, _ = _as_1d(x)
    scales = tuple(int(s) for s in scales)
    if not scales:
        raise ValueError("scales must be non-empty")
    if min(scales) < 1:
        raise ValueError("scales are 1-based; the smallest valid scale is 1")
    n = arr.size
    W, _V = modwt(arr, wavelet=wavelet, levels=max(scales), mode="causal")
    detail = W[[s - 1 for s in scales], :]  # (k, N)

    valid = ~np.isnan(detail).any(axis=0)
    signs = np.sign(np.nan_to_num(detail, nan=0.0))

    if weights is None:
        sq = np.where(np.isnan(detail), 0.0, detail**2)
        cnt = np.cumsum(~np.isnan(detail), axis=1)
        w = np.cumsum(sq, axis=1) / np.maximum(cnt, 1)
    else:
        w_arr = np.asarray(weights, dtype=float)
        if w_arr.shape != (len(scales),):
            raise ValueError("weights must have one entry per requested scale")
        if (w_arr < 0).any():
            raise ValueError("weights must be non-negative")
        w = np.repeat(w_arr[:, None], n, axis=1)

    denom = w.sum(axis=0)
    out = np.full(n, np.nan)
    ok = valid & (denom > 0)
    out[ok] = (w[:, ok] * signs[:, ok]).sum(axis=0) / denom[ok]
    return out


def mtf_align(
    frames: Mapping[str, pd.DataFrame | pd.Series],
    target_index: pd.DatetimeIndex,
    label: str = "close",
    lag_bars: int = 1,
) -> pd.DataFrame:
    """Align coarse timeframes onto a fine index without leaking the future.

    The note's *"各種資料週期速度更新的非同步性"* problem. A weekly bar labelled
    Monday is not knowable on Monday; it is knowable only once that week has
    **closed**. The naive ``reindex(method='ffill')`` on the coarse frame's own
    label makes the whole week's high, low and close visible from its first
    minute, which is the single most common source of a beautiful, fake
    multi-timeframe backtest.

    Implementation: for each coarse frame the values are shifted down by
    ``shift`` rows and then joined onto ``target_index`` with a **backward
    as-of** join (:func:`pandas.merge_asof`) keyed on the coarse index. So at a
    target timestamp ``t`` you see the value of the most recent coarse bar that
    had already *closed* at or before ``t``, and nothing else.

    ``shift = (1 if label == 'open' else 0) + lag_bars``

    ==================  ==========  ==========================================
    ``label``           ``lag_bars``  meaning
    ==================  ==========  ==========================================
    ``'open'``          0           Index is the bar's left/open label (pandas
                                    ``resample`` default). Bar *i* closes at
                                    ``index[i+1]``, so shifting by one row is
                                    exactly right and adds no extra delay.
    ``'close'``         0           Index is already the bar's end timestamp.
                                    Correct **only if the caller has verified
                                    that**; many vendors ship left-labelled bars
                                    while calling the column "close".
    ``'close'``         1 (default) One extra bar of conservatism on top of the
                                    above.
    ==================  ==========  ==========================================

    The default is ``label='close', lag_bars=1`` — one bar more conservative
    than strictly necessary. That is deliberate: an alignment that is one bar
    late costs you a little edge, an alignment that is one bar early invents
    edge that does not exist.

    Parameters
    ----------
    frames
        e.g. ``{'W': weekly_df, 'D': daily_df, 'H4': h4_df}``. Values may be
        DataFrames or Series; each must carry a sorted-able DatetimeIndex.
    target_index
        The finest DatetimeIndex, i.e. the index of the frame you actually
        trade on. Must share tz-awareness with every coarse frame's index.
    label
        ``'open'`` or ``'close'`` — the labelling convention of the coarse
        indices (assumed the same for all frames).
    lag_bars
        Extra whole coarse bars of delay. Must be >= 0.

    Returns
    -------
    pandas.DataFrame
        Indexed by ``target_index``; columns named ``f"{key}_{column}"``
        (a Series contributes a single column named after its key). NaN before
        a frame's first visible bar.
    """
    if label not in ("open", "close"):
        raise ValueError("label must be 'open' or 'close'")
    if lag_bars < 0:
        raise ValueError("lag_bars must be >= 0")
    target_index = pd.DatetimeIndex(target_index)
    if not target_index.is_monotonic_increasing:
        raise ValueError("target_index must be sorted ascending")
    shift = (1 if label == "open" else 0) + lag_bars

    out = pd.DataFrame(index=target_index)
    left = pd.DataFrame({"__t": target_index})
    for key, frame in frames.items():
        df = frame.to_frame(name=key) if isinstance(frame, pd.Series) else frame.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            raise TypeError(f"frame {key!r} must have a DatetimeIndex")
        df = df.sort_index()
        df.columns = [f"{key}_{c}" for c in df.columns]
        # Shift the *values* rather than the index: at coarse timestamp
        # index[i] the visible row is i - shift, i.e. the bar that closed then.
        # Shifting values (not the index) also handles the tail without having
        # to invent timestamps beyond the frame's last bar.
        right = df.shift(shift).reset_index()
        right.columns = ["__t", *df.columns]
        right = right.dropna(subset=["__t"])
        merged = pd.merge_asof(left, right, on="__t", direction="backward")
        for col in df.columns:
            out[col] = merged[col].to_numpy()
    return out


def _wilson_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson (1927) score interval for a binomial proportion.

    Preferred over the Wald interval here because the conditioned sample is
    routinely small and often has a proportion near 0 or 1, exactly where Wald
    coverage collapses (Brown, Cai & DasGupta 2001).
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    z = float(norm.ppf(1.0 - alpha / 2.0))
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z / denom * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return (max(0.0, centre - half), min(1.0, centre + half))


def conditional_lift(
    signal,
    condition,
    forward_return,
    threshold: float = 0.0,
) -> dict:
    """Does the large-scale filter actually improve the small-scale trigger?

    The formal version of the note's
    ``P(trading signal in small-scale morphology | large-scale morphology)``.

    Given a boolean ``signal`` (the small-scale trigger), a boolean
    ``condition`` (the large-scale regime filter) and a ``forward_return``
    series, computes

        ``p_uncond = P(fwd > threshold | signal)``
        ``p_cond   = P(fwd > threshold | signal AND condition)``
        ``lift     = p_cond / p_uncond``

    **The point of this function is the sample size, not the lift.** A filter
    that raises precision while shrinking the conditioning sample can be
    statistically indistinguishable from no filter at all: halve your trades and
    the standard error on the win rate grows by ~1.4x, so a "lift of 1.3" on 25
    observations is entirely consistent with a filter that does nothing. Lift
    reported without ``n_cond`` and a confidence interval is not evidence, and
    ``power_warning`` exists so that this cannot be quietly omitted from a
    report.

    Returns
    -------
    dict with keys
        ``p_uncond``, ``p_cond``, ``lift``, ``n_signal``, ``n_cond``,
        ``ci_cond`` (Wilson 95% CI on ``p_cond``), ``se_diff``, ``z``,
        ``p_value``, ``power_warning``.

    ``power_warning`` is True when ``n_cond < 30`` **or** when the Wilson CI on
    ``p_cond`` contains ``p_uncond`` — i.e. whenever "the filter does nothing"
    remains a comfortable explanation of the data.

    Caveat on the test statistic (the literature is not on our side here):
    ``z`` is the standard two-proportion z-test with a pooled variance, but the
    two samples are **nested** (the conditioned set is a subset of the signal
    set), not independent. The nesting induces a positive correlation between
    the two estimates, so the independent-sample standard error ``se_diff`` is
    too large and the reported ``p_value`` is therefore *conservative* — it will
    under-reject rather than over-reject. If you need an exact test, compare
    ``signal AND condition`` against ``signal AND NOT condition``, which are
    genuinely disjoint. We report the nested version because it is what
    "lift versus the unconditional base rate" literally means.

    Rows where ``forward_return`` is NaN are dropped from every count.
    """
    sig = np.asarray(signal)
    cond = np.asarray(condition)
    fwd = np.asarray(forward_return, dtype=float)
    if not (sig.shape == cond.shape == fwd.shape):
        raise ValueError("signal, condition and forward_return must be same length")
    sig = np.nan_to_num(sig.astype(float), nan=0.0).astype(bool)
    cond = np.nan_to_num(cond.astype(float), nan=0.0).astype(bool)

    usable = ~np.isnan(fwd)
    sel_u = sig & usable
    sel_c = sig & cond & usable

    n_signal = int(sel_u.sum())
    n_cond = int(sel_c.sum())
    k_signal = int((fwd[sel_u] > threshold).sum())
    k_cond = int((fwd[sel_c] > threshold).sum())

    p_uncond = k_signal / n_signal if n_signal else float("nan")
    p_cond = k_cond / n_cond if n_cond else float("nan")
    lift = p_cond / p_uncond if (n_signal and n_cond and p_uncond > 0) else float("nan")
    ci_cond = _wilson_interval(k_cond, n_cond)

    if n_signal and n_cond:
        p_pool = (k_cond + k_signal) / (n_cond + n_signal)
        se_diff = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_cond + 1.0 / n_signal))
        if se_diff > 0:
            z = (p_cond - p_uncond) / se_diff
            p_value = float(2.0 * norm.sf(abs(z)))
        else:
            z, p_value = float("nan"), float("nan")
    else:
        se_diff = z = p_value = float("nan")

    ci_contains_base = (
        n_cond > 0
        and not math.isnan(p_uncond)
        and ci_cond[0] <= p_uncond <= ci_cond[1]
    )
    # Warn whenever "the filter does nothing" is still a comfortable reading of
    # the data: too few conditioned observations to resolve anything, or a
    # Wilson interval that still straddles the unconditional win rate. Coerced
    # through bool() so the flag is a real Python bool -- a numpy.bool_ here
    # would silently fail an `is True` check downstream.
    power_warning = bool(n_cond < _MIN_CONDITIONED_OBS or ci_contains_base)

    return {
        "p_uncond": p_uncond,
        "p_cond": p_cond,
        "lift": lift,
        "n_signal": n_signal,
        "n_cond": n_cond,
        "ci_cond": ci_cond,
        "se_diff": se_diff,
        "z": z,
        "p_value": p_value,
        "power_warning": power_warning,
    }


__all__ = [
    "NONCAUSAL",
    "CAUSAL",
    "available_wavelets",
    "max_level",
    "modwt",
    "modwt_mra",
    "scale_energy",
    "cross_scale_resonance",
    "mtf_align",
    "conditional_lift",
]
