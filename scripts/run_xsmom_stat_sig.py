"""Quantify the xsmom_stkfut_rmt M17 negative finding into a formal stat-sig test.

Three complementary null-hypothesis tests on the daily-return series:

  1. Block bootstrap Sharpe 95% CI (block_size=20 ≈ 1 monthly rebalance cycle)
     -- accounts for serial autocorrelation in returns; CI includes 0 means
     Sharpe is not statistically distinguishable from zero.

  2. Block bootstrap mean-return p-value (one-sided)
     -- fraction of bootstrap samples whose mean exceeds 0; tests directly
     whether the observed negative drift could have arisen by chance.

  3. Sign-flip permutation test (n=10000)
     -- randomly flips ±1 on each daily return, builds null distribution of
     Sharpe under H0(mean = 0). Preserves the empirical variance and the
     event of large daily moves; symmetrizes only the sign.

Loads result.pkl, writes a markdown table + JSON to stdout. Wraps .env so
pickle.load can import zipline.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_stat_sig.py \\
        /tmp/xsmom_m17_commonly_result.pkl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Auto-load .env so pickle.load() can import zipline (TEJAPI_KEY at module-import).
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

TRADING_DAYS_PER_YEAR = 252


def sharpe(r: np.ndarray) -> float:
    s = r.std(ddof=1)
    if s <= 0 or len(r) < 2:
        return float("nan")
    return float(r.mean() / s * np.sqrt(TRADING_DAYS_PER_YEAR))


def block_bootstrap_indices(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    """Stationary block bootstrap: sample ceil(n/block_size) start points,
    take block_size consecutive indices (with wrap-around), truncate to n."""
    n_blocks = (n + block_size - 1) // block_size
    starts = rng.integers(0, n, size=n_blocks)
    idx = (starts[:, None] + np.arange(block_size)[None, :]) % n
    return idx.ravel()[:n]


def run_block_bootstrap(returns: np.ndarray, block_size: int, n_iter: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = len(returns)
    sharpes = np.empty(n_iter)
    means = np.empty(n_iter)
    for i in range(n_iter):
        idx = block_bootstrap_indices(n, block_size, rng)
        sample = returns[idx]
        sharpes[i] = sharpe(sample)
        means[i] = sample.mean()
    sharpes = sharpes[~np.isnan(sharpes)]
    return {
        "n_iter": int(n_iter),
        "block_size": int(block_size),
        "sharpe_observed": sharpe(returns),
        "sharpe_p025": float(np.percentile(sharpes, 2.5)),
        "sharpe_p50": float(np.percentile(sharpes, 50)),
        "sharpe_p975": float(np.percentile(sharpes, 97.5)),
        "ci_includes_zero": bool(np.percentile(sharpes, 2.5) <= 0 <= np.percentile(sharpes, 97.5)),
        "mean_observed": float(returns.mean()),
        # one-sided p-value: P(bootstrap mean >= 0) under H0(true mean=0)
        # we use empirical bootstrap shifted to be centered at 0:
        # p = P(mean_centered >= -obs_mean) where mean_centered = means - mean_observed
        "p_mean_greater_than_zero": float(np.mean((means - returns.mean()) >= -returns.mean())),
    }


def run_signflip_permutation(returns: np.ndarray, n_iter: int, seed: int) -> dict:
    rng = np.random.default_rng(seed + 7919)  # different seed stream from bootstrap
    n = len(returns)
    obs_sharpe = sharpe(returns)
    null_sharpes = np.empty(n_iter)
    for i in range(n_iter):
        flips = rng.choice([-1.0, 1.0], size=n)
        null_sharpes[i] = sharpe(flips * returns)
    null_sharpes = null_sharpes[~np.isnan(null_sharpes)]
    p_one_sided = float(np.mean(null_sharpes <= obs_sharpe))
    p_two_sided = float(np.mean(np.abs(null_sharpes) >= abs(obs_sharpe)))
    return {
        "n_iter": int(n_iter),
        "sharpe_observed": obs_sharpe,
        "null_sharpe_mean": float(null_sharpes.mean()),
        "null_sharpe_std": float(null_sharpes.std(ddof=1)),
        "null_sharpe_p025": float(np.percentile(null_sharpes, 2.5)),
        "null_sharpe_p975": float(np.percentile(null_sharpes, 97.5)),
        "p_one_sided_neg": p_one_sided,  # fraction of nulls <= observed
        "p_two_sided": p_two_sided,
    }


def parametric_t_test(returns: np.ndarray) -> dict:
    """One-sample t-test of returns against 0. Provides parametric reference
    against which the bootstrap / permutation results can be sanity-checked."""
    from scipy import stats

    t_stat, p_two = stats.ttest_1samp(returns, 0.0)
    # one-sided p-value for "mean < 0" (since observed mean is negative)
    p_one_lt = p_two / 2 if t_stat < 0 else 1 - p_two / 2
    return {
        "t_stat": float(t_stat),
        "p_two_sided": float(p_two),
        "p_one_sided_neg": float(p_one_lt),
        "dof": int(len(returns) - 1),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pkl", help="zipline result.pkl path")
    ap.add_argument("--block-size", type=int, default=20, help="bootstrap block size (~1 month)")
    ap.add_argument("--n-iter", type=int, default=10000, help="bootstrap / permutation iterations")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--include-zeros", action="store_true",
                    help="keep zero-return days (default: drop tail zeros after portfolio dies)")
    ap.add_argument("--json", action="store_true", help="output JSON instead of markdown")
    args = ap.parse_args()

    df = pd.read_pickle(args.pkl)
    returns = df["returns"].values.astype(float)
    n_total = len(returns)

    # Drop tail zeros after portfolio dies (PV drops to point where daily moves
    # round to 0 in float precision -- not actual market data, just dead state).
    if not args.include_zeros:
        # Find last non-zero return; keep everything up to and including it.
        nonzero_mask = returns != 0
        if nonzero_mask.any():
            last_nonzero = np.where(nonzero_mask)[0][-1]
            returns = returns[: last_nonzero + 1]
    n_used = len(returns)

    print(f"# xsmom_stkfut_rmt statistical significance test", file=sys.stderr)
    print(f"# input: {args.pkl}", file=sys.stderr)
    print(f"# total rows: {n_total}, used (post-dead-state trim): {n_used}", file=sys.stderr)
    print(f"# block_size={args.block_size}, n_iter={args.n_iter}, seed={args.seed}", file=sys.stderr)

    bootstrap = run_block_bootstrap(returns, args.block_size, args.n_iter, args.seed)
    signflip = run_signflip_permutation(returns, args.n_iter, args.seed)
    ttest = parametric_t_test(returns)

    result = {
        "input_path": args.pkl,
        "n_total_rows": int(n_total),
        "n_used_rows": int(n_used),
        "trim_tail_zeros": not args.include_zeros,
        "block_bootstrap": bootstrap,
        "signflip_permutation": signflip,
        "parametric_t_test": ttest,
    }

    if args.json:
        json.dump(result, sys.stdout, indent=2)
        print()
        return 0

    # markdown output
    print()
    print(f"## Statistical significance: {Path(args.pkl).stem}")
    print()
    print(f"- daily returns used: {n_used} / {n_total} (post-dead-state trim: {not args.include_zeros})")
    print(f"- block bootstrap: {args.n_iter} iter, block_size={args.block_size} days")
    print()
    print("### Block bootstrap Sharpe 95% CI")
    print()
    print("| stat | value |")
    print("|---|---:|")
    print(f"| observed Sharpe | {bootstrap['sharpe_observed']:.3f} |")
    print(f"| bootstrap median | {bootstrap['sharpe_p50']:.3f} |")
    print(f"| 95% CI lower (p2.5) | {bootstrap['sharpe_p025']:.3f} |")
    print(f"| 95% CI upper (p97.5) | {bootstrap['sharpe_p975']:.3f} |")
    print(f"| CI includes 0 | {bootstrap['ci_includes_zero']} |")
    print()
    print("### Mean return p-value (one-sided, H1: mean > 0)")
    print()
    print(f"- bootstrap p(mean > 0) = {bootstrap['p_mean_greater_than_zero']:.4f}")
    print(f"- parametric t-test t = {ttest['t_stat']:.3f} (dof={ttest['dof']})")
    print(f"- parametric one-sided p(mean < 0) = {ttest['p_one_sided_neg']:.4g}")
    print()
    print("### Sign-flip permutation test (H0: mean = 0)")
    print()
    print("| stat | value |")
    print("|---|---:|")
    print(f"| observed Sharpe | {signflip['sharpe_observed']:.3f} |")
    print(f"| null Sharpe mean | {signflip['null_sharpe_mean']:.3f} |")
    print(f"| null Sharpe std | {signflip['null_sharpe_std']:.3f} |")
    print(f"| null Sharpe p2.5 / p97.5 | {signflip['null_sharpe_p025']:.3f} / {signflip['null_sharpe_p975']:.3f} |")
    print(f"| p (one-sided, null Sharpe ≤ observed) | {signflip['p_one_sided_neg']:.4f} |")
    print(f"| p (two-sided, &#124;null&#124; ≥ &#124;obs&#124;) | {signflip['p_two_sided']:.4f} |")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
