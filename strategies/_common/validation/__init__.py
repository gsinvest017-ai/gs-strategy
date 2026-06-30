"""Backtest-overfitting validation statistics (lift-ready into gs-common).

Self-written replacement for the closed-source mlfinlab routines:
CPCV splits, Deflated/Probabilistic Sharpe, and PBO. Dependencies are limited
to numpy/scipy/pandas so this subpackage can later be lifted verbatim into
``gs_common.quant.validation`` (see docs/survey-quant-frontier-2026-06.md).
"""
from __future__ import annotations

from .cpcv import (
    combinatorial_purged_splits,
    n_cpcv_paths,
    purged_kfold_splits,
)
from .pbo import pbo
from .sharpe import (
    annualized_sharpe,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)

__all__ = [
    "purged_kfold_splits",
    "combinatorial_purged_splits",
    "n_cpcv_paths",
    "pbo",
    "annualized_sharpe",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
]
