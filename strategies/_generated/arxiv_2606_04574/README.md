# Dynamic Multi-Pair Trading Strategy in Cryptocurrency Markets with Deep Reinforcement Learning

Auto-generated bundle from `arxiv:2606.04574`.

Template: **mean_reversion**

Matched keywords: `statistical arbitrage`

Paper URL: http://arxiv.org/abs/2606.04574v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.04574",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.04574")`.

### Auto-retrieved passages

- **p.19** (BM25 -19.309):
  > interdependent; ex- panding the window smooths the standard deviation, directly altering threshold breach frequencies. Optimizing both simultaneously risks severe data-mining bias and curve- fitting. In sequential optimization, it is methodologically sounder to deterministically lock the physical time horizon first, and subsequently optimize the statistical boundary (Entry Threshold) to fit that constraint. •Exit Threshold = 0.0: Fixed deterministically without optimization because it serves as the fundamental theoretical anchor of the strategy. Statistical arbitrage relies strictly on mean-reversion, meaning that the predictive edge is exhausted exactly when the spread reverts to its histor …

- **p.20** (BM25 -16.731):
  > : Distribution by Entry Threshold Panel B: Median & Mean by Entry Threshold Note: The Stop Loss (SL) multiplier is disabled to evaluate the pure entry signal. Panel A displays the distribution of monthly Sortino Ratios in the one-year In-Sample backtest (2024), while Panel B tracks the mean and median of this distribution. Constant parameters: Exit Threshold = 0.0, Z-Score Window = 168, Pairs = 20. As illustrated in Figure 2, conducting the initial search without a structural Stop Loss reveals the raw predictive power of the mean-reversion signal. Two distinct regions of interest emerge, exhibiting localized peaks in the median Sortino ratio: the 3.0 threshold and the 3.5 threshold. However, …

- **p.7** (BM25 -12.356):
  > icates persistent (trending) behavior. Therefore, only spreads exhibiting anti- persistence (H <0.5) possess the mean-reverting properties required to validate the core premise of statistical arbitrage [33, 34]. 7

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
