# Faster Forward Sensitivities: Reduced stochastic hedge ratios from pathwise algorithmic differentiation

Auto-generated bundle from `arxiv:2605.23979`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.23979v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.23979",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.23979")`.

### Auto-retrieved passages

- **p.18** (BM25 -3.241):
  > es projected or least-squares reduced hedge ratios. It takes the specification of the financial derivative, hedge portfolio, and model parameters, the solution and test basis functions, and the reduction method. The derivative and hedge portfolio are passed as differentiable random variables, which allows their differentials to be queried by object id. 8. Conclusion We have derived reduced methods for obtaining stochastic hedge ratios from pathwise model-primitive sensitivities. The common dimension reduction is the representation of hedge ratios in a finite empirical basis; the hedge-instrument sensitivity tensor is not separately compressed. Two coefficient criteria are natural. The empiri …

- **p.18** (BM25 -3.196):
  > Faster Forward Sensitivities Fries, Christian P . 7.2. Out-of-sample use If the solution basis functions depend only on observable state variables at time t, the fitted coefficients can be used on new paths or in a live hedge calculation by evaluating Xq at the new state and applying (46). Test functions Ys are needed for fitting and diagnostics, but not for reconstructing the hedge ratios. If empirical orthonormalization transformed an original solution basis into X, the same transformation must be stored and reused out of sample. 7.3. Reference implementation A reference implementation is available in the development version of finmath-lib [9]. It is located in the package net.finmath.mont …

- **p.7** (BM25 -2.735):
  > Faster Forward Sensitivities Fries, Christian P . the pathwise hedge-instrument sensitivity tensor is retained in the reduced empirical equations. Several approaches also determine hedge or risk coefficients by regression or simulation. Hedged Monte-Carlo methods include a hedge strategy in the Monte-Carlo valuation and estimate hedge coefficients together with the price [26]. Avellaneda and Gamba [3] characterize Monte-Carlo hedge ratios with respect to input prices through moments of simulated cash flows. Regression-based methods for sensitivities and hedging, especially for American or Bermudan products, are developed in [4, 27, 22]. These methods share the use of simulated paths and fini …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
