"""Drawdown-aware risk statistics and MDD-constrained leverage sizing.

Companion to ``strategies._common.validation``: that subpackage asks "is this
edge real?", this one asks "given the edge, how much can I press it, and what
will the ride look like?".

Same design rule — numpy / scipy / pandas only, no zipline, no strategy
imports — so this subpackage is lift-ready into ``gs_common.quant.risk``.

Every ratio exported here is convention-dependent; each function documents its
convention and ``ratio_report`` returns them alongside the numbers.
"""
from __future__ import annotations

from .drawdown import (
    EMDD_ASYMPTOTIC_THRESHOLD,
    cagr,
    calmar_ratio,
    complexity_budget,
    drawdown_series,
    drawdown_table,
    equity_from_returns,
    expected_max_drawdown,
    grossman_zhou_leverage,
    kelly_leverage_with_dd_cap,
    martin_ratio,
    max_drawdown,
    mdd_scaling_check,
    merton_fraction,
    ratio_report,
    sortino_ratio,
    sterling_ratio,
    time_under_water,
    ulcer_index,
)

__all__ = [
    # Part A - drawdown geometry
    "drawdown_series",
    "max_drawdown",
    "drawdown_table",
    "ulcer_index",
    "martin_ratio",
    "time_under_water",
    # Part B - ratios
    "cagr",
    "equity_from_returns",
    "calmar_ratio",
    "sterling_ratio",
    "sortino_ratio",
    "ratio_report",
    # Part C - expected maximum drawdown (Magdon-Ismail & Atiya 2004)
    "expected_max_drawdown",
    "mdd_scaling_check",
    "EMDD_ASYMPTOTIC_THRESHOLD",
    # Part D - MDD-constrained leverage
    "merton_fraction",
    "grossman_zhou_leverage",
    "kelly_leverage_with_dd_cap",
    "complexity_budget",
]
