"""Runnable PoC for the causal factor de-overfitting loop.

Builds a synthetic stock x month panel with TWO factors:
  * ``real_factor``    — genuinely *causes* forward return.
  * ``spurious_factor``— correlated with return only through a confounder
                         (``macro``); it has NO direct causal effect.

Returns also share an industry x month shock, as real equity panels do, so the
loop has to use period-clustered inference. A correct loop should PASS
real_factor and FAIL spurious_factor.

Usage (from repo root, inside the strategies env):
    python -m strategies._common.causal.examples.causal_poc
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies._common.causal import causal_factor_verdict, format_verdict
from strategies._common.validation import deflated_sharpe_ratio


def make_panel(n_months: int = 60, n_stocks: int = 80, n_industries: int = 8, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    month = np.repeat(np.arange(n_months), n_stocks)
    industry = np.tile(np.arange(n_stocks) % n_industries, n_months)
    cell = month * n_industries + industry
    n = month.size
    macro = rng.standard_normal(n)                       # confounder
    real_factor = rng.standard_normal(n)
    # spurious factor is driven by macro, not by its own signal
    spurious_factor = 0.8 * macro + 0.6 * rng.standard_normal(n)
    shock = rng.standard_normal(n_months * n_industries)[cell]
    # forward return: caused by real_factor and macro; NOT by spurious_factor
    fwd_ret = 0.05 * real_factor + 0.04 * macro + 0.03 * shock + 0.01 * rng.standard_normal(n)
    return pd.DataFrame({
        "month": month, "fwd_ret": fwd_ret, "real_factor": real_factor,
        "spurious_factor": spurious_factor, "macro": macro,
    })


def main() -> None:
    panel = make_panel()
    confounders = ["macro"]

    print("=== Causal factor de-overfitting PoC ===")
    for factor in ["real_factor", "spurious_factor"]:
        v = causal_factor_verdict(panel, factor, "fwd_ret", confounders, time_col="month")
        print(format_verdict(v))
        print()

    # demo the overfitting-aware gate on a toy return stream
    rng = np.random.default_rng(1)
    pnl = 0.0008 + 0.01 * rng.standard_normal(750)
    dsr = deflated_sharpe_ratio(pnl, n_trials=50)
    print(f"Deflated Sharpe (50 trials sprayed) P(skill) = {dsr:.3f}")


if __name__ == "__main__":
    main()
