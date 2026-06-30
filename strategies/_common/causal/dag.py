"""Causal-graph discovery + confounder selection.

Wraps ``causal-learn`` (PC algorithm) to propose a DAG from data, then reads
off the parents of the outcome as the confounder set to control for. Optional
dependency; if absent, :func:`select_confounders` falls back to "use every
non-treatment, non-outcome column", which is the safe (over-)conditioning set.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def discover_dag(panel: pd.DataFrame, columns: Sequence[str], alpha: float = 0.05):
    """Run PC and return (adjacency_matrix, column_order).

    Raises ImportError if causal-learn is not installed — callers should catch
    and degrade to :func:`select_confounders`'s fallback.
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
    """Return confounders to control for: nodes adjacent to *both* treatment
    and outcome in the discovered DAG. Falls back to all candidates.
    """
    cols = [treatment, outcome, *candidates]
    try:
        adj, order = discover_dag(panel, cols, alpha=alpha)
    except ImportError:
        return list(candidates)

    ti, oi = order.index(treatment), order.index(outcome)
    chosen = []
    for c in candidates:
        ci = order.index(c)
        # adjacency (any edge mark) to both treatment and outcome => confounder
        adj_t = adj[ci][ti] != 0 or adj[ti][ci] != 0
        adj_o = adj[ci][oi] != 0 or adj[oi][ci] != 0
        if adj_t and adj_o:
            chosen.append(c)
    return chosen or list(candidates)
