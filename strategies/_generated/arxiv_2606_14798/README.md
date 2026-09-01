# Two Sides of Schur Damping: High-Dimensional Pseudo-Likelihoods and Portfolio Allocation

Auto-generated bundle from `arxiv:2606.14798`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.14798v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.14798",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.14798")`.

### Auto-retrieved passages

- **p.2** (BM25 -2.946):
  > readings. Damping the complement, as in the next section, givesS(𝛾)=(1−𝛾) ·1+𝛾(1−𝜌 2)=1−𝛾 𝜌 2: at 𝛾=1 the full hedge / full conditioning, at 𝛾=0 none (the marginal variance, an unhedged position), and at𝛾=𝛾 ★ a residual risk that trusts the estimated coupling only as far as it is reliable. The pseudo-likelihood and the portfolio read the same1−𝛾 𝜌 2 off the same complement. 3 The shared cure: damping by reliability Both readings break for the same reason—𝑅−1 𝑐𝑐 is estimated from limited data, so𝑏𝑘 andS 𝑘 overfit—and both apply the same cure, a convex damping by𝛾∈ [0,1]: 𝑏𝑘 (𝛾)=𝛾 𝑏 𝑘,S 𝑘 (𝛾)=(1−𝛾)𝑅 𝑘 𝑘 +𝛾S 𝑘.(2) At 𝛾=1 thisisfullconditioning—theexactGaussianlikelihood,theminimum-varianceportf …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
