# Polymarket-v1 Database

Auto-generated bundle from `arxiv:2606.04217`.

Template: **mean_reversion**

Matched keywords: `mean-reversion`

Paper URL: http://arxiv.org/abs/2606.04217v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.04217",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.04217")`.

### Auto-retrieved passages

- **p.2** (BM25 -16.047):
  > n—a momentum- like behavior that violates the mean-reversion assumption inherent in traditional trade classification models. Second, we show that this systematic classification error propagates into standard execution quality metrics, causing severe distortions in inferred liquidity measures (such as VPIN) and estimates of informed trading. This demonstrates that traditional Transaction Cost Analysis (TCA) reports and sell-side quality assessments, which rely on inferred trade directions, are structurally biased. 1

- **p.2** (BM25 -14.289):
  > nd ground-truth microstructural properties unexplored. To demonstrate the unique value of this dataset as an empirical laboratory, we docu- ment three primary findings that challenge standard market microstructure assumptions. First, we validate standard trade classification algorithms (such as the tick rule and bulk volume classification) against our truth-aligned dataset and document a systematic failure: standard classifiers achieve near-randomoverallaccuracy (49 .83% for the tick rule and 50.51% for bulk volume classification), but this aggregate conceals two opposing system- atic biases that cancel in the mean—classifiers over-predict buys in low-price regions and under-predict them in  …

- **p.1** (BM25 -13.231):
  > 9 .83% and 50.51%), but this masks a systematic, correctable price- level gradient driven by positive trade direction autocorrelation and concentrated market-making – two structural features of prediction markets that violate the mean- reversion assumption embedded in classical classifiers. Second, these classification errors propagate into downstream metrics: inferred VPIN diverges substantially from ground-truth VPIN, and OFI estimates are directionally biased, with material conse- quences for Transaction Cost Analysis. Third, ground-truth microstructure quality predicts forecasting performance in ways that classification-based proxies cannot recover: True VPIN positively predicts Brier sc …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
