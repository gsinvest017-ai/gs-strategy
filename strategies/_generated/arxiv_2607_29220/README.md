# Decoupled Probabilistic Forecasting and Arbitrage-Aware Refinement of Implied Volatility Surfaces

Auto-generated bundle from `arxiv:2607.29220`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.29220v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.29220",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.29220")`.

### Auto-retrieved passages

- **p.4** (BM25 -3.525):
  > ally useful, and the refinement stage developed in this paper also adopts residual based regularization for static no-arbitrage restrictions. The main limitation is therefore not the use of soft penalties per se, but the frequent reliance on pointwise mappings such as multi layer perceptrons. In these coordinate to volatility architectures, the output at each target coordinate is generated mainly from local input features and is only indirectly coupled with other surface regions through shared parameters and global loss terms. This can be restrictive for IVS refinement, since option smiles, term structures, and static no-arbitrage conditions are intrinsically cross sectional. 4

- **p.8** (BM25 -3.287):
  > butional evalua- tion, while its pointwise median provides a robust representative forecast for Stage II. Stage II refines this representative surface against scattered market observations. Its training objective combines data fitting with residual regularization for the calendar, butterfly, and wing diagnostics evaluated on synthetic collocation grids. This decom- position separates conditional distribution learning from surface refinement, allowing the diffusion model to capture stochastic market dynamics while SAAM improves fit to market observations and reduces finite-grid static no-arbitrage residual violations for the final representative surface. 4.1 Stage I: Conditional Scenario Gene …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
