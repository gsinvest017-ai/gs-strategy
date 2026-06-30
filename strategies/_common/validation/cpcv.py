"""Combinatorial Purged Cross-Validation (CPCV) splits.

López de Prado's purged + embargoed CV for time-series backtests, pure
numpy/pandas. Replaces the closed-source ``mlfinlab`` CPCV. Consumes only an
index of observation times; knows nothing about zipline.
"""
from __future__ import annotations

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
    point estimate.
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
