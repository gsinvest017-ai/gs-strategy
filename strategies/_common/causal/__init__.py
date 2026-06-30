"""Causal factor de-overfitting loop (survey gap #1).

Adopts DoubleML + causal-learn + DoWhy where installed, degrades to numpy/scipy
fallbacks otherwise, so the loop is runnable today. Pure pandas in / verdict
out — no zipline coupling (kept lift-ready per the gs-common-lift report; would
move to gs-quant-common, not gs-common's infra core).
"""
from __future__ import annotations

from .dag import discover_dag, select_confounders
from .dml import DMLResult, estimate_factor_effect
from .pipeline import CausalVerdict, causal_factor_verdict, format_verdict
from .refute import RefutationReport, refute_factor

__all__ = [
    "estimate_factor_effect",
    "DMLResult",
    "discover_dag",
    "select_confounders",
    "refute_factor",
    "RefutationReport",
    "causal_factor_verdict",
    "CausalVerdict",
    "format_verdict",
]
