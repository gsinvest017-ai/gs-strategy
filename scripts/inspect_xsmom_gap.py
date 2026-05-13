"""Extract the recorded RMT complexity-gap series from an xsmom_stkfut_rmt
result pickle and print percentile statistics.

Usage:
    .venv-bt/bin/python scripts/inspect_xsmom_gap.py /tmp/xsmom_stkfut_rmt_result.pkl
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_env_path = _ROOT / ".env"
if _env_path.exists() and not os.environ.get("TEJAPI_KEY"):
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import numpy as np
import pandas as pd


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    df = pd.read_pickle(sys.argv[1])
    gap = pd.to_numeric(df["gap"], errors="coerce").dropna()
    print(f"gap n={len(gap)}")
    for p in [5, 10, 25, 33, 50, 66, 75, 90, 95]:
        v = np.percentile(gap, p)
        print(f"  p{p:>2}: {v:.4f}")
    print(f"  mean: {gap.mean():.4f}")
    print(f"  std : {gap.std():.4f}")
    print(f"  min : {gap.min():.4f}")
    print(f"  max : {gap.max():.4f}")

    scale = pd.to_numeric(df["regime_scale"], errors="coerce").dropna()
    print("\nregime_scale distribution:")
    print(scale.value_counts().sort_index())

    print("\nproposed thresholds (paper logic preserved, scaled to observed range):")
    p75 = float(np.percentile(gap, 75))
    p33 = float(np.percentile(gap, 33))
    print(f"  rmt_threshold     (p75 ≈ full position above this): {p75:.4f}")
    print(f"  rmt_low_threshold (p33 ≈ de-risk below this)      : {p33:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
