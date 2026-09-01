# What Does Deep Hedging Actually Learn? Delta Corrections, Regime Fragility, and Symbolic Distillation

Auto-generated bundle from `arxiv:2605.21696`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.21696v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.21696",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.21696")`.

### Auto-retrieved passages

- **p.5** (BM25 -3.937):
  > level in(3.5). Dividend yield enters the Black-Scholes benchmark and the forward-moneyness state variable, but it is not added as a separate realized cash-flow term in the index-level hedge account. This convention keeps the P&L definition aligned with the price series used in the empirical data and avoids mixing the index-level hedge with the cash-flow accounting of a dividend-paying ETF or stock basket. The exact implemented reward is computed from daily P&L as: rt+1 = 10 ( 0.03 + PnL(100) t+1 −κ ⏐⏐⏐PnL(100) t+1 ⏐⏐⏐ α) ,(3.6) 5

- **p.5** (BM25 -2.817):
  > where ϕdenotes the parameters of the actor network. The objective is to maximize the expected discounted return J(µϕ) =E [∞∑ i=0 γirt+i ⏐⏐⏐⏐⏐µϕ ] ,(3.3) where γ∈(0, 1]is the discount factor andrt+i represents the immediate reward. In finite hedging episodes, the sum ends at episode termination or option maturity. Because the action is continuous, the implementation uses Twin Delayed Deep Deter- ministic Policy Gradient (TD3), an actor-critic method. A critic network estimates the action valueQ(s,a|θ), and the actor is updated in the direction that raises the critic’s value for the chosen hedge. TD3 stabilizes this procedure by training two critics and using the smaller target value, yj =r j  …

- **p.5** (BM25 -2.768):
  > as, the noise smooths the value surface, and delayed actor updates make policy changes depend on more stable critic estimates. 3.2 Reward Function and Hedging P&L The reward function determines what kind of hedge the agent is asked to learn. Unlike a quadratic or terminal mean-variance criterion, the objective here is local and asymmetric. It is closest to lower-partial-moment and shortfall-risk ideas (Föllmer and Leukert, 2000; Schulmerich and Trautmann, 2003; Coleman et al., 2003): adverse hedging errors matter, while favorable hedging outcomes are not treated as risk in the same way. The empirical environment in this paper evaluates a long call option hedged with a short position in the u …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
