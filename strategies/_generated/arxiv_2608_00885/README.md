# Optimal Trading of Microstructure Mean Reversion

Auto-generated bundle from `arxiv:2608.00885`.

Template: **mean_reversion**

Matched keywords: `mean reversion`

Paper URL: http://arxiv.org/abs/2608.00885v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.00885",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.00885")`.

### Auto-retrieved passages

- **p.7** (BM25 -18.83):
  > ave no trace in the drift, and the nonlinearity survives only in the total event rate, where the stationary mean definingσ2 M picks it up. SinceX is a martingale,E[dXt|Ft−] = 0, and the reversion of the gap follows. We record it together with the stationary structure it forces. Proposition 2.1(Exact reversion, ergodicity, and moments).Under Definitions 2.1–2.2 and the balanced-response condition(2.8), the gap mean-reverts exactly, E [ dGt|Ft− ] =−αGt−dt (2.12) with no expansion and no approximation, and the conditional mean closes at every horizon, from every state, with no stationarity involved: E[Gt+h|Ft] =G te−αh, t,h≥0.(2.13) 7

- **p.2** (BM25 -17.876):
  > whose move intensities lean toward the efficient price; under one balanced-response condition on the flow, the gap’s reversion, at the book’s leaning rateα, is then a theorem: its conditional mean and stationary covariance 2

- **p.1** (BM25 -16.633):
  > etween mid and efficient price. We take that price to be an exogenous Brownian martingale, andG to be observable. The mid is a pure jump process whose move intensities lean toward the efficient price. Under one balanced-response condition, which equalises the book’s corrective drift across parities, mean reversion ofG is a theorem: its conditional mean and stationary covariance are exactly those of an Ornstein–Uhlenbeck process of reversion rateαand stationary standard deviationsG (the pair the gap’s autocovariance identifies). Its paths are not: the mid jumps. Passage times are therefore evaluated on the Gaussian diffusion those two moments define, at an error we bound on the reward side an …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
