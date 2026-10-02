"""Backtest-overfitting validation statistics (lift-ready into gs-common).

Self-written replacement for the closed-source mlfinlab routines:
CPCV splits, Deflated/Probabilistic Sharpe, and PBO. Dependencies are limited
to numpy/scipy/pandas so this subpackage can later be lifted verbatim into
``gs_common.quant.validation`` (see docs/survey-quant-frontier-2026-06.md).

Each leg covers a *different* failure mode and none substitutes for another:

``cpcv``        leakage from serially-overlapping labels
``sharpe``      estimation error on a single strategy's Sharpe (PSR / DSR)
``pbo``         probability the in-sample winner collapses out of sample
``online_fdr``  the multiple-testing correction for the case where variants
                arrive one at a time and N is *not* known in advance -- an
                offline correction cannot be applied there without using
                future information to set past thresholds (ADDIS)
``decision``    which test the ruleset mandates for a declared set of data
                properties, and whether a recorded verdict can be recomputed

``online_fdr`` keeps the numpy/scipy/pandas-only invariant by implementing
ADDIS here rather than depending on the ``online-fdr`` package; correctness is
held by a step-by-step cross-check against that package in the test suite,
which skips when it is not installed.
"""
from __future__ import annotations

from .cpcv import (
    combinatorial_purged_splits,
    n_cpcv_paths,
    purged_kfold_splits,
)
from .online_fdr import (
    AddisBudget,
    AddisStep,
    PValueProvenanceError,
    budget_from_ledger,
)
from .pbo import pbo
from .sharpe import (
    annualized_sharpe,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)

__all__ = [
    # cpcv
    "purged_kfold_splits",
    "combinatorial_purged_splits",
    "n_cpcv_paths",
    # pbo
    "pbo",
    # sharpe
    "annualized_sharpe",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    # online_fdr
    "AddisBudget",
    "AddisStep",
    "budget_from_ledger",
    "PValueProvenanceError",
]
