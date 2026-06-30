"""Probability of Backtest Overfitting (PBO) via combinatorially symmetric CV.

Bailey, Borwein, López de Prado & Zhu (2017). Pure numpy. Takes a matrix of
per-trial performance across CPCV paths and estimates how often the
in-sample-best configuration underperforms the median out-of-sample.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np


def pbo(performance: np.ndarray, n_splits: int = 10) -> float:
    """Estimate PBO.

    ``performance``: shape ``(T, N)`` — T time observations of a chosen metric
    (e.g. per-bar return contribution) for each of N candidate configs.
    Returns the probability in ``[0, 1]`` that the IS-optimal config is below
    the OOS median (high → the selection is overfit).
    """
    perf = np.asarray(performance, dtype=float)
    T, N = perf.shape
    if N < 2:
        raise ValueError("need at least 2 candidate configurations")
    blocks = np.array_split(np.arange(T), n_splits)
    logits = []
    half = n_splits // 2
    for combo in combinations(range(n_splits), half):
        is_rows = np.concatenate([blocks[b] for b in combo])
        oos_rows = np.concatenate(
            [blocks[b] for b in range(n_splits) if b not in combo]
        )
        is_perf = perf[is_rows].mean(axis=0)
        oos_perf = perf[oos_rows].mean(axis=0)
        best = int(np.argmax(is_perf))
        # rank of the IS-best config among OOS performances
        rank = (oos_perf <= oos_perf[best]).mean()
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        logits.append(np.log(rank / (1 - rank)))
    logits = np.asarray(logits)
    return float((logits <= 0).mean())
