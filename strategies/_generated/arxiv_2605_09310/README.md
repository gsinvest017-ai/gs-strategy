# Beyond ESG Scores: Learning Dynamic Constraints for Sequential Portfolio Optimization

Auto-generated bundle from `arxiv:2605.09310`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.09310v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.09310",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.09310")`.

### Auto-retrieved passages

- **p.18** (BM25 -5.924):
  > ints per unit turnover. The drawdown penalty uses λdd = 0.02 and d0 = 0.05, so small fluctuations are not penalized, while larger drawdowns reduce the reward. These parameters are shared across methods within each reported experiment. Return, Sharpe, Calmar, turnover, and ESG Violation are computed from the same deterministic test rollouts, so no method receives a more favorable financial evaluation rule. Cash and position constraints.The action is represented as target portfolio weights over N risky assets plus cash. The raw policy output is converted into an invested fraction αt and a normalized risky-asset allocation. In the reported experiments, αt ∈[0.85,1],(30) so the portfolio must ke …

- **p.18** (BM25 -2.956):
  > l contemplated portfolio transition rather than to an unconstrained raw action. Fair-comparison principle.The protocol is designed so that differences in reported performance cannot be attributed to different market observations, different financial rewards, different cash permissions, or different transaction-cost assumptions. All methods use the same financial-only observation space, the same train/validation/test split, the same minimum-invested rule, the same position caps, the same turnover cost, and the same drawdown penalty. Fixed-penalty PPO is the only baseline that inserts ESG cost directly into the reward-side objective, and it is therefore reported as a reward-shaping reference r …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
