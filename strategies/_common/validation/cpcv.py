"""Combinatorial Purged Cross-Validation (CPCV) splits.

López de Prado's purged + embargoed CV for time-series backtests, pure
numpy/pandas. Replaces the closed-source ``mlfinlab`` CPCV. Consumes only an
index of observation times; knows nothing about zipline.

When CPCV is *not* evidence: a strategy with no parameters fitted on the
training groups never uses them, so a "test path" Sharpe is just the Sharpe of
the k test groups. The C(N, k) splits share groups -- each group sits in
C(N-1, k-1) of them -- so the median over splits is close to the full-sample
Sharpe and the spread across splits understates sampling error. For such
strategies report :func:`block_sharpes` (non-overlapping blocks) instead.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Iterator, Sequence

import numpy as np


def _as_int_index(n_samples: int) -> np.ndarray:
    return np.arange(n_samples)


def purged_kfold_splits(
    n_samples: int,
    n_splits: int = 5,
    embargo_pct: float = 0.01,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Plain purged K-Fold (single test group per fold) with embargo.

    Yields ``(train_idx, test_idx)``. The ``embargo_pct`` fraction of samples
    immediately after each test block is dropped from train to kill leakage
    from serially-correlated labels.
    """
    idx = _as_int_index(n_samples)
    fold_bounds = np.array_split(idx, n_splits)
    embargo = int(n_samples * embargo_pct)
    for test in fold_bounds:
        t0, t1 = test[0], test[-1]
        train_mask = np.ones(n_samples, dtype=bool)
        # purge the test block and an embargo tail
        train_mask[t0 : t1 + 1 + embargo] = False
        # also purge an embargo *before* the block (bidirectional safety)
        train_mask[max(0, t0 - embargo) : t0] = False
        yield idx[train_mask], test


def combinatorial_purged_splits(
    n_samples: int,
    n_groups: int = 6,
    n_test_groups: int = 2,
    embargo_pct: float = 0.01,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Full CPCV: choose ``n_test_groups`` of ``n_groups`` as the test set.

    Produces ``C(n_groups, n_test_groups)`` train/test paths, the basis for a
    distribution of OOS Sharpes (feed into PBO / DSR) rather than a single
    point estimate. Only meaningful when something is *fitted or selected* on
    the training indices; see the module docstring.
    """
    if n_test_groups >= n_groups:
        raise ValueError("n_test_groups must be < n_groups")
    idx = _as_int_index(n_samples)
    groups = np.array_split(idx, n_groups)
    embargo = int(n_samples * embargo_pct)
    for combo in combinations(range(n_groups), n_test_groups):
        test_idx = np.concatenate([groups[g] for g in combo])
        train_mask = np.ones(n_samples, dtype=bool)
        for g in combo:
            blk = groups[g]
            b0, b1 = blk[0], blk[-1]
            train_mask[max(0, b0 - embargo) : b1 + 1 + embargo] = False
        yield idx[train_mask], np.sort(test_idx)


def n_cpcv_paths(n_groups: int, n_test_groups: int) -> int:
    from math import comb

    return comb(n_groups, n_test_groups)


def block_sharpes(
    returns: Sequence[float],
    n_blocks: int = 6,
    periods_per_year: int | None = None,
) -> list[float]:
    """Sharpe ratio of each contiguous, non-overlapping block of ``returns``.

    Use this instead of CPCV test-path Sharpes for parameter-free strategies.
    A block with fewer than two observations or zero variance yields NaN.
    Pass ``periods_per_year`` to annualise.
    """
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    out: list[float] = []
    for blk in np.array_split(np.arange(r.size), n_blocks):
        x = r[blk]
        sd = float(x.std(ddof=1)) if x.size > 1 else 0.0
        s = float(x.mean() / sd) if sd > 0 else float("nan")
        if periods_per_year and math.isfinite(s):
            s *= math.sqrt(periods_per_year)
        out.append(s)
    return out
