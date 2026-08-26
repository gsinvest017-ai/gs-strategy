"""Backtest-overfitting-aware Sharpe statistics.

Pure ``numpy``/``scipy`` implementations of Bailey & López de Prado's
Probabilistic and Deflated Sharpe Ratios — the open replacement for the
now-closed-source ``mlfinlab`` versions.

Design rule (see survey-quant-frontier-2026-06.md / gs-common-lift report):
this module consumes only return arrays, imports nothing from zipline or
gs-strategy, and is therefore lift-ready into ``gs_common.quant.validation``.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np

try:
    from scipy.stats import norm  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "scipy is required for validation.sharpe: pip install scipy"
    ) from exc


def _moments(returns: Sequence[float]) -> tuple[np.ndarray, float, float, float, int]:
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    n = r.size
    if n < 3:
        raise ValueError("need at least 3 return observations")
    sr = r.mean() / r.std(ddof=1)
    # skew / kurtosis of the *returns*, used in the PSR variance term
    skew = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4)
    return r, float(sr), skew, kurt, n


def probabilistic_sharpe_ratio(
    returns: Sequence[float],
    sr_benchmark: float = 0.0,
) -> float:
    """P(true SR > benchmark SR) given the estimation error of the sample SR.

    All quantities are in the same (per-period) frequency as ``returns``.
    """
    _, sr, skew, kurt, n = _moments(returns)
    # variance of the SR estimator (Lo 2002, with non-normal correction)
    sr_std = math.sqrt((1 - skew * sr + (kurt - 1) / 4 * sr**2) / (n - 1))
    return float(norm.cdf((sr - sr_benchmark) / sr_std))


def deflated_sharpe_ratio(
    returns: Sequence[float],
    n_trials: int,
    sr_variance_across_trials: float | None = None,
    sr_benchmark: float | None = None,
) -> float:
    """Deflated Sharpe Ratio (DSR).

    Deflates the observed SR by the SR you'd expect from the *best* of
    ``n_trials`` independent backtests under the null of zero skill — the
    direct antidote to the model-zoo spray problem flagged in the survey.

    ``sr_variance_across_trials`` is Var[SR] across the trials you ran; if you
    don't have it, pass ``None`` and a conservative default of 1/(n-1) is used.
    """
    r, sr, skew, kurt, n = _moments(returns)
    if n_trials < 1:
        raise ValueError("n_trials must be >= 1")
    if sr_variance_across_trials is None:
        sr_variance_across_trials = 1.0 / (n - 1)
    if n_trials == 1:
        # Single trial: under the null of zero skill the expected maximum SR
        # over one draw is just E[SR] = 0, so there is nothing to deflate and
        # DSR collapses to PSR against a zero benchmark.
        #
        # This case MUST be special-cased. The Bailey & LdP closed form below
        # is an extreme-value approximation valid only for n_trials >= 2: at
        # n_trials == 1 we get e = 1, hence z1 = norm.ppf(0) = -inf, hence
        # expected_max_sr = -inf, hence PSR(benchmark=-inf) = 1.0 for *every*
        # return series. That silently turns DSR into a constant perfect
        # score — strictly worse than reporting nothing at all.
        expected_max_sr = 0.0
    else:
        # expected max SR among n_trials draws (Bailey & LdP 2014)
        euler_mascheroni = 0.5772156649015329
        e = 1.0 / n_trials
        z1 = norm.ppf(1 - e)
        z2 = norm.ppf(1 - e * math.exp(-1))
        expected_max_sr = math.sqrt(sr_variance_across_trials) * (
            (1 - euler_mascheroni) * z1 + euler_mascheroni * z2
        )
    if sr_benchmark is None:
        sr_benchmark = expected_max_sr
    return probabilistic_sharpe_ratio(r, sr_benchmark=sr_benchmark)


def annualized_sharpe(returns: Sequence[float], periods_per_year: int = 252) -> float:
    """Convenience: classic annualized SR (no overfitting correction)."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))
