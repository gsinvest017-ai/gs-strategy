# Distributional Portfolio Optimization (DPO): A Unified Framework for Distributions over Weights, Returns, and Parameters

Auto-generated bundle from `arxiv:2605.30464`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.30464v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.30464",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.30464")`.

### Auto-retrieved passages

- **p.22** (BM25 -5.769):
  > aves, convergence holds inL 2 for the entire allocation vector. The RA-HRP case is identical with the corresponding split parameters. 9 Distributional reinforcement learning for portfolios Standard RLPO learnsQ π(s, w) =E π[P t γtRt |s 0 =s, w 0 =w]. Distributional RL (Bellemare et al., 2017) learns the full return distributionZ π(s, w) = Law(P t γtRt |s 0 =s, w 0 =w). 9.1 The portfolio MDP and distributional Bellman operator Let (S,A,P, γ) be a discounted portfolio MDP withA=W. To allow turnover penalties, the one-period reward is allowed to depend on the current action, next state, and next action: g(s, w, s′, w′) :=w ⊤r(s, s′)−c(w, w ′). The transition iss ′ ∼P(· |s, w), and the next acti …

- **p.9** (BM25 -4.641):
  > 2.5 Standing assumptions Assumption 2.7(Standing regularity).Unless stated otherwise, the following are imposed throughout the paper. (i) The feasible setW ⊂R K is non-empty, convex, compact, withB W := supw∈W ∥w∥<∞. (ii) Return laws lie inP 1(RK), and the conditional modelθ7→R θ is Borel measurable. (iii) The utilityu:R→Ris non-decreasing, concave, and continuous; when Wasserstein- continuity is required,uis assumedL u-Lipschitz. (iv) Risk measures act on lossesL(w, r) =−r ⊤w. Unless otherwise stated,ρis a law-invariant convex risk measure on losses (Definition 2.1), lower semicontinuous with respect toW 1 convergence onP 1(R). (v) In static product-form problems, the allocation draw and re …

- **p.26** (BM25 -4.598):
  > static CVaR does not decompose recursively: CVaRα(R+γZ(s ′, w′))̸=R+γCVaR α(Z(s ′, w′)) in general. Equality holds only in special cases, for example whenRis deterministic conditional on the current state-action pair (so the translation invariance of CVaR applies). The static formulation of Definition 9.4 therefore does not admit a Bellman recursion withρ= CVaR α; the dynamic formulation of Definition 9.6, which nestsρ 1 s′,w′ = CVaRα at each step, does, by Theorem 9.8. Remark9.12 (Dynamic-CVaR and Markov risk measures).The time-inconsistency of static CVaR is formalized in a substantial literature on Markov risk measures and time-consistent dynamic programming. Ruszczy´ nski (2010) introduc …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
