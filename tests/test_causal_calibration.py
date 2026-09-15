"""Size and power calibration for strategies/_common/causal — synthetic panels only.

The factor and the return both carry an independent industry x period shock,
the pattern that made the previous loop pass pure-noise factors on real Taiwan
equity panels (i.i.d. rejection rates 33-63% in the 2026-09 reviews).
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

C = importlib.import_module("strategies._common.causal")


def _panel(rng: np.random.Generator, beta: float = 0.0, n_months: int = 72,
           n_stocks: int = 120, n_industries: int = 8) -> pd.DataFrame:
    month = np.repeat(np.arange(n_months), n_stocks)
    industry = np.tile(np.arange(n_stocks) % n_industries, n_months)
    cell = month * n_industries + industry
    n = month.size
    x = rng.standard_normal(n)
    factor_shock = rng.standard_normal(n_months * n_industries)[cell]
    return_shock = rng.standard_normal(n_months * n_industries)[cell]
    d = factor_shock + 0.5 * rng.standard_normal(n) + 0.3 * x
    y = beta * d + 0.5 * x + return_shock + rng.standard_normal(n)
    return pd.DataFrame({"month": month, "d": d, "y": y, "x": x})


def test_noise_factor_false_pass_rate_is_controlled():
    rng = np.random.default_rng(2026)
    n_sim = 40
    passes = iid_rejects = cluster_rejects = 0
    for _ in range(n_sim):
        v = C.causal_factor_verdict(_panel(rng), "d", "y", ["x"], time_col="month", learner="linear")
        passes += v.verdict == "PASS"
        iid_rejects += v.effect.pvalue_iid < 0.05
        cluster_rejects += v.effect.pvalue < 0.05
    assert passes / n_sim <= 0.15
    assert cluster_rejects / n_sim <= 0.20
    # documents why the i.i.d. standard error cannot be the gate
    assert iid_rejects / n_sim >= 0.25


def test_real_effect_passes():
    v = C.causal_factor_verdict(_panel(np.random.default_rng(7), beta=0.25), "d", "y", ["x"],
                                time_col="month", learner="linear")
    assert v.verdict == "PASS", C.format_verdict(v)
    assert v.effect.design_effect > 1.5
    assert v.period_effect is not None and v.period_effect.t_nw > 3


def test_without_time_col_verdict_is_capped():
    v = C.causal_factor_verdict(_panel(np.random.default_rng(7), beta=0.25), "d", "y", ["x"], learner="linear")
    assert v.verdict in ("CONDITIONAL", "FAIL")
    assert any("time_col" in n for n in v.notes)


def test_confounders_are_never_narrowed():
    df = _panel(np.random.default_rng(1))
    df["z"] = np.random.default_rng(2).standard_normal(len(df))
    assert C.select_confounders(df, "d", "y", ["x", "z"]) == ["x", "z"]
    v = C.causal_factor_verdict(df, "d", "y", ["x", "z"], time_col="month", learner="linear", discover=True)
    assert v.confounders == ["x", "z"]


def test_by_period_effect_requires_enough_periods():
    df = _panel(np.random.default_rng(3), n_months=6)
    with pytest.raises(ValueError):
        C.estimate_effect_by_period(df, "d", "y", ["x"], time_col="month")
