"""Causal factor de-overfitting loop (survey gap #1).

Cross-fitted partially linear DML with period-clustered inference, a
per-period (Fama-MacBeth) effect, and disjoint time-block sign checks. Heavy
libraries are optional: scikit-learn for nuisance learners (OLS fallback),
causal-learn for a descriptive PC graph, DoWhy for auxiliary refuters. Pure
pandas in / verdict out -- no zipline coupling.
"""
from __future__ import annotations

from .dag import dag_diagnostics, discover_dag, select_confounders
from .dml import DMLResult, PeriodEffect, estimate_effect_by_period, estimate_factor_effect
from .pipeline import CausalVerdict, causal_factor_verdict, format_verdict
from .refute import RefutationReport, dowhy_auxiliary, refute_factor

__all__ = [
    "estimate_factor_effect",
    "estimate_effect_by_period",
    "DMLResult",
    "PeriodEffect",
    "discover_dag",
    "select_confounders",
    "dag_diagnostics",
    "refute_factor",
    "dowhy_auxiliary",
    "RefutationReport",
    "causal_factor_verdict",
    "CausalVerdict",
    "format_verdict",
]
