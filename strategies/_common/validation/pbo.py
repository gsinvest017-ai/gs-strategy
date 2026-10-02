"""Probability of Backtest Overfitting (PBO) via combinatorially symmetric CV.

Bailey, Borwein, López de Prado & Zhu (2017). Pure numpy. Takes a matrix of
per-trial performance across time and estimates how often the in-sample-best
configuration lands below the out-of-sample median.

Scoring metric matters. The earlier version ranked configurations by their
*mean* return. When candidate configurations differ mainly in volatility
(equal- vs value-weighted, levered variants, 5 vs 10 quantiles), the mean is
roughly ``L_j * mu``: whenever the common drift ``mu`` is positive both in and
out of sample, the most volatile configuration wins both halves, the IS-best
rank is always at the top, and PBO collapses toward 0 -- regardless of whether
choosing among the configurations adds anything. Ranking by Sharpe removes the
leverage scale, which is what the original paper does.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np

_METRICS = ("sharpe", "mean")


def _score(perf: np.ndarray, rows: np.ndarray, metric: str) -> np.ndarray:
    block = perf[rows]
    mean = np.nanmean(block, axis=0)
    if metric == "mean":
        return mean
    sd = np.nanstd(block, axis=0, ddof=1)
    out = np.full(mean.shape, -np.inf)
    ok = np.isfinite(sd) & (sd > 0)
    out[ok] = mean[ok] / sd[ok]
    return out


def pbo(performance: np.ndarray, n_splits: int = 10, metric: str = "sharpe") -> float:
    """Estimate PBO.

    ``performance``: shape ``(T, N)`` -- T time observations of per-period
    returns for each of N candidate configs. Candidates should share one return
    type (do not mix long/short spreads with hedged long-only series).
    ``metric``: ``"sharpe"`` (default) or ``"mean"`` (legacy; biased toward
    high-volatility configurations, see module docstring).

    Returns the probability in ``[0, 1]`` that the IS-optimal config is at or
    below the OOS median (high -> the selection is overfit), or NaN when no
    split has a finite in-sample score.
    """
    if metric not in _METRICS:
        raise ValueError(f"metric must be one of {_METRICS}, got {metric!r}")
    perf = np.asarray(performance, dtype=float)
    T, N = perf.shape
    if N < 2:
        raise ValueError("need at least 2 candidate configurations")
    blocks = np.array_split(np.arange(T), n_splits)
    half = n_splits // 2
    logits = []
    for combo in combinations(range(n_splits), half):
        is_rows = np.concatenate([blocks[b] for b in combo])
        oos_rows = np.concatenate([blocks[b] for b in range(n_splits) if b not in combo])
        is_score = _score(perf, is_rows, metric)
        if not np.isfinite(is_score).any():
            continue
        oos_score = _score(perf, oos_rows, metric)
        best = int(np.nanargmax(np.where(np.isfinite(is_score), is_score, -np.inf)))
        # relative rank of the IS-best config among OOS scores
        rank = float((oos_score <= oos_score[best]).mean())
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))
    if not logits:
        return float("nan")
    return float((np.asarray(logits) <= 0).mean())
