"""Refutation gate — the de-overfitting check.

Runs DoWhy's refuters (placebo treatment, random common cause, data subset) to
attack a claimed causal effect. A factor only passes if the estimated effect
*survives* refutation (collapses to ~0 under placebo, stays stable under random
common cause). Optional dependency; if DoWhy is absent we run two cheap
numpy-only analogues (placebo permutation + bootstrap subset stability).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass
class RefutationReport:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    detail: dict[str, float] = field(default_factory=dict)
    method: str = "fallback"


def refute_factor(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
    observed_effect: float,
    *,
    n_perm: int = 200,
    seed: int = 0,
) -> RefutationReport:
    """Try to refute ``observed_effect``. Returns a pass/fail report."""
    try:
        return _dowhy_refute(panel, treatment, outcome, confounders, observed_effect)
    except ImportError:
        return _fallback_refute(
            panel, treatment, outcome, confounders, observed_effect, n_perm, seed
        )


def _dowhy_refute(panel, treatment, outcome, confounders, observed_effect):
    from dowhy import CausalModel  # type: ignore

    model = CausalModel(
        data=panel.dropna(subset=[treatment, outcome, *confounders]),
        treatment=treatment,
        outcome=outcome,
        common_causes=list(confounders),
    )
    est = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(est, method_name="backdoor.linear_regression")
    checks, detail = {}, {}
    for name, kind in [
        ("placebo", "placebo_treatment_refuter"),
        ("random_cc", "random_common_cause"),
        ("subset", "data_subset_refuter"),
    ]:
        res = model.refute_estimate(est, estimate, method_name=kind)
        new = float(res.new_effect)
        detail[name] = new
        if name == "placebo":
            checks[name] = bool(abs(new) < abs(estimate.value) * 0.5)
        else:
            checks[name] = bool(abs(new - estimate.value) < abs(estimate.value) * 0.5)
    return RefutationReport(
        passed=all(checks.values()), checks=checks, detail=detail, method="dowhy"
    )


def _fallback_refute(panel, treatment, outcome, confounders, observed_effect, n_perm, seed):
    from .dml import estimate_factor_effect

    rng = np.random.default_rng(seed)
    df = panel[[outcome, treatment, *confounders]].dropna().reset_index(drop=True)

    # placebo: shuffle the treatment, the effect should vanish
    placebo_effects = []
    for _ in range(min(n_perm, 200)):
        shuffled = df.copy()
        shuffled[treatment] = rng.permutation(shuffled[treatment].to_numpy())
        placebo_effects.append(
            estimate_factor_effect(shuffled, treatment, outcome, confounders).coef
        )
    placebo_effects = np.asarray(placebo_effects)
    # one-sided p: how often placebo |effect| >= observed
    placebo_p = float((np.abs(placebo_effects) >= abs(observed_effect)).mean())

    # subset stability: re-estimate on 70% bootstraps, check sign stability
    signs = []
    for _ in range(50):
        idx = rng.choice(len(df), int(len(df) * 0.7), replace=False)
        signs.append(
            np.sign(
                estimate_factor_effect(
                    df.iloc[idx], treatment, outcome, confounders
                ).coef
            )
        )
    sign_stability = float((np.asarray(signs) == np.sign(observed_effect)).mean())

    checks = {
        "placebo": placebo_p < 0.05,          # observed effect beats placebo noise
        "subset_sign_stable": sign_stability > 0.9,
    }
    return RefutationReport(
        passed=all(checks.values()),
        checks=checks,
        detail={"placebo_p": placebo_p, "sign_stability": sign_stability},
        method="fallback",
    )
