# Sequential Structure in Intraday Futures Data: LSTM vs Gradient Boosting on MNQ

Auto-generated bundle from `arxiv:2605.17724`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.17724v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.17724",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.17724")`.

### Auto-retrieved passages

- **p.3** (BM25 -6.915):
  > (intraday matrix) 30 features including 12-bar sequence Target variable Binary: session close > 10:30 open + 10 pts Base rate (intraday target) 51.80% Table 1. Dataset and pipeline parameters. 2.2 Daily Feature Engineering The daily feature matrix aggregates each RTH session into a single row with 29 engineered features. All rolling statistics use strict no-lookahead construction: for any feature on day N, the rolling window uses only data from days 0 through N−1. Features fall into six categories: return features (daily return, lagged returns at 1, 2, 3, and 5 days, rolling returns at 5, 10, and 20 days), gap features (overnight gap and lags at 1, 2, 3 days), volatility features (rolling re …

- **p.5** (BM25 -6.024):
  > ample to show any directional skill. Year-by-year sample counts are consistent across 2022 (251 days), 2023 (257 days), 2024 (249 days), and 2025 (168 days), confirming no year is structurally underrepresented. The 10-point threshold was selected to represent a meaningful directional move at baseline MNQ volatility (ATR baseline of 10.34 points from Mesfin 2026a). A session close that exceeds the 10:30 open by more than 10 points represents approximately one full baseline ATR of directional movement—a threshold that is economically meaningful for prop firm account sizing while remaining frequent enough (51.80% base rate) to provide sufficient positive examples for model training. 4. Model Ar …

- **p.3** (BM25 -3.458):
  > te return, last-30-minute return, first-bar volume deviation), prior-day features (prior close position, prior range ratio, prior volume z-score), and day-of-week dummies (Monday through Friday). All continuous features are tokenized into decile bins (0–9) using expanding-window quantile boundaries. For day N, the decile thresholds are computed from days 0 through N−1 only, ensuring no future information contaminates the tokenization step. This approach is directly motivated by Kronos’s binary spherical quantization step, which normalizes raw OHLCV values into discrete tokens that capture relative magnitude rather than absolute price levels. Mesfin (2026) | 3

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
