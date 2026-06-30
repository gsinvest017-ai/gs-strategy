"""Runnable PoC for the causal factor de-overfitting loop.

Builds a synthetic panel with TWO factors:
  * ``real_factor``    — genuinely *causes* forward return.
  * ``spurious_factor``— correlated with return only through a confounder
                         (``macro``); it has NO direct causal effect.

A correct loop should PASS real_factor and FAIL/CONDITIONAL spurious_factor.
Runs today on numpy/scipy/pandas alone (no doubleml/dowhy needed); install the
heavy libs to exercise the real DML + DoWhy paths.

Usage (from repo root, inside the strategies env):
    python -m strategies._common.causal.examples.causal_poc
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies._common.causal import causal_factor_verdict, format_verdict
from strategies._common.validation import deflated_sharpe_ratio


def make_panel(n: int = 1500, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    macro = rng.standard_normal(n)                       # confounder
    real_factor = rng.standard_normal(n)
    # spurious factor is driven by macro, not by its own signal
    spurious_factor = 0.8 * macro + 0.6 * rng.standard_normal(n)
    # forward return: caused by real_factor and macro; NOT by spurious_factor
    fwd_ret = (
        0.05 * real_factor
        + 0.04 * macro
        + 0.01 * rng.standard_normal(n)
    )
    return pd.DataFrame(
        {
            "fwd_ret": fwd_ret,
            "real_factor": real_factor,
            "spurious_factor": spurious_factor,
            "macro": macro,
        }
    )


def main() -> None:
    panel = make_panel()
    confounders = ["macro"]

    print("=== Causal factor de-overfitting PoC ===")
    for factor in ["real_factor", "spurious_factor"]:
        v = causal_factor_verdict(panel, factor, "fwd_ret", confounders)
        print(format_verdict(v))
        print()

    # demo the overfitting-aware gate on a toy return stream
    rng = np.random.default_rng(1)
    pnl = 0.0008 + 0.01 * rng.standard_normal(750)
    dsr = deflated_sharpe_ratio(pnl, n_trials=50)
    print(f"Deflated Sharpe (50 trials sprayed) P(skill) = {dsr:.3f}")


if __name__ == "__main__":
    main()
