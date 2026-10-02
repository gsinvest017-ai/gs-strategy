"""Stability checks that can actually fail on a spurious panel effect.

The earlier gate used DoWhy's placebo-treatment, random-common-cause and
data-subset refuters. None of them has power against the failure that matters
on factor panels (a treatment that co-moves with returns through a common
period/industry shock):

* placebo: permuting D destroys *any* D-Y link, spurious or causal, so the
  placebo estimate is ~0 in expectation under every data-generating process.
  "Placebo effect < half the original" holds whenever the original estimate is
  a few standard errors from 0 -- which the inflated i.i.d. t-stat guarantees.
* random common cause: an independent W is orthogonal to D and Y, so by
  Frisch-Waugh-Lovell the estimate moves by O_p(1/sqrt(n)); it always passes.
* data subset: an 80% random row subset estimates the same probability limit;
  the change is O_p(sqrt(0.2/n)) and falls below half the estimate whenever
  the i.i.d. t exceeds ~4 -- again implied by the inflated t-stat.

All three reuse the i.i.d. row structure, so they are functions of the same
biased statistic they are meant to audit. They remain available through
:func:`dowhy_auxiliary` for descriptive output only.

The replacement splits the sample into contiguous, **disjoint** time blocks and
re-estimates the effect inside each block. A spurious common-shock effect has
block signs close to coin flips; a real effect keeps its sign in most blocks.
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
    method: str = "time_block_sign"


def _partial_slope(df: pd.DataFrame, treatment: str, outcome: str, confounders: Sequence[str]) -> float:
    Z = np.column_stack([np.ones(len(df)), df[list(confounders)].to_numpy(dtype=float).reshape(len(df), -1)])
    Q, _ = np.linalg.qr(Z)
    y = df[outcome].to_numpy(dtype=float)
    d = df[treatment].to_numpy(dtype=float)
    ry = y - Q @ (Q.T @ y)
    rd = d - Q @ (Q.T @ d)
    denom = float(rd @ rd)
    return float(rd @ ry) / denom if denom > 1e-12 else float("nan")


def refute_factor(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
    observed_effect: float,
    *,
    time_col: str | None = None,
    n_blocks: int = 10,
    min_sign_share: float = 0.7,
    n_boot: int = 50,
    seed: int = 0,
) -> RefutationReport:
    """Check that the sign of ``observed_effect`` is stable.

    With ``time_col`` (recommended): estimate a linear partialling-out slope in
    each of ``n_blocks`` contiguous, disjoint time blocks and require at least
    ``min_sign_share`` of them to share the observed sign.

    Without ``time_col``: fall back to 70% random row subsets (``n_boot``
    draws) and require 90% sign agreement. This cannot detect within-period
    dependence and is flagged with ``method="iid_row_subset"``.
    """
    sign = np.sign(observed_effect)
    cols = [outcome, treatment, *confounders] + ([time_col] if time_col else [])
    df = panel[cols].dropna().reset_index(drop=True)

    if time_col is not None:
        periods = np.sort(pd.unique(df[time_col]))
        n_b = int(min(n_blocks, max(2, periods.size // 6)))
        slopes = []
        for blk in np.array_split(periods, n_b):
            sub = df[df[time_col].isin(blk)]
            if len(sub) > len(confounders) + 3:
                slopes.append(_partial_slope(sub, treatment, outcome, confounders))
        slopes = np.asarray([s for s in slopes if np.isfinite(s)])
        share = float((np.sign(slopes) == sign).mean()) if slopes.size and sign != 0 else 0.0
        ok = share >= min_sign_share
        return RefutationReport(
            passed=bool(ok),
            checks={"time_block_sign": bool(ok)},
            detail={"block_sign_share": share, "n_blocks": float(slopes.size)},
            method="time_block_sign",
        )

    rng = np.random.default_rng(seed)
    signs = []
    for _ in range(n_boot):
        idx = rng.choice(len(df), int(len(df) * 0.7), replace=False)
        signs.append(np.sign(_partial_slope(df.iloc[idx], treatment, outcome, confounders)))
    stability = float((np.asarray(signs) == sign).mean()) if sign != 0 else 0.0
    ok = stability > 0.9
    return RefutationReport(
        passed=bool(ok),
        checks={"iid_subset_sign_stable": bool(ok)},
        detail={"sign_stability": stability},
        method="iid_row_subset",
    )


def dowhy_auxiliary(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
) -> dict | None:
    """DoWhy's three refuters, for descriptive output only (never a gate).

    Returns None if DoWhy is not installed.
    """
    try:
        from dowhy import CausalModel  # type: ignore
    except ImportError:
        return None
    model = CausalModel(
        data=panel.dropna(subset=[treatment, outcome, *confounders]),
        treatment=treatment,
        outcome=outcome,
        common_causes=list(confounders),
    )
    est = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(est, method_name="backdoor.linear_regression")
    out = {"estimate": float(estimate.value)}
    for name, kind in [
        ("placebo", "placebo_treatment_refuter"),
        ("random_cc", "random_common_cause"),
        ("subset", "data_subset_refuter"),
    ]:
        out[name] = float(model.refute_estimate(est, estimate, method_name=kind).new_effect)
    return out
