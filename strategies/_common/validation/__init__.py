"""Backtest-overfitting validation statistics (lift-ready into gs-common).

Self-written replacement for the closed-source mlfinlab routines:
CPCV splits, Deflated/Probabilistic Sharpe, and PBO. Dependencies are limited
to numpy/scipy/pandas so this subpackage can later be lifted verbatim into
``gs_common.quant.validation`` (see docs/survey-quant-frontier-2026-06.md).

Each leg covers a *different* failure mode and none substitutes for another
(see docs/math-spec-pv-technical-analysis.md §6.4):

``cpcv``           leakage from serially-overlapping labels
``sharpe``         estimation error on a single strategy's Sharpe (PSR / DSR)
``pbo``            probability the in-sample winner collapses out of sample
``reality_check``  data snooping across the M strategies you actually tried
                   (White's Reality Check, Hansen's SPA, Romano-Wolf StepM)
``tradability``    whether the instrument carries exploitable serial structure
                   at all -- the check that belongs *before* the others
``online_fdr``     the multiple-testing correction for the case where variants
                   arrive one at a time and N is *not* known in advance -- an
                   offline correction cannot be applied there without using
                   future information to set past thresholds (ADDIS)
``decision``       which test the ruleset mandates for a declared set of data
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
from .reality_check import (
    circular_block_bootstrap_indices,
    hansens_spa,
    snooping_report,
    stationary_bootstrap_indices,
    stepwise_multiple_testing,
    whites_reality_check,
)
from .sharpe import (
    annualized_sharpe,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)
from .tradability import (
    hurst_dfa,
    hurst_rs,
    ljung_box_abs_returns,
    ljung_box_returns,
    permutation_entropy,
    runs_test,
    ta_suitability,
    variance_ratio,
    variance_ratio_profile,
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
    # reality_check
    "stationary_bootstrap_indices",
    "circular_block_bootstrap_indices",
    "whites_reality_check",
    "hansens_spa",
    "stepwise_multiple_testing",
    "snooping_report",
    # tradability
    "variance_ratio",
    "variance_ratio_profile",
    "hurst_rs",
    "hurst_dfa",
    "permutation_entropy",
    "ljung_box_returns",
    "ljung_box_abs_returns",
    "runs_test",
    "ta_suitability",
    # online_fdr
    "AddisBudget",
    "AddisStep",
    "budget_from_ledger",
    "PValueProvenanceError",
]
