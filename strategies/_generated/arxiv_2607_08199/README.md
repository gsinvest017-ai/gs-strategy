# Volatility in Prediction Markets: A Structural Approach

Auto-generated bundle from `arxiv:2607.08199`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.08199v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.08199",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.08199")`.

### Auto-retrieved passages

- **p.26** (BM25 -4.14):
  > e from the training window into a test month, the variance state is carried forward sequentially using only information available before each forecast origin. Parameters are fixed at the beginning of the test month, but the variance state updates as earlier within-contract innovations become observable. Future test observations are never used to estimate that month’s parameters. Boundary conventions.All model families use common numerical conventions near binary bound- aries and near expiration. These conventions are applied uniformly across specifications, so relative performance is not driven by singularities in a particular formula. C. Additional Model-Free Binning Diagnostics This append …

- **p.9** (BM25 -4.101):
  > very retained contract-houri, a volatility forecasthi, equivalently a conditional variance forecasth 2 i . We estimate all specifications in a monthly expanding-window design: each calendar month from September 2021 through April 2026 serves once as the test window, with all earlier observations used for training. This yields 56 out-of-sample test months. A contract may appear in both a training window and a later test month, but no observation from a test month is used to fit that month’s parameters. Parameters are estimated separately for each test month using forecast-origin volume weights. The same weights are used in evaluation, so the reported scores emphasize contract-hours in which m …

- **p.2** (BM25 -3.956):
  > eady improves substantially on those generic benchmarks, DR-AS with concave volume scaling is the strongest closed-form specification, and GARCH+DR-AS is the best overall model. In headline numbers, the one-parameter closed-form structural specification outperforms a plain GARCH(1,1) by34%on the volume-weighted Winkler interval score. Appendix D shows that this advantage is not driven by the active-update definition: when zero-update hours are added back to evaluation, and when the filter is removed from both estimation and evaluation, prediction-market structural variables remain well ahead of generic ARCH/GARCH dynamics. 2

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
