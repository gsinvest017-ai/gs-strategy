"""Double Machine Learning factor-effect estimation.

Thin wrapper over the ``DoubleML`` package (Chernozhukov et al. 2018). Estimates
the causal effect of a *factor* (treatment) on *forward return* (outcome) while
partialling out confounders Z with ML nuisance learners.

Heavy deps (doubleml, scikit-learn) are imported lazily so the rest of the
package — and the numpy-only fallback in :mod:`pipeline` — work without them.
Consumes a plain pandas DataFrame; no zipline coupling.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd


@dataclass
class DMLResult:
    coef: float          # estimated causal effect of factor on forward return
    se: float            # standard error
    pvalue: float
    ci_low: float
    ci_high: float
    n_obs: int
    method: str          # "doubleml" or "partial_corr_fallback"

    @property
    def significant(self) -> bool:
        return self.pvalue < 0.05


def estimate_factor_effect(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
    *,
    learner: str = "rf",
    n_folds: int = 5,
) -> DMLResult:
    """Estimate the partial linear DML effect of ``treatment`` on ``outcome``.

    ``panel`` rows are observations (e.g. (date, instrument)); columns include
    the factor value, the forward return, and confounder series. Falls back to
    a residual-on-residual partial-correlation OLS if doubleml is unavailable
    (same identification idea, linear nuisances), clearly flagged in ``method``.
    """
    cols = [outcome, treatment, *confounders]
    df = panel[cols].dropna()
    if len(df) < 50:
        raise ValueError(f"too few rows after dropna: {len(df)}")

    try:
        return _doubleml_effect(df, treatment, outcome, confounders, learner, n_folds)
    except ImportError:
        return _partial_corr_effect(df, treatment, outcome, confounders)


def _doubleml_effect(df, treatment, outcome, confounders, learner, n_folds) -> DMLResult:
    import doubleml as dml  # type: ignore
    from sklearn.ensemble import (  # type: ignore
        RandomForestRegressor,
    )
    from sklearn.linear_model import LassoCV  # type: ignore

    ml = (
        RandomForestRegressor(n_estimators=200, max_depth=5, n_jobs=-1)
        if learner == "rf"
        else LassoCV()
    )
    dml_data = dml.DoubleMLData(
        df, y_col=outcome, d_cols=treatment, x_cols=list(confounders)
    )
    plr = dml.DoubleMLPLR(dml_data, ml_l=ml, ml_m=ml, n_folds=n_folds)
    plr.fit()
    ci = plr.confint().iloc[0]
    return DMLResult(
        coef=float(plr.coef[0]),
        se=float(plr.se[0]),
        pvalue=float(plr.pval[0]),
        ci_low=float(ci.iloc[0]),
        ci_high=float(ci.iloc[1]),
        n_obs=len(df),
        method="doubleml",
    )


def _partial_corr_effect(df, treatment, outcome, confounders) -> DMLResult:
    """numpy-only Frisch–Waugh–Lovell fallback: regress y and d on Z, then
    OLS of the residuals. Same 'control for confounders' identification, linear.
    """
    from scipy import stats  # scipy is already a validation dep

    Z = np.column_stack([np.ones(len(df)), df[list(confounders)].to_numpy()])
    y = df[outcome].to_numpy()
    d = df[treatment].to_numpy()

    def _resid(target):
        beta, *_ = np.linalg.lstsq(Z, target, rcond=None)
        return target - Z @ beta

    ry, rd = _resid(y), _resid(d)
    n = len(df)
    slope = float((rd @ ry) / (rd @ rd))
    resid = ry - slope * rd
    dof = n - len(confounders) - 2
    se = float(np.sqrt((resid @ resid) / dof / (rd @ rd)))
    t = slope / se if se > 0 else 0.0
    pval = float(2 * (1 - stats.t.cdf(abs(t), dof)))
    crit = stats.t.ppf(0.975, dof)
    return DMLResult(
        coef=slope,
        se=se,
        pvalue=pval,
        ci_low=slope - crit * se,
        ci_high=slope + crit * se,
        n_obs=n,
        method="partial_corr_fallback",
    )
