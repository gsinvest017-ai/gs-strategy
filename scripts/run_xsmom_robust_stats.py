"""Robust statistical reporting on top of M18 stat-sig results.

Three additions beyond M18 (run_xsmom_stat_sig.py):

  1. Newey-West HAC-adjusted t-statistic (lag = 5 trading days ≈ 1 week)
     -- corrects the parametric t-stat for autocorrelation & heteroscedasticity
     in daily returns. Compare against the plain OLS t-stat from M18.

  2. Cohen's d effect size with block-bootstrap 95% CI (block_size=20)
     -- d = mean / std; CI from same block-bootstrap as M18's Sharpe CI.
     |d| > 0.8 is "large effect"; here we expect ~7σ-scale values.

  3. Multi-test corrections across 4 datasets (M17 canonical + 3 sub-periods)
     -- Bonferroni (a = a/k) and Holm-Bonferroni step-down on the
     parametric one-sided p-values. Demonstrates the M11-M17 ablation
     budget (≈ 13 tests) is still rejected at corrected alpha.

Loads one or more zipline result.pkl paths, writes a combined markdown
report. Wraps .env so pickle.load can import zipline.

Usage:
    .venv-bt/bin/python scripts/run_xsmom_robust_stats.py \\
        /tmp/xsmom_m17_commonly_result.pkl \\
        /tmp/xsmom_m16_walkforward_P1_2020_2021_result.pkl \\
        /tmp/xsmom_m16_walkforward_P2_2022_2023_result.pkl \\
        /tmp/xsmom_m16_walkforward_P3_2024_2026_result.pkl
"""
from __future__ import annotations

import argparse
import json
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
from scipy import stats
import statsmodels.api as sm

TRADING_DAYS_PER_YEAR = 252


def _sharpe(r: np.ndarray) -> float:
    s = r.std(ddof=1)
    if s <= 0 or len(r) < 2:
        return float("nan")
    return float(r.mean() / s * np.sqrt(TRADING_DAYS_PER_YEAR))


def _cohens_d(r: np.ndarray) -> float:
    """Cohen's d for one-sample test against 0: d = mean / std."""
    s = r.std(ddof=1)
    if s <= 0 or len(r) < 2:
        return float("nan")
    return float(r.mean() / s)


def _block_bootstrap_idx(n: int, block_size: int, rng: np.random.Generator) -> np.ndarray:
    """Stationary block-bootstrap indices (with wrap-around)."""
    n_blocks = (n + block_size - 1) // block_size
    starts = rng.integers(0, n, size=n_blocks)
    idx = (starts[:, None] + np.arange(block_size)[None, :]) % n
    return idx.ravel()[:n]


def block_bootstrap_cohens_d(
    returns: np.ndarray, block_size: int, n_iter: int, seed: int
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(returns)
    ds = np.empty(n_iter)
    for i in range(n_iter):
        idx = _block_bootstrap_idx(n, block_size, rng)
        ds[i] = _cohens_d(returns[idx])
    ds = ds[~np.isnan(ds)]
    return {
        "observed": _cohens_d(returns),
        "p025": float(np.percentile(ds, 2.5)),
        "p50": float(np.percentile(ds, 50)),
        "p975": float(np.percentile(ds, 97.5)),
        "ci_includes_zero": bool(np.percentile(ds, 2.5) <= 0 <= np.percentile(ds, 97.5)),
        "n_iter": int(n_iter),
        "block_size": int(block_size),
    }


def newey_west_t_stat(returns: np.ndarray, lag: int) -> dict:
    """One-sample HAC t-test of mean(returns) vs 0 with Newey-West (HAC) SE.

    Regresses returns on a constant; reports the const coefficient's HAC
    t-statistic at the given lag.
    """
    n = len(returns)
    X = np.ones((n, 1))
    model = sm.OLS(returns, X)
    res = model.fit(cov_type="HAC", cov_kwds={"maxlags": int(lag)})
    coef = float(res.params[0])
    se = float(res.bse[0])
    t = float(res.tvalues[0])
    # parametric one-sided p for "mean < 0" given observed sign
    p_two = float(res.pvalues[0])
    p_one_lt = p_two / 2 if t < 0 else 1 - p_two / 2
    return {
        "lag": int(lag),
        "mean": coef,
        "hac_se": se,
        "t_stat": t,
        "p_two_sided": p_two,
        "p_one_sided_neg": p_one_lt,
    }


def plain_t_test(returns: np.ndarray) -> dict:
    t_stat, p_two = stats.ttest_1samp(returns, 0.0)
    p_one_lt = p_two / 2 if t_stat < 0 else 1 - p_two / 2
    return {
        "t_stat": float(t_stat),
        "p_two_sided": float(p_two),
        "p_one_sided_neg": float(p_one_lt),
        "dof": int(len(returns) - 1),
    }


def bonferroni_corrected(pvals: list[float], k_total: int) -> list[float]:
    """Multiply each p-value by k_total, cap at 1.0."""
    return [min(p * k_total, 1.0) for p in pvals]


def holm_bonferroni(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment.

    Sort p-values asc; multiply the i-th smallest by (k - i); take running max
    so adjusted p-values are monotonic; return in original order.
    """
    k = len(pvals)
    order = sorted(range(k), key=lambda i: pvals[i])
    adj_sorted = []
    running_max = 0.0
    for rank, orig_idx in enumerate(order):
        candidate = pvals[orig_idx] * (k - rank)
        adj = min(max(candidate, running_max), 1.0)
        running_max = adj
        adj_sorted.append(adj)
    out = [0.0] * k
    for rank, orig_idx in enumerate(order):
        out[orig_idx] = adj_sorted[rank]
    return out


def trim_tail_zeros(returns: np.ndarray) -> np.ndarray:
    nonzero_mask = returns != 0
    if not nonzero_mask.any():
        return returns
    last_nonzero = np.where(nonzero_mask)[0][-1]
    return returns[: last_nonzero + 1]


def analyze_one(pkl_path: str, block_size: int, n_iter: int, lag: int, seed: int) -> dict:
    df = pd.read_pickle(pkl_path)
    raw = df["returns"].values.astype(float)
    n_total = len(raw)
    returns = trim_tail_zeros(raw)
    n_used = len(returns)

    plain = plain_t_test(returns)
    hac = newey_west_t_stat(returns, lag=lag)
    cohend = block_bootstrap_cohens_d(returns, block_size, n_iter, seed)

    return {
        "input_path": pkl_path,
        "label": Path(pkl_path).stem,
        "n_total": int(n_total),
        "n_used": int(n_used),
        "sharpe_observed": _sharpe(returns),
        "plain_t": plain,
        "newey_west": hac,
        "cohens_d": cohend,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pkls", nargs="+", help="one or more zipline result.pkl paths")
    ap.add_argument("--block-size", type=int, default=20)
    ap.add_argument("--n-iter", type=int, default=10000)
    ap.add_argument("--lag", type=int, default=5, help="Newey-West HAC lag (trading days)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--ablation-budget",
        type=int,
        default=13,
        help="number of independent hypotheses across M11-M17 ablation for "
             "Bonferroni denominator (M11=8, M13/14/15/16/17 cost map=5)",
    )
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    print(f"# xsmom_stkfut_rmt robust statistical report", file=sys.stderr)
    print(f"# n_iter={args.n_iter}, block_size={args.block_size}, lag={args.lag}", file=sys.stderr)
    print(f"# ablation budget for Bonferroni = {args.ablation_budget} hypotheses", file=sys.stderr)
    print(f"# datasets: {len(args.pkls)}", file=sys.stderr)

    rows = [analyze_one(p, args.block_size, args.n_iter, args.lag, args.seed) for p in args.pkls]

    # multi-test corrections — use HAC one-sided p as the primary test
    # (it's the most conservative against autocorrelation).
    hac_pvals = [r["newey_west"]["p_one_sided_neg"] for r in rows]
    bonf_local = bonferroni_corrected(hac_pvals, len(hac_pvals))
    bonf_budget = bonferroni_corrected(hac_pvals, args.ablation_budget)
    holm = holm_bonferroni(hac_pvals)
    for r, b_local, b_budget, h in zip(rows, bonf_local, bonf_budget, holm):
        r["correction"] = {
            "bonferroni_k_local": float(b_local),
            "bonferroni_k_ablation": float(b_budget),
            "holm_bonferroni": float(h),
        }

    if args.json:
        json.dump({"datasets": rows}, sys.stdout, indent=2)
        print()
        return 0

    # markdown
    print()
    print("## M19 — Robust statistical reporting")
    print()
    print(f"- HAC lag = {args.lag} trading days (~ 1 week serial dependence)")
    print(f"- Cohen's d block-bootstrap: block_size = {args.block_size}, n_iter = {args.n_iter}")
    print(f"- Bonferroni denominators: k_local = {len(rows)}, k_ablation = {args.ablation_budget}")
    print()
    print("### Per-dataset HAC vs plain t-statistic + effect size")
    print()
    print("| dataset | n_used | Sharpe | plain t | HAC t (lag=5) | HAC SE / plain SE | Cohen's d | d 95% CI | d CI ∋ 0? |")
    print("|---|---:|---:|---:|---:|---:|---:|---|---:|")
    for r in rows:
        plain_se = abs(r["plain_t"]["t_stat"]) and (
            abs(r["newey_west"]["mean"]) / abs(r["plain_t"]["t_stat"])
        ) or float("nan")
        hac_to_plain_se = (r["newey_west"]["hac_se"] / plain_se) if plain_se else float("nan")
        d = r["cohens_d"]
        print(
            f"| {r['label']} | {r['n_used']} | {r['sharpe_observed']:.3f} | "
            f"{r['plain_t']['t_stat']:.3f} | {r['newey_west']['t_stat']:.3f} | "
            f"{hac_to_plain_se:.3f}× | "
            f"{d['observed']:.3f} | [{d['p025']:.3f}, {d['p975']:.3f}] | "
            f"{d['ci_includes_zero']} |"
        )
    print()
    print("### Multi-test corrections (one-sided p, H1: mean < 0)")
    print()
    print("| dataset | HAC p (raw) | plain p (raw) | Bonf k=local | Bonf k=ablation | Holm-Bonf |")
    print("|---|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['label']} | {r['newey_west']['p_one_sided_neg']:.3e} | "
            f"{r['plain_t']['p_one_sided_neg']:.3e} | "
            f"{r['correction']['bonferroni_k_local']:.3e} | "
            f"{r['correction']['bonferroni_k_ablation']:.3e} | "
            f"{r['correction']['holm_bonferroni']:.3e} |"
        )
    print()
    print("### Pass/fail at α = 0.05")
    print()
    print("| dataset | raw HAC | Bonf local | Bonf ablation | Holm |")
    print("|---|---|---|---|---|")
    for r in rows:
        raw = r["newey_west"]["p_one_sided_neg"]
        bl = r["correction"]["bonferroni_k_local"]
        bb = r["correction"]["bonferroni_k_ablation"]
        h = r["correction"]["holm_bonferroni"]
        def _v(p):
            return "REJECT H0" if p < 0.05 else "fail to reject"
        print(f"| {r['label']} | {_v(raw)} | {_v(bl)} | {_v(bb)} | {_v(h)} |")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
