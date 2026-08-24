"""Tests for strategies/_common/validation/report.py — synthetic returns only."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

report = importlib.import_module("strategies._common.validation.report")


def _perf_frame(seed=7, n=504, drift=0.0004):
    rng = np.random.RandomState(seed)
    rets = rng.normal(drift, 0.01, n)
    return pd.DataFrame({"returns": rets})


def test_build_report_fields_and_sanity():
    rep = report.build_report(_perf_frame(), n_trials=1)
    for key in ("schema", "n_days", "total_return", "cagr",
                "annualized_sharpe", "max_drawdown", "psr", "dsr", "n_trials"):
        assert key in rep, key
    assert rep["n_days"] == 504
    assert -1.0 < rep["max_drawdown"] <= 0.0
    assert 0.0 <= rep["psr"] <= 1.0


def test_dsr_deflates_with_more_trials():
    perf = _perf_frame()
    dsr_1 = report.build_report(perf, n_trials=1)["dsr"]
    dsr_100 = report.build_report(perf, n_trials=100)["dsr"]
    assert dsr_100 < dsr_1            # more trials -> harsher deflation


def test_missing_column_and_short_series_raise():
    with pytest.raises(ValueError):
        report.build_report(pd.DataFrame({"close": [1, 2, 3]}))
    with pytest.raises(ValueError):
        report.build_report(pd.DataFrame({"returns": [0.01] * 5}))


def test_cli_parquet_roundtrip(tmp_path):
    perf = _perf_frame()
    p = tmp_path / "perf.parquet"
    perf.to_parquet(p, index=False)
    out = tmp_path / "report.json"
    rc = report.main([str(p), "--n-trials", "10", "-o", str(out)])
    assert rc == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == report.SCHEMA
    assert doc["n_trials"] == 10
