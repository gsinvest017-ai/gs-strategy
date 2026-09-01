# When Alpha Disappears: A One-Switch Benchmark for Decision-Time Leakage in Financial Backtests

Auto-generated bundle from `arxiv:2605.23959`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.23959v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.23959",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.23959")`.

### Auto-retrieved passages

- **p.13** (BM25 -3.375):
  > anks scores cross-sectionally on day t and holds the top decile with equal weights. Clean reference.In the clean setting, signals are formed after the close of day t, execution occurs at the open of dayt+ 1, and the label is open-to-open: yclean i,t = log Oi,t+h+1 Oi,t+1 ,(1) rtrade,clean i,t = Oi,t+2 Oi,t+1 −1.(2) Feature standardization parameters are fit on the training split only, and graph/relation features are estimated from admissible trailing information only. Clean graph construction.Let m(t) be the calendar month containing day t, and let τm be the first trading day of month m. For each month m, the clean relation graph is estimated once using the 13

- **p.17** (BM25 -3.26):
  > Table 4: Feature-schema summary. The released schema file provides the exact feature names, source fields, rolling windows, and admissibility timestamps. Feature family Clean construction Related protocol variant Raw OHLCV fields Daily open, high, low, close, and volume timestamped by bar availability EXEC_OPENtests use of post-open fields before the open Return and momentum features Trailing returns computed from admissible historical bars Momentum uses fixedret_20; TEMP_CENTERdoes not affect it Rolling statistics Trailing rolling operators using observations no later thant TEMP_CENTERreplaces trailing windows with centered windows Normalization Parameters fit within the training scope of e …

- **p.4** (BM25 -3.241):
  > e controlled violations. They instantiate different ways in which a backtest can preserve chronological train/test splits while changing the effective information set or the assumed execution time. TEMP_CENTER.The clean reference uses trailing rolling operators. TEMP_CENTER replaces them with centered rolling statistics, so a feature at decision time t can depend on observations after t. This is a generic temporal-causality violation: the split remains chronological, but the feature construction no longer respects the decision-time information set. NORM_GLOBAL.The clean reference fits normalization parameters within the training scope of each walk-forward window. NORM_GLOBAL instead fits fea …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
