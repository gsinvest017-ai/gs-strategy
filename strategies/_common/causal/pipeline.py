"""Causal factor de-overfitting loop.

    factor panel -> full pre-registered control set (PC graph only as a diagnostic)
                 -> cross-fitted PLR effect, period-clustered SE
                 -> per-period (Fama-MacBeth) effect, Newey-West t
                 -> disjoint time-block sign check
                 -> verdict PASS / CONDITIONAL / FAIL

Significance requires BOTH the period-clustered DML p-value and the per-period
NW t to clear the threshold with the same sign. The first allows arbitrary
correlation within a period; the second collapses each period to one number
and handles serial correlation. On synthetic panels with industry x period
noise the old loop (i.i.d. SE, PC-narrowed controls, DoWhy refuters) passed
pure-noise factors far above the nominal 5%; see
tests/test_causal_calibration.py for the calibration this version must keep.

Consumes a pandas panel only -- no zipline import -- keeping it lift-ready.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import stats

from .dag import dag_diagnostics, select_confounders
from .dml import DMLResult, PeriodEffect, estimate_effect_by_period, estimate_factor_effect
from .refute import RefutationReport, refute_factor


@dataclass
class CausalVerdict:
    factor: str
    verdict: str                       # "PASS" | "CONDITIONAL" | "FAIL"
    effect: DMLResult
    refutation: RefutationReport
    confounders: list[str]
    period_effect: PeriodEffect | None = None
    dag: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def causal_factor_verdict(
    panel: pd.DataFrame,
    factor: str,
    forward_return: str,
    candidate_confounders: Sequence[str],
    *,
    time_col: str | None = None,
    discover: bool = False,
    learner: str = "rf",
    n_folds: int = 5,
    alpha: float = 0.05,
    random_state: int = 0,
) -> CausalVerdict:
    """Run the loop for one factor and return a PASS/CONDITIONAL/FAIL verdict.

    ``time_col``: period column. Required for a PASS on any panel where rows
    share periods; without it the standard errors assume independent rows and
    the verdict is capped at CONDITIONAL.
    ``discover``: also run the PC graph and attach it as ``dag`` (never changes
    the control set).

    PASS         = clustered DML p < alpha AND per-period |NW t| clears the
                   t critical value with the same sign AND time-block signs agree.
    CONDITIONAL  = significant but the block sign check fails, or no time_col.
    FAIL         = not significant under either test.
    """
    notes: list[str] = []
    confounders = select_confounders(panel, factor, forward_return, candidate_confounders)
    dag = dag_diagnostics(panel, factor, forward_return, confounders) if discover else {}
    if dag.get("available") and not dag.get("treatment_outcome_adjacent"):
        notes.append("PC graph has no factor-return edge (diagnostic only; PC assumes i.i.d. rows)")

    effect = estimate_factor_effect(
        panel, factor, forward_return, confounders,
        cluster=time_col, learner=learner, n_folds=n_folds, random_state=random_state,
    )
    if effect.method.startswith("plr_crossfit_linear_fallback"):
        notes.append("scikit-learn absent -> OLS nuisances used")

    period: PeriodEffect | None = None
    if time_col is not None:
        period = estimate_effect_by_period(panel, factor, forward_return, confounders, time_col=time_col)
    else:
        notes.append("no time_col: SEs assume independent rows; on stock x period panels p-values are "
                     "too small, so the verdict is capped at CONDITIONAL")

    refutation = refute_factor(
        panel, factor, forward_return, confounders, effect.coef,
        time_col=time_col, seed=random_state,
    )

    significant = effect.pvalue < alpha
    if not significant:
        notes.append(f"effect not significant (p={effect.pvalue:.3f}, {effect.method})")
    if period is not None:
        crit = float(stats.t.ppf(1 - alpha / 2, period.n_periods - 1))
        same_sign = np.sign(period.mean_coef) == np.sign(effect.coef)
        if abs(period.t_nw) < crit or not same_sign:
            significant = False
            notes.append(f"per-period effect not significant (NW t={period.t_nw:.2f}, need |t|>={crit:.2f}, "
                         f"same sign={bool(same_sign)})")

    if not significant:
        verdict = "FAIL"
    elif time_col is None:
        verdict = "CONDITIONAL"
    elif refutation.passed:
        verdict = "PASS"
    else:
        verdict = "CONDITIONAL"
        failed = [k for k, v in refutation.checks.items() if not v]
        notes.append(f"stability checks failed: {failed}")

    return CausalVerdict(
        factor=factor, verdict=verdict, effect=effect, refutation=refutation,
        confounders=confounders, period_effect=period, dag=dag, notes=notes,
    )


def format_verdict(v: CausalVerdict) -> str:
    e = v.effect
    lines = [
        f"[{v.verdict}] factor={v.factor}",
        f"  effect={e.coef:+.4g}  CI=({e.ci_low:+.4g}, {e.ci_high:+.4g})  p={e.pvalue:.3g}  n={e.n_obs}  ({e.method})",
        f"  iid p={e.pvalue_iid:.3g}  clusters={e.n_clusters}  design effect={e.design_effect:.2f}",
    ]
    if v.period_effect is not None:
        p = v.period_effect
        lines.append(f"  per-period: mean={p.mean_coef:+.4g}  NW t={p.t_nw:.2f}  periods={p.n_periods}  "
                     f"share>0={p.share_positive:.2f}")
    lines += [
        f"  stability={v.refutation.checks} {v.refutation.detail}  ({v.refutation.method})",
        f"  confounders={v.confounders}",
    ]
    lines += [f"  note: {n}" for n in v.notes]
    return "\n".join(lines)
