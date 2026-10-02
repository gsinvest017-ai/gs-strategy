"""Double/debiased ML factor-effect estimation for stock x period panels.

Partially linear model (Chernozhukov et al. 2018, partialling-out score)::

    Y = theta * D + g(X) + U,      D = m(X) + V
    y~ = Y - l^(X),  d~ = D - m^(X)    (cross-fitted nuisance predictions)
    theta^ = sum(d~ y~) / sum(d~^2),   psi_i = d~_i (y~_i - theta^ d~_i)

Why this is hand-rolled rather than a thin DoubleMLPLR wrapper: factor panels
need (a) cross-fitting folds that keep whole periods together and (b) a
variance estimator that allows the scores of stocks in the same period to be
correlated. The i.i.d. variance ``mean(psi^2) / (n J^2)`` treats every row as
independent. With a common period or industry-period shock in both D and U the
true variance is larger by the design effect
``1 + (m - 1) * rho_d * rho_u`` (m = rows per cluster, rho = intraclass
correlations), so the i.i.d. t-stat is inflated by its square root. On real
Taiwan equity panels the ratio of i.i.d. to month-clustered standard errors
was 1.9-2.3x, and pure-noise factors were "significant" 33-63% of the time.

Pass ``cluster=<period column>`` whenever rows share periods. For a
Fama-MacBeth-style check that is robust to any within-period dependence, see
:func:`estimate_effect_by_period`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class DMLResult:
    coef: float          # estimated effect of factor on forward return
    se: float            # standard error used for inference (cluster-robust if clustered)
    pvalue: float
    ci_low: float
    ci_high: float
    n_obs: int
    method: str
    se_iid: float = float("nan")
    pvalue_iid: float = float("nan")
    n_clusters: int | None = None
    design_effect: float = float("nan")   # (se / se_iid)^2

    @property
    def significant(self) -> bool:
        return self.pvalue < 0.05


@dataclass
class PeriodEffect:
    mean_coef: float
    t_nw: float
    pvalue: float
    n_periods: int
    share_positive: float
    nw_lags: int
    coefs: pd.Series = field(repr=False)


def _make_learner(kind: str, random_state: int):
    """Return an unfitted regressor, or None for closed-form OLS."""
    if kind == "linear":
        return None
    try:
        from sklearn.ensemble import RandomForestRegressor  # type: ignore
        from sklearn.linear_model import LassoCV  # type: ignore
    except ImportError:
        return None
    if kind == "rf":
        return RandomForestRegressor(
            n_estimators=200, max_depth=5, min_samples_leaf=50,
            n_jobs=-1, random_state=random_state,
        )
    if kind == "lasso":
        return LassoCV(cv=3, random_state=random_state)
    raise ValueError(f"unknown learner {kind!r}; use 'rf', 'lasso' or 'linear'")


def _ols_fit_predict(Z_tr: np.ndarray, y_tr: np.ndarray, Z_te: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(Z_tr)), Z_tr])
    B = np.column_stack([np.ones(len(Z_te)), Z_te])
    beta, *_ = np.linalg.lstsq(A, y_tr, rcond=None)
    return B @ beta


def _fold_ids(n: int, n_folds: int, groups: np.ndarray | None, random_state: int) -> np.ndarray:
    rng = np.random.default_rng(random_state)
    if groups is None:
        ids = np.empty(n, dtype=int)
        ids[rng.permutation(n)] = np.arange(n) % n_folds
        return ids
    codes, uniques = pd.factorize(pd.Series(groups))
    fold_of_group = np.empty(len(uniques), dtype=int)
    fold_of_group[rng.permutation(len(uniques))] = np.arange(len(uniques)) % n_folds
    return fold_of_group[codes]


def _crossfit_residuals(Y, D, Z, fold_ids, n_folds, learner, random_state):
    ry = np.empty_like(Y)
    rd = np.empty_like(D)
    for k in range(n_folds):
        te = fold_ids == k
        tr = ~te
        for target, out in ((Y, ry), (D, rd)):
            model = _make_learner(learner, random_state) if Z.shape[1] else None
            if model is None:
                pred = _ols_fit_predict(Z[tr], target[tr], Z[te])
            else:
                model.fit(Z[tr], target[tr])
                pred = model.predict(Z[te])
            out[te] = target[te] - pred
    return ry, rd


def estimate_factor_effect(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
    *,
    cluster: str | None = None,
    learner: str = "rf",
    n_folds: int = 5,
    random_state: int = 0,
) -> DMLResult:
    """Cross-fitted partially linear DML effect of ``treatment`` on ``outcome``.

    ``cluster``: column identifying groups whose rows may be correlated
    (normally the period). When given, folds keep clusters together and
    inference uses the cluster-robust variance with G - 1 degrees of freedom.
    ``learner``: ``"rf"`` (default), ``"lasso"`` or ``"linear"``; falls back to
    OLS nuisances if scikit-learn is missing (flagged in ``method``).
    """
    cols = [outcome, treatment, *confounders] + ([cluster] if cluster else [])
    df = panel[cols].dropna()
    if len(df) < 50:
        raise ValueError(f"too few rows after dropna: {len(df)}")
    Y = df[outcome].to_numpy(dtype=float)
    D = df[treatment].to_numpy(dtype=float)
    Z = df[list(confounders)].to_numpy(dtype=float).reshape(len(df), -1)
    groups = df[cluster].to_numpy() if cluster else None
    if groups is not None and pd.unique(pd.Series(groups)).size < max(n_folds, 3):
        raise ValueError("need at least max(n_folds, 3) clusters")

    fold_ids = _fold_ids(len(df), n_folds, groups, random_state)
    ry, rd = _crossfit_residuals(Y, D, Z, fold_ids, n_folds, learner, random_state)

    n = len(df)
    ssd = float(rd @ rd)
    if ssd <= 0:
        raise ValueError("treatment has no variation left after partialling out confounders")
    theta = float(rd @ ry) / ssd
    psi = rd * (ry - theta * rd)
    J = ssd / n
    se_iid = math.sqrt(float(psi @ psi) / n) / (J * math.sqrt(n))
    p_iid = float(2 * stats.norm.sf(abs(theta / se_iid))) if se_iid > 0 else float("nan")

    used = learner if (learner == "linear" or _make_learner(learner, random_state) is not None) else "linear_fallback"
    if groups is None:
        se, pvalue, crit, n_cl, deff = se_iid, p_iid, float(stats.norm.ppf(0.975)), None, float("nan")
        method = f"plr_crossfit_{used}_iid"
    else:
        sums = pd.Series(psi).groupby(pd.Series(groups).to_numpy()).sum().to_numpy()
        G = sums.size
        se = math.sqrt(G / (G - 1) * float(sums @ sums)) / (J * n)
        dof = G - 1
        pvalue = float(2 * stats.t.sf(abs(theta / se), dof)) if se > 0 else float("nan")
        crit = float(stats.t.ppf(0.975, dof))
        n_cl, deff = G, float((se / se_iid) ** 2) if se_iid > 0 else float("nan")
        method = f"plr_crossfit_{used}_cluster"
    return DMLResult(
        coef=theta, se=se, pvalue=pvalue,
        ci_low=theta - crit * se, ci_high=theta + crit * se,
        n_obs=n, method=method, se_iid=se_iid, pvalue_iid=p_iid,
        n_clusters=n_cl, design_effect=deff,
    )


def _newey_west_lrv(x: np.ndarray, lags: int) -> float:
    x = x - x.mean()
    T = x.size
    v = float(x @ x) / T
    for lag in range(1, min(lags, T - 1) + 1):
        v += 2 * (1 - lag / (lags + 1)) * float(x[lag:] @ x[:-lag]) / T
    return v


def estimate_effect_by_period(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    confounders: Sequence[str],
    *,
    time_col: str,
    min_obs: int = 30,
    nw_lags: int = 6,
) -> PeriodEffect:
    """Fama-MacBeth-style effect: one partialling-out slope per period, NW t of their mean.

    Each period collapses its cross-section to a single slope, so no pattern of
    within-period correlation (market, industry, style shocks) can inflate the
    t-stat; serial correlation of the slopes is handled by Newey-West. Nuisances
    are linear within each period: per-period cross-sections are too small for
    flexible learners without overfitting.
    """
    df = panel[[time_col, outcome, treatment, *confounders]].dropna()
    k = len(confounders)
    coefs: dict = {}
    for t, g in df.groupby(time_col, sort=True):
        if len(g) < max(min_obs, k + 3):
            continue
        Z = np.column_stack([np.ones(len(g)), g[list(confounders)].to_numpy(dtype=float).reshape(len(g), -1)])
        Q, _ = np.linalg.qr(Z)
        y = g[outcome].to_numpy(dtype=float)
        d = g[treatment].to_numpy(dtype=float)
        ry = y - Q @ (Q.T @ y)
        rd = d - Q @ (Q.T @ d)
        denom = float(rd @ rd)
        if denom <= 1e-12:
            continue
        coefs[t] = float(rd @ ry) / denom
    s = pd.Series(coefs).sort_index()
    T = s.size
    if T < 12:
        raise ValueError(f"need at least 12 usable periods, got {T}")
    x = s.to_numpy()
    se = math.sqrt(_newey_west_lrv(x, nw_lags) / T)
    t_nw = float(x.mean() / se) if se > 0 else float("nan")
    return PeriodEffect(
        mean_coef=float(x.mean()), t_nw=t_nw,
        pvalue=float(2 * stats.t.sf(abs(t_nw), T - 1)),
        n_periods=T, share_positive=float((x > 0).mean()), nw_lags=nw_lags, coefs=s,
    )
