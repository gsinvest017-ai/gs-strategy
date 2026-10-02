"""Causal-graph discovery, reported as a diagnostic only.

Wraps ``causal-learn`` (PC algorithm) to propose a DAG from data. Earlier
versions used it to *narrow* the confounder set to nodes adjacent to both the
treatment and the outcome. That is removed, for three reasons:

1. PC's conditional-independence tests use i.i.d. p-values. On stock x period
   panels with 1e5 rows and common shocks, edges appear and disappear with the
   sample size and the cross-sectional correlation, not with the causal
   structure.
2. Dropping a true confounder X re-introduces omitted-variable bias
   ``plim theta^ - theta = beta_X * Cov(D, X | kept) / Var(D | kept)``, and PC
   is most likely to drop exactly the weakly-estimated variables.
3. Inference after data-driven selection is not valid with the unadjusted
   standard error.

Controls may be added to a pre-registered list, never removed by the data.
"""
from __future__ import annotations

from typing import Sequence

import pandas as pd


def discover_dag(panel: pd.DataFrame, columns: Sequence[str], alpha: float = 0.05):
    """Run PC and return (adjacency_matrix, column_order).

    Raises ImportError if causal-learn is not installed.
    """
    from causallearn.search.ConstraintBased.PC import pc  # type: ignore

    data = panel[list(columns)].dropna().to_numpy()
    cg = pc(data, alpha=alpha, show_progress=False)
    return cg.G.graph, list(columns)


def select_confounders(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    candidates: Sequence[str],
    alpha: float = 0.05,
) -> list[str]:
    """Return the confounders to control for: always the full candidate list.

    Kept for backward compatibility; ``panel``, ``treatment``, ``outcome`` and
    ``alpha`` are ignored. See the module docstring for why the data may not
    shrink this set. Use :func:`dag_diagnostics` to look at the PC graph.
    """
    return list(candidates)


def dag_diagnostics(
    panel: pd.DataFrame,
    treatment: str,
    outcome: str,
    candidates: Sequence[str],
    alpha: float = 0.05,
) -> dict:
    """Descriptive PC-graph facts; never used to change the control set."""
    cols = [treatment, outcome, *candidates]
    try:
        adj, order = discover_dag(panel, cols, alpha=alpha)
    except ImportError:
        return {"available": False}
    ti, oi = order.index(treatment), order.index(outcome)

    def adjacent(a: int, b: int) -> bool:
        return adj[a][b] != 0 or adj[b][a] != 0

    return {
        "available": True,
        "treatment_outcome_adjacent": bool(adjacent(ti, oi)),
        "adjacent_to_treatment": [c for c in candidates if adjacent(order.index(c), ti)],
        "adjacent_to_outcome": [c for c in candidates if adjacent(order.index(c), oi)],
        "note": "PC uses i.i.d. conditional-independence tests; descriptive only on panels",
    }
