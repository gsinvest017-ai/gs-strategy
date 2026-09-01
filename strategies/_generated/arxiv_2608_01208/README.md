# Climate-Dyna Deep Hedging for XVAs: Model-Based Reinforcement Learning, Residual Climate HVA, and Hedge-Instrument Discovery

Auto-generated bundle from `arxiv:2608.01208`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.01208v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.01208",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.01208")`.

### Auto-retrieved passages

- **p.7** (BM25 -4.333):
  > ct the affected coordinates. The factorbremoves the climate correction from the baseline branch. Masked- softmax regime rows, nonnegative intensities, and absorbing default enforce the state constraints. At updater, the ensembleM r ={(ξ k, ψk)}Kens k=1 represents uncertainty in both the structural and correction parameters. 7

- **p.4** (BM25 -2.938):
  > ndHmax ⊆ H 0 ∪ Hc the largest available universe after maturity, liquidity, and inventory restrictions. Positions inH0 remain fixed;H c is traded only against the liability in (1). Couple the climate and baseline branches on the same one-period shock. Conditional on the pre-trade stateY n, letξcollect the structural climate–financial parameters: scenario probabilities, pass-through and damage coefficients, credit sensitivities, and liquidity dynamics. Both branches useε n+1 ∼P(· | F n)for uncertainty not known attn: Y b n+1 =F b ξ,n(Yn, εn+1), b∈ {0,1},(5) whereb= 1follows the climate-on economy andb= 0freezes documented climate drifts, pass- through, credit and liquidity loadings, and regim …

- **p.3** (BM25 -2.865):
  > trategy and can include convex risk measures and trading frictions [18]. Market impact may make a partial hedge preferable to a full delta hedge [19]. Robust and adversarial variants account for uncertainty in market dynamics [20, 21]. Separate work on multivariate time- series forecasting develops efficient neural architectures such as Kernel-U-Net [22]; such models can support transition estimation but do not themselves solve the hedging problem. The hedging methods above generally train the whole trading strategy. We change only the climate overlay and leave the inherited hedge fixed, so the learned policy prices only the residual climate adjustment. Long climate transitions are rarely ob …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
