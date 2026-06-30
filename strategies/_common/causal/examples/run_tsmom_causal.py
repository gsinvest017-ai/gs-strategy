"""Run the causal de-overfitting loop on the REAL tsmom panel.

Runs in an ISOLATED env (doubleml/dowhy/causal-learn installed, NO zipline) —
per the survey/gs-common-lift isolation rule. We import the zipline-free
``causal`` and ``validation`` subpackages as TOP-LEVEL packages (adding
strategies/_common to sys.path) so the zipline-coupled ``_common/__init__.py``
is never executed.

Run (causal env):
    /home/kevin/.venv-causal/bin/python \
      strategies/_common/causal/examples/run_tsmom_causal.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[4]          # .../gs-strategy
COMMON = REPO / "strategies" / "_common"
sys.path.insert(0, str(COMMON))                      # expose causal/ & validation/

import causal              # noqa: E402  (top-level, zipline-free)
import validation          # noqa: E402

PANEL = REPO / "data" / "causal" / "tsmom_panel.parquet"
CONFOUNDERS = ["vol", "rev", "other_mom"]


def main() -> None:
    panel = pd.read_parquet(PANEL)
    print(f"panel rows={len(panel)} cols={list(panel.columns)}")
    print(f"DoubleML available: {_have('doubleml')}  DoWhy: {_have('dowhy')}"
          f"  causal-learn: {_have('causallearn')}\n")

    # Pooled across TX & MTX: does the 12-1 momentum factor *causally* predict
    # next-month return once vol / reversal / cross-root momentum are controlled?
    v = causal.causal_factor_verdict(
        panel, factor="mom", forward_return="fwd_ret",
        candidate_confounders=CONFOUNDERS,
    )
    print(causal.format_verdict(v))

    # Overfitting-aware gate on the factor's own long/short monthly returns.
    signed = (panel["mom"].apply(lambda x: 1 if x > 0 else -1) * panel["fwd_ret"])
    dsr = validation.deflated_sharpe_ratio(signed.to_numpy(), n_trials=10)
    sr = validation.annualized_sharpe(signed.to_numpy(), periods_per_year=12)
    print(f"\nfactor L/S monthly: annualised SR={sr:.2f}  "
          f"Deflated-SR P(skill | 10 trials)={dsr:.3f}")


def _have(mod: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(mod) is not None


if __name__ == "__main__":
    main()
