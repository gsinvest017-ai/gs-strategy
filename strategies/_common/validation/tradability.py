"""Is this instrument even suitable for technical analysis?

A morphological / technical strategy only has something to find if the price
path carries exploitable *serial* structure. If a series is statistically
indistinguishable from a martingale, no amount of pattern matching will help,
and whatever edge a backtest shows is selection noise. This module runs a
battery of predictability diagnostics *before* the strategy work starts, and
reports them without dressing them up.

Design rule (same as sharpe.py / cpcv.py): this module consumes only price and
return arrays, imports nothing from zipline or gs-strategy, and is therefore
lift-ready into ``gs_common.quant.validation``.

Causality note — read this before wiring anything here into a signal
--------------------------------------------------------------------
Every public entry point below is a **whole-sample diagnostic**: it maps a
series to a scalar or to a small table, using the whole sample it is given. No
function here maps a time series to a time series of signals, so the usual
"value at t may depend only on inputs at <= t" property is vacuous for them —
there is no per-bar output to be causal about.

That is *not* a licence to use them carelessly. The look-ahead risk lives one
level up: if you compute ``ta_suitability`` on 2010-2026 and then backtest a
technical strategy on 2010-2026, you have selected the instrument using the
same data you are measuring on, and the resulting Sharpe is contaminated.
Compute the diagnostics on a training window, freeze the verdict, and trade
the window that follows. ``WHOLE_SAMPLE_DIAGNOSTICS`` names every function
that carries this obligation.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

try:
    from scipy.stats import norm  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required for validation.tradability: pip install scipy"
    ) from exc


#: Every public function in this module is a whole-sample diagnostic, i.e. its
#: result depends on the entire input window. None of them is a signal
#: generator, and none of them may be applied to the same window a strategy is
#: later evaluated on without inviting selection bias. Kept as data so a test
#: can assert the module never quietly grows a per-bar signal function.
WHOLE_SAMPLE_DIAGNOSTICS: frozenset[str] = frozenset({
    "variance_ratio",
    "variance_ratio_profile",
    "hurst_rs",
    "hurst_dfa",
    "permutation_entropy",
    "ljung_box_returns",
    "ljung_box_abs_returns",
    "runs_test",
    "ta_suitability",
})


# --------------------------------------------------------------------------
# ta_suitability scoring constants — exposed so the heuristic is auditable
# rather than buried in the function body. These are judgement calls, not
# estimates of anything; see ta_suitability.__doc__.
# --------------------------------------------------------------------------
VR_WEIGHT = 35.0
LJUNG_BOX_WEIGHT = 25.0
RUNS_WEIGHT = 15.0
ENTROPY_WEIGHT = 15.0
HURST_WEIGHT = 10.0

#: Permutation entropy of an iid series sits just below 1.0 (finite-sample
#: bias), so credit is only given below this floor, saturating one SPAN lower.
ENTROPY_FLOOR = 0.99
ENTROPY_SPAN = 0.10

#: |H - 0.5| at which the Hurst component saturates.
HURST_SPAN = 0.15

SUITABLE_THRESHOLD = 55.0
MARGINAL_THRESHOLD = 25.0


def _clean(x: Sequence[float], name: str, minimum: int) -> np.ndarray:
    a = np.asarray(x, dtype=float).ravel()
    a = a[np.isfinite(a)]
    if a.size < minimum:
        raise ValueError(f"{name}: need at least {minimum} finite observations, got {a.size}")
    return a


# --------------------------------------------------------------------------
# 1-2. Variance ratio (Lo & MacKinlay 1988)
# --------------------------------------------------------------------------

def variance_ratio(
    returns: Sequence[float],
    q: int,
    heteroskedastic: bool = True,
) -> dict:
    """Lo & MacKinlay (1988) variance ratio test at aggregation horizon ``q``.

    Computes VR(q) = Var[q-period return] / (q * Var[1-period return]), using
    overlapping q-period sums and the unbiased estimators of Lo & MacKinlay
    (1988), "Stock Market Prices Do Not Follow Random Walks: Evidence from a
    Simple Specification Test", *Review of Financial Studies* 1(1), 41-66.

    With ``T`` return observations and ``mu = mean(r)``::

        sigma_a^2 = (1 / (T - 1)) * sum_{t=1..T} (r_t - mu)^2
        m         = q * (T - q + 1) * (1 - q / T)
        sigma_c^2 = (1 / m) * sum_{t=q..T} ( sum_{j=0..q-1} r_{t-j} - q*mu )^2
        VR(q)     = sigma_c^2 / sigma_a^2

    Both of Lo & MacKinlay's z-statistics are returned:

    * homoskedastic (their M1 / z1), asymptotic variance
      ``phi(q) = 2 * (2q - 1) * (q - 1) / (3 * q * T)``;
    * heteroskedasticity-robust (their M2 / z2), which is the one to quote on
      financial returns because volatility clustering makes the homoskedastic
      variance far too small::

          delta_j = sum_{t=j+1..T} (r_t - mu)^2 (r_{t-j} - mu)^2
                    / [ sum_{t=1..T} (r_t - mu)^2 ]^2
          theta   = sum_{j=1..q-1} [ 2 (q - j) / q ]^2 * delta_j
          z2      = (VR - 1) / sqrt(theta)

    ``heteroskedastic`` selects which of the two lands in the ``'z'`` and
    ``'p_value'`` keys; both are always present under their own keys, so the
    caller can see whether the conclusion depends on that choice.

    Interpretation: VR > 1 means positive autocorrelation / trending (a
    q-period move is larger than q independent one-period moves), VR < 1 means
    mean reversion. VR == 1 is the random-walk null. Both z-statistics are
    asymptotically standard normal, so p-values on samples of a few hundred
    observations are approximate; the normal approximation is known to be
    poor in the tails for small ``T`` and large ``q``.

    Returns a dict with keys ``vr``, ``z``, ``p_value``, ``z_homoskedastic``,
    ``p_homoskedastic``, ``z_heteroskedastic``, ``p_heteroskedastic``, ``q``,
    ``n_obs``, ``heteroskedastic``.
    """
    if q < 2:
        raise ValueError("q must be >= 2 (q = 1 is the trivial identity VR = 1)")
    r = _clean(returns, "returns", minimum=3)
    t = r.size
    if t < 2 * q:
        raise ValueError(f"need at least 2q = {2 * q} return observations for q = {q}, got {t}")

    mu = r.mean()
    dev = r - mu
    sigma_a2 = float(dev @ dev) / (t - 1)
    if sigma_a2 <= 0.0:
        raise ValueError("returns have zero variance; the variance ratio is undefined")

    # Overlapping q-period sums via a cumulative sum: rolling[k] = r_k + ... + r_{k+q-1}
    csum = np.concatenate(([0.0], np.cumsum(r)))
    rolling = csum[q:] - csum[:-q]              # length T - q + 1
    m = q * (t - q + 1) * (1.0 - q / t)
    sigma_c2 = float(((rolling - q * mu) ** 2).sum()) / m

    vr = sigma_c2 / sigma_a2

    # --- M1: homoskedastic ---
    phi = 2.0 * (2 * q - 1) * (q - 1) / (3.0 * q * t)
    z_homo = (vr - 1.0) / math.sqrt(phi)

    # --- M2: heteroskedasticity-robust ---
    dev2 = dev ** 2
    denom = float(dev2.sum()) ** 2
    theta = 0.0
    for j in range(1, q):
        delta_j = float(dev2[j:] @ dev2[:-j]) / denom
        theta += (2.0 * (q - j) / q) ** 2 * delta_j
    if theta <= 0.0:
        # Degenerate only for pathological input (e.g. a constant series that
        # slipped past the variance check); refuse to emit a fake z rather
        # than dividing by ~0 and reporting a huge one.
        z_hetero = float("nan")
    else:
        z_hetero = (vr - 1.0) / math.sqrt(theta)

    p_homo = float(2.0 * norm.sf(abs(z_homo)))
    p_hetero = float(2.0 * norm.sf(abs(z_hetero))) if np.isfinite(z_hetero) else float("nan")

    z = z_hetero if heteroskedastic else z_homo
    p = p_hetero if heteroskedastic else p_homo
    return {
        "q": int(q),
        "n_obs": int(t),
        "vr": float(vr),
        "z": float(z),
        "p_value": float(p),
        "z_homoskedastic": float(z_homo),
        "p_homoskedastic": p_homo,
        "z_heteroskedastic": float(z_hetero),
        "p_heteroskedastic": p_hetero,
        "heteroskedastic": bool(heteroskedastic),
    }


def variance_ratio_profile(
    returns: Sequence[float],
    qs: Iterable[int] = (2, 4, 8, 16, 32),
    heteroskedastic: bool = True,
) -> pd.DataFrame:
    """VR(q) across a range of horizons, one row per ``q``.

    The *shape* of the profile is the object worth looking at, not any single
    q. A single significant VR(q) is one test out of many and is routinely a
    false positive; a profile that rises monotonically above 1 across horizons
    is the signature of genuine trend persistence, and one that dips below 1
    at short horizons and recovers is the signature of microstructure /
    bid-ask bounce rather than tradable mean reversion (Lo & MacKinlay 1988,
    section 2; Campbell, Lo & MacKinlay 1997, ch. 2).

    Note the rows are *not* independent tests — the q-period sums overlap and
    share the same underlying data — so counting how many rows have p < 0.05
    is not a valid multiple-comparison procedure. Read the profile, do not
    tally it.

    Columns: ``q``, ``vr``, ``z``, ``p_value``, ``z_homoskedastic``,
    ``p_homoskedastic``, ``z_heteroskedastic``, ``p_heteroskedastic``,
    ``n_obs``.
    """
    rows = []
    for q in qs:
        res = variance_ratio(returns, int(q), heteroskedastic=heteroskedastic)
        rows.append({
            "q": res["q"],
            "vr": res["vr"],
            "z": res["z"],
            "p_value": res["p_value"],
            "z_homoskedastic": res["z_homoskedastic"],
            "p_homoskedastic": res["p_homoskedastic"],
            "z_heteroskedastic": res["z_heteroskedastic"],
            "p_heteroskedastic": res["p_heteroskedastic"],
            "n_obs": res["n_obs"],
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3. Long-memory exponents
# --------------------------------------------------------------------------

#: Minimum number of distinct window sizes required before fitting a slope in
#: log-log space. Three points can be fitted but the resulting exponent is
#: noise; refusing is more honest than returning it.
_MIN_SCALES = 4


def _loglog_slope(sizes: np.ndarray, values: np.ndarray) -> float:
    ok = np.isfinite(values) & (values > 0)
    if ok.sum() < 3:
        return float("nan")
    slope = np.polyfit(np.log(sizes[ok]), np.log(values[ok]), 1)[0]
    return float(slope)


def _log_spaced(lo: int, hi: int, count: int = 16) -> np.ndarray:
    if hi <= lo:
        return np.array([lo], dtype=int)
    raw = np.unique(np.round(np.geomspace(lo, hi, count)).astype(int))
    return raw[raw >= lo]


def hurst_rs(x: Sequence[float], min_window: int = 8) -> float:
    """Hurst exponent of a price *path* by classical rescaled-range analysis.

    ``x`` is the **level series** (log prices, or a cumulative return path) —
    not the increments. The function differences it internally, so
    ``hurst_rs(log_prices)`` is the exponent of the path described by those
    prices.

    Method (Hurst 1951; Mandelbrot & Wallis 1969): let ``d = diff(x)``. For
    each window length ``n``, split ``d`` into non-overlapping blocks; within
    a block, mean-adjust, cumulate, take the range ``R`` of the cumulative
    deviations and the standard deviation ``S`` of the block, and average
    ``R/S`` over blocks. Then ``E[R/S](n) ~ c * n^H``, and ``H`` is the slope
    of ``log(R/S)`` on ``log(n)`` over log-spaced ``n`` from ``min_window`` to
    ``len(d) // 2``.

    Caveats, stated plainly because this estimator is routinely oversold:

    * R/S is **strongly biased upward on short samples**. On iid data it
      returns values well above 0.5 for n below roughly 1000 — the classical
      Anis & Lloyd (1976) / Weron (2002) small-sample correction exists
      precisely because of this, and is **not** applied here. Treat any H from
      fewer than ~1000 observations as uninformative.
    * H near 0.5 is the null, not a finding. It is not evidence of a random
      walk; it is an absence of evidence against one.
    * R/S is not robust to the fat tails and volatility clustering of real
      returns, both of which can shift H without any long memory being
      present. Corroborate with :func:`hurst_dfa` and with the variance-ratio
      profile before believing anything.
    """
    path = _clean(x, "x", minimum=32)
    d = np.diff(path)
    n_obs = d.size
    max_window = n_obs // 2
    if max_window < min_window:
        raise ValueError(
            f"series too short for R/S: need >= {2 * min_window + 1} points for "
            f"min_window={min_window}"
        )

    sizes = _log_spaced(min_window, max_window)
    if sizes.size < _MIN_SCALES:
        raise ValueError(
            f"series too short for R/S: only {sizes.size} usable window sizes between "
            f"{min_window} and {max_window}; need >= {_MIN_SCALES} for a log-log fit"
        )
    rs_means = np.full(sizes.size, np.nan)
    for i, n in enumerate(sizes):
        n_blocks = n_obs // n
        if n_blocks < 1:
            continue
        blocks = d[: n_blocks * n].reshape(n_blocks, n)
        centred = blocks - blocks.mean(axis=1, keepdims=True)
        cumdev = np.cumsum(centred, axis=1)
        rng = cumdev.max(axis=1) - cumdev.min(axis=1)
        std = blocks.std(axis=1, ddof=1) if n > 1 else np.zeros(n_blocks)
        good = std > 0
        if not good.any():
            continue
        rs_means[i] = float(np.mean(rng[good] / std[good]))
    return _loglog_slope(sizes.astype(float), rs_means)


def hurst_dfa(x: Sequence[float], order: int = 1) -> float:
    """Hurst / scaling exponent of a price *path* by detrended fluctuation analysis.

    ``x`` is the **level series** (log prices, or a cumulative return path).
    Note the convention: standard DFA (Peng et al. 1994, *Phys. Rev. E* 49,
    1685) integrates its input to build a profile, then detrends. Here the
    input *is* the profile — no additional integration is performed — so
    ``hurst_dfa(path)`` is numerically the same as textbook DFA applied to
    ``diff(path)``. This makes ``0.5`` the random-walk null for a price path,
    which is the convention a trading desk expects. Feeding this function
    *returns* instead of a path is a real and easy mistake and will give an
    exponent near 0, not near 0.5.

    Method: for each log-spaced scale ``s``, cut the series into
    non-overlapping windows of length ``s`` (forward and backward, so a
    trailing remainder is not discarded), fit and remove a polynomial of
    degree ``order`` inside each window, and take
    ``F(s) = sqrt(mean(residual^2))``. Then ``F(s) ~ s^alpha`` and ``alpha``
    is the reported exponent. ``order=1`` (DFA1) removes a linear trend, which
    is the usual choice; higher orders remove more of the deterministic drift
    at the cost of resolution at small ``s``.

    Caveats:

    * DFA is better behaved than R/S but is still biased on short samples and
      its estimate depends on the chosen scale range; different scale ranges
      on the same data routinely move ``alpha`` by 0.05-0.10. The scale range
      used here (``max(8, 4*(order+1))`` to ``n // 4``) is a common default,
      not a derived optimum.
    * ``alpha ~ 0.5`` is the null. It is not evidence of a random walk.
    * Volatility clustering alone can bias ``alpha`` upward without any
      predictability in direction.
    """
    y = _clean(x, "x", minimum=32)
    n = y.size
    min_scale = max(8, 4 * (order + 1))
    max_scale = n // 4
    if max_scale < min_scale:
        raise ValueError(
            f"series too short for DFA(order={order}): need >= {4 * min_scale} points, got {n}"
        )

    scales = _log_spaced(min_scale, max_scale)
    if scales.size < _MIN_SCALES:
        raise ValueError(
            f"series too short for DFA(order={order}): only {scales.size} usable scales "
            f"between {min_scale} and {max_scale}; need >= {_MIN_SCALES} for a log-log fit"
        )
    fluct = np.full(scales.size, np.nan)
    for i, s in enumerate(scales):
        n_win = n // s
        if n_win < 1:
            continue
        # Forward and backward partitions: the backward pass covers the tail
        # that integer division would otherwise throw away.
        segments = np.concatenate([
            y[: n_win * s].reshape(n_win, s),
            y[n - n_win * s:].reshape(n_win, s),
        ])
        t = np.arange(s, dtype=float)
        # polyfit vectorises over columns, so transpose: one column per window
        coeffs = np.polyfit(t, segments.T, order)
        trend = np.polyval(coeffs, t[:, None])
        resid = segments.T - trend
        fluct[i] = math.sqrt(float(np.mean(resid ** 2)))
    return _loglog_slope(scales.astype(float), fluct)


# --------------------------------------------------------------------------
# 4. Permutation entropy
# --------------------------------------------------------------------------

def permutation_entropy(
    x: Sequence[float],
    m: int = 4,
    tau: int = 1,
    normalize: bool = True,
) -> float:
    """Bandt & Pompe (2002) permutation entropy of the ordinal structure of ``x``.

    Bandt, C. & Pompe, B. (2002), "Permutation Entropy: A Natural Complexity
    Measure for Time Series", *Phys. Rev. Lett.* 88(17), 174102.

    Every embedding window ``(x_t, x_{t+tau}, ..., x_{t+(m-1)tau})`` is reduced
    to the permutation ``pi`` that sorts it. With ``p(pi)`` the relative
    frequency of each of the ``m!`` patterns::

        H = - sum_pi p(pi) * log p(pi)

    and, when ``normalize`` is True, ``H / log(m!)``, which lies in ``[0, 1]``.
    1.0 means all ordinal patterns are equally likely (maximally random
    ordering — what iid noise looks like); lower values mean deterministic
    ordinal structure. A clean oscillation scores far below 1 because only a
    handful of patterns ever occur.

    Ties are broken by index (numpy stable argsort), which is the usual
    convention and matters only for heavily discretised series; on tick-size
    quantised prices, prefer running this on returns.

    Practical caveat: real financial returns score ~0.99 at ``m=4``, i.e.
    almost indistinguishable from noise, so this statistic is much better at
    *rejecting* an instrument than at endorsing one. The estimate is also
    biased downward when the number of windows is small relative to ``m!``;
    aim for at least ``5 * m!`` windows (that is ``~120`` at ``m=4``,
    ``~3600`` at ``m=6``).
    """
    if m < 2:
        raise ValueError("m must be >= 2")
    if tau < 1:
        raise ValueError("tau must be >= 1")
    a = _clean(x, "x", minimum=m * tau + 1)
    n = a.size
    length = n - (m - 1) * tau
    if length < 2:
        raise ValueError(f"need at least {(m - 1) * tau + 2} observations for m={m}, tau={tau}")

    # (length, m) matrix of embedding windows, built by strided slicing
    windows = np.column_stack([a[i * tau: i * tau + length] for i in range(m)])
    order = np.argsort(windows, axis=1, kind="stable")
    # Encode each permutation as a base-m integer so np.unique can count them
    powers = m ** np.arange(m)
    codes = order @ powers
    _, counts = np.unique(codes, return_counts=True)
    p = counts / counts.sum()
    h = float(-(p * np.log(p)).sum())
    if not normalize:
        return h
    return h / math.log(math.factorial(m))


# --------------------------------------------------------------------------
# 5. Ljung-Box
# --------------------------------------------------------------------------

def _ljung_box(series: np.ndarray, lags: Iterable[int]) -> pd.DataFrame:
    # Imported lazily: statsmodels costs ~1s at import time and most callers
    # of this module only want the variance ratio.
    from statsmodels.stats.diagnostic import acorr_ljungbox  # type: ignore

    lag_list = [int(l) for l in lags]
    out = acorr_ljungbox(series, lags=lag_list, return_df=True)
    return pd.DataFrame({
        "lag": lag_list,
        "lb_stat": out["lb_stat"].to_numpy(dtype=float),
        "p_value": out["lb_pvalue"].to_numpy(dtype=float),
    })


def ljung_box_returns(
    returns: Sequence[float],
    lags: Iterable[int] = (5, 10, 20),
) -> pd.DataFrame:
    """Ljung-Box Q test for autocorrelation in the *returns* themselves.

    Ljung, G. M. & Box, G. E. P. (1978), "On a Measure of Lack of Fit in Time
    Series Models", *Biometrika* 65(2), 297-303. Thin wrapper around
    ``statsmodels.stats.diagnostic.acorr_ljungbox``::

        Q(h) = T (T + 2) * sum_{k=1..h} rho_k^2 / (T - k),   Q(h) ~ chi2(h)

    under the null of no autocorrelation up to lag ``h``. Rejection here is
    evidence that **direction** is serially predictable — the thing a
    technical strategy actually needs.

    Read this together with :func:`ljung_box_abs_returns`, and do not confuse
    the two. Volatility clustering makes the |r| test reject on essentially
    every liquid instrument ever traded; that says the *magnitude* of the next
    move is predictable, which is worth something to an options or sizing
    desk and worth **nothing** to a directional pattern strategy. Treating a
    rejection on |r| as evidence that price patterns work is the single most
    common error in this whole exercise.

    ``lags`` are cumulative horizons, so the rows are nested and their
    p-values are heavily dependent; do not treat them as independent tests.

    Returns a DataFrame with columns ``lag``, ``lb_stat``, ``p_value``.
    """
    r = _clean(returns, "returns", minimum=max(int(l) for l in lags) + 2)
    return _ljung_box(r, lags)


def ljung_box_abs_returns(
    returns: Sequence[float],
    lags: Iterable[int] = (5, 10, 20),
) -> pd.DataFrame:
    """Ljung-Box Q test on ``|r - mean(r)|`` — a volatility-clustering probe.

    Same statistic as :func:`ljung_box_returns`, applied to absolute demeaned
    returns, which is the standard cheap proxy for ARCH effects (Ding,
    Granger & Engle 1993 use the more general ``|r|^d`` family).

    **Rejection here is not evidence that direction is predictable.** It is
    nearly universal: absolute returns are autocorrelated for practically
    every traded instrument at every frequency. It is reported so that a
    non-rejection on :func:`ljung_box_returns` cannot be quietly swapped for a
    rejection here when someone wants a green light. If |r| rejects and r does
    not, the honest conclusion is "the volatility is forecastable, the
    direction is not", and a directional technical strategy has no edge to
    harvest.

    Returns a DataFrame with columns ``lag``, ``lb_stat``, ``p_value``.
    """
    r = _clean(returns, "returns", minimum=max(int(l) for l in lags) + 2)
    return _ljung_box(np.abs(r - r.mean()), lags)


# --------------------------------------------------------------------------
# 6. Runs test
# --------------------------------------------------------------------------

def runs_test(returns: Sequence[float]) -> dict:
    """Wald-Wolfowitz runs test on the sign sequence of ``returns``.

    Wald, A. & Wolfowitz, J. (1940), "On a Test Whether Two Samples are from
    the Same Population", *Annals of Mathematical Statistics* 11(2), 147-162.

    Zero returns are dropped (a flat bar carries no directional information).
    With ``n1`` positive and ``n2`` negative observations, ``n = n1 + n2`` and
    ``R`` the observed number of runs (maximal blocks of identical sign)::

        E[R]   = 2 * n1 * n2 / n + 1
        Var[R] = 2 * n1 * n2 * (2 * n1 * n2 - n) / (n^2 * (n - 1))
        z      = (R - E[R]) / sqrt(Var[R])

    ``z`` is asymptotically standard normal under the null that signs are iid.
    No continuity correction is applied — this is the large-sample form, and
    it is unreliable below roughly 30 observations of each sign.

    Interpretation: ``z < 0`` (too few runs) means signs cluster, i.e. positive
    serial dependence / trending; ``z > 0`` (too many runs) means signs
    alternate, i.e. mean reversion. The test only looks at signs, so it is
    blind to magnitude and is deliberately weak — it is a robustness check on
    the variance ratio, not a substitute for it.

    Returns a dict with ``z``, ``p_value`` (two-sided), ``n_runs``,
    ``expected_runs``, ``n_pos``, ``n_neg``.
    """
    r = _clean(returns, "returns", minimum=3)
    signs = np.sign(r)
    signs = signs[signs != 0]
    n1 = int((signs > 0).sum())
    n2 = int((signs < 0).sum())
    n = n1 + n2
    if n1 == 0 or n2 == 0 or n < 3:
        raise ValueError("runs test needs at least one positive and one negative return")

    n_runs = int(1 + np.count_nonzero(np.diff(signs)))
    expected = 2.0 * n1 * n2 / n + 1.0
    var = 2.0 * n1 * n2 * (2.0 * n1 * n2 - n) / (n ** 2 * (n - 1.0))
    if var <= 0:
        z = float("nan")
        p = float("nan")
    else:
        z = (n_runs - expected) / math.sqrt(var)
        p = float(2.0 * norm.sf(abs(z)))
    return {
        "z": float(z),
        "p_value": float(p),
        "n_runs": n_runs,
        "expected_runs": float(expected),
        "n_pos": n1,
        "n_neg": n2,
    }


# --------------------------------------------------------------------------
# 7. Aggregate screen
# --------------------------------------------------------------------------

def _log_returns(prices: Sequence[float]) -> np.ndarray:
    p = _clean(prices, "prices", minimum=64)
    if np.any(p <= 0):
        raise ValueError("prices must be strictly positive to take log returns")
    return np.diff(np.log(p))


def ta_suitability(
    prices: Sequence[float],
    qs: Iterable[int] = (2, 5, 10, 20),
    alpha: float = 0.05,
) -> dict:
    """Screen whether an instrument's price path is worth applying TA to.

    Runs the whole battery on ``prices`` (a strictly positive level series;
    log returns are taken internally) and returns::

        {'components': {...raw per-test results...},
         'score':      float in [0, 100],
         'verdict':    'suitable' | 'marginal' | 'unsuitable',
         'reason':     one-line explanation of the verdict,
         'caveats':    list[str]}

    What the score is, and what it is not
    -------------------------------------
    The 0-100 number is a **screening heuristic with no sampling
    distribution**. It is a weighted tally of how many diagnostics rejected
    their null, with weights (``VR_WEIGHT`` .. ``HURST_WEIGHT``, all module
    constants) chosen by judgement. There is no null distribution for it, no
    confidence interval, no p-value, and no theory saying 55 is the right
    cut-off. Two instruments scoring 40 and 60 have not been shown to differ.

    * **The component p-values are the real evidence.** The score exists to
      rank a watchlist for human attention, nothing more.
    * **The tests are not independent.** The variance ratio, the Ljung-Box on
      returns and the runs test all read the same first-order autocorrelation
      from the same sample; the VR rows across ``qs`` overlap by construction.
      The score is therefore **not** a multiple-testing correction, and adding
      more components would not make it one. If you need a corrected
      statement, apply Bonferroni / Benjamini-Hochberg to the component
      p-values yourself and quote that instead.
    * **A 'suitable' verdict is necessary, not sufficient.** It says the
      series is statistically distinguishable from a martingale on this
      sample. It does not say the dependence is stable out of sample, that it
      survives costs and slippage, that it is large enough to trade, or that
      any particular pattern captures it. Every one of those has killed more
      strategies than the martingale null ever did.
    * Run it on a *training* window and freeze the verdict before backtesting
      the window that follows. Screening and evaluating on the same sample is
      selection bias, and the score cannot detect that you did it.

    Scoring (all constants exported at module level so this is auditable):
    variance ratio contributes ``VR_WEIGHT`` scaled by the fraction of ``qs``
    rejecting at ``alpha``; Ljung-Box on returns contributes
    ``LJUNG_BOX_WEIGHT`` if any lag rejects; the runs test contributes
    ``RUNS_WEIGHT`` if it rejects; permutation entropy contributes
    ``ENTROPY_WEIGHT`` scaled linearly from ``ENTROPY_FLOOR`` down; the DFA
    exponent contributes ``HURST_WEIGHT`` scaled by ``|H - 0.5| / HURST_SPAN``.
    Ljung-Box on |r| is reported but deliberately scores **zero** — volatility
    clustering is not directional predictability.
    """
    r = _log_returns(prices)
    n = r.size

    lags = tuple(l for l in (5, 10, 20) if l < n - 1) or (min(5, n - 2),)
    usable_qs = tuple(int(q) for q in qs if 2 * int(q) <= n)
    if not usable_qs:
        raise ValueError(f"no usable q in {tuple(qs)} for a series of {n} returns")

    vr_profile = variance_ratio_profile(r, usable_qs)
    lb_ret = ljung_box_returns(r, lags)
    lb_abs = ljung_box_abs_returns(r, lags)
    runs = runs_test(r)
    pe = permutation_entropy(r, m=4, tau=1, normalize=True)

    log_prices = np.log(_clean(prices, "prices", minimum=64))
    try:
        h_rs = hurst_rs(log_prices)
    except ValueError:
        h_rs = float("nan")
    try:
        h_dfa = hurst_dfa(log_prices, order=1)
    except ValueError:
        h_dfa = float("nan")

    caveats: list[str] = [
        "The 0-100 score is a screening heuristic with no sampling distribution; "
        "the component p-values are the evidence.",
        "The component tests are not independent (they read the same "
        "autocorrelation from the same sample), so the score is not a "
        "multiple-testing correction.",
        "A 'suitable' verdict is necessary, not sufficient: it says the series is "
        "distinguishable from a martingale in-sample, not that a strategy will "
        "survive out-of-sample, costs or slippage.",
        "Screening and backtesting on the same window is selection bias; freeze "
        "this verdict on a training window before evaluating anything.",
    ]

    # --- component scores ---
    vr_p = vr_profile["p_value"].to_numpy(dtype=float)
    vr_reject_frac = float(np.mean(vr_p < alpha)) if vr_p.size else 0.0
    vr_score = VR_WEIGHT * vr_reject_frac

    lb_ret_min_p = float(np.nanmin(lb_ret["p_value"].to_numpy(dtype=float)))
    lb_score = LJUNG_BOX_WEIGHT if lb_ret_min_p < alpha else 0.0

    runs_score = RUNS_WEIGHT if (np.isfinite(runs["p_value"]) and runs["p_value"] < alpha) else 0.0

    pe_score = ENTROPY_WEIGHT * float(np.clip((ENTROPY_FLOOR - pe) / ENTROPY_SPAN, 0.0, 1.0))

    if np.isfinite(h_dfa):
        hurst_score = HURST_WEIGHT * float(np.clip(abs(h_dfa - 0.5) / HURST_SPAN, 0.0, 1.0))
    else:
        hurst_score = 0.0
        caveats.append("DFA exponent could not be estimated (series too short); "
                       "its component scored zero.")

    score = float(vr_score + lb_score + runs_score + pe_score + hurst_score)

    lb_abs_min_p = float(np.nanmin(lb_abs["p_value"].to_numpy(dtype=float)))
    if lb_abs_min_p < alpha and lb_ret_min_p >= alpha:
        caveats.append(
            "|r| is autocorrelated but r is not: volatility is forecastable, "
            "direction is not. This is the normal state of a liquid market and is "
            "no basis for a directional technical strategy."
        )
    if n < 1000:
        caveats.append(
            f"Only {n} return observations: the Hurst estimators are badly biased "
            "below ~1000 points and the asymptotic p-values are approximate."
        )

    if score >= SUITABLE_THRESHOLD:
        verdict = "suitable"
    elif score >= MARGINAL_THRESHOLD:
        verdict = "marginal"
    else:
        verdict = "unsuitable"

    n_vr_reject = int((vr_p < alpha).sum())
    reason = (
        f"score {score:.0f}/100: VR rejects at {n_vr_reject}/{len(usable_qs)} horizons, "
        f"Ljung-Box(r) min p={lb_ret_min_p:.3g}, runs p={runs['p_value']:.3g}, "
        f"perm-entropy={pe:.3f}, DFA H={h_dfa:.2f}"
    )

    return {
        "components": {
            "variance_ratio_profile": vr_profile,
            "ljung_box_returns": lb_ret,
            "ljung_box_abs_returns": lb_abs,
            "runs_test": runs,
            "permutation_entropy": float(pe),
            "hurst_rs": float(h_rs),
            "hurst_dfa": float(h_dfa),
            "n_returns": int(n),
            "alpha": float(alpha),
        },
        "component_scores": {
            "variance_ratio": float(vr_score),
            "ljung_box_returns": float(lb_score),
            "runs_test": float(runs_score),
            "permutation_entropy": float(pe_score),
            "hurst_dfa": float(hurst_score),
            "ljung_box_abs_returns": 0.0,   # reported, never scored — see docstring
        },
        "score": score,
        "verdict": verdict,
        "reason": reason,
        "caveats": caveats,
    }
