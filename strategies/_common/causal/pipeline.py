"""Causal factor de-overfitting loop.

Orchestrates the gap-#1 glue identified in the survey:

    factor panel -> (causal-learn) discover DAG / pick confounders
                 -> (DoubleML)    estimate causal effect + CI
                 -> (DoWhy)       refute (placebo / random-cc / subset)
                 -> verdict       PASS / CONDITIONAL / FAIL

Every heavy library is optional; with none installed the loop still runs end to
end on the numpy/scipy fallbacks, so it is wired and testable today. Consumes a
pandas factor panel only — no zipline import — keeping it lift-ready.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import pandas as pd

from .dag import select_confounders
from .dml import DMLResult, estimate_factor_effect
from .refute import RefutationReport, refute_factor


@dataclass
class CausalVerdict:
    factor: str
    verdict: str                       # "PASS" | "CONDITIONAL" | "FAIL"
    effect: DMLResult
    refutation: RefutationReport
    confounders: list[str]
    notes: list[str] = field(default_factory=list)


def causal_factor_verdict(
    panel: pd.DataFrame,
    factor: str,
    forward_return: str,
    candidate_confounders: Sequence[str],
    *,
    discover: bool = True,
) -> CausalVerdict:
    """Run the full loop for one factor and return a PASS/CONDITIONAL/FAIL verdict.

    PASS         = significant causal effect that survives refutation.
    CONDITIONAL  = significant but refutation is shaky (treat with caution).
    FAIL         = not significant, or effect vanishes / flips under refutation.
    """
    notes: list[str] = []

    confounders = (
        select_confounders(panel, factor, forward_return, candidate_confounders)
        if discover
        else list(candidate_confounders)
    )
    if set(confounders) != set(candidate_confounders):
        notes.append(f"DAG narrowed confounders to {confounders}")

    effect = estimate_factor_effect(panel, factor, forward_return, confounders)
    if effect.method == "partial_corr_fallback":
        notes.append("doubleml absent -> linear FWL fallback used")

    refutation = refute_factor(
        panel, factor, forward_return, confounders, effect.coef
    )
    if refutation.method == "fallback":
        notes.append("dowhy absent -> permutation/bootstrap refutation used")

    if not effect.significant:
        verdict = "FAIL"
        notes.append(f"effect not significant (p={effect.pvalue:.3f})")
    elif refutation.passed:
        verdict = "PASS"
    else:
        failed = [k for k, v in refutation.checks.items() if not v]
        verdict = "CONDITIONAL"
        notes.append(f"refutation checks failed: {failed}")

    return CausalVerdict(
        factor=factor,
        verdict=verdict,
        effect=effect,
        refutation=refutation,
        confounders=confounders,
        notes=notes,
    )


def format_verdict(v: CausalVerdict) -> str:
    lines = [
        f"[{v.verdict}] factor={v.factor}",
        f"  effect={v.effect.coef:+.4g}  CI=({v.effect.ci_low:+.4g},"
        f" {v.effect.ci_high:+.4g})  p={v.effect.pvalue:.3f}  n={v.effect.n_obs}"
        f"  ({v.effect.method})",
        f"  refutation={v.refutation.checks}  ({v.refutation.method})",
        f"  confounders={v.confounders}",
    ]
    lines += [f"  note: {n}" for n in v.notes]
    return "\n".join(lines)
