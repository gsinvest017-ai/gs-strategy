# Machine Learning-Based Bitcoin Trading Under Transaction Costs: Evidence From Walk-Forward Forecasting

Auto-generated bundle from `arxiv:2606.00060`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.00060v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.00060",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.00060")`.

### Auto-retrieved passages

- **p.7** (BM25 -8.885):
  > maker–taker order routing, or time-varying bid–ask spreads; transaction-cost sensitivity is therefore examined in Section 6.2. The baseline sign rule can generate excessive turnover because hourly forecasts often fluctuate around zero. A cost-aware execution filter is therefore introduced. Letpos∗ t denote the position implied by the sign of the forecast and letpost−1 denote the current position. The strategy updates the position only if the forecast magnitude is large enough to compensate for the transaction cost implied by the trade: |ˆrt+1|> λ·c· |pos ∗ t −pos t−1|,(5) where λ > 0controls the strictness of the filter. If condition(5) is satisfied, the strategy moves to the forecast-implie …

- **p.29** (BM25 -8.202):
  > 25 basis points should not be interpreted as transaction costs improving the strategy. It reflects the endogenous regeneration of the position path: a higher cost assumption raises the execution hurdle, suppresses additional trades, and can therefore avoid some losing position changes. The broader pattern remains clear: higher effective costs reduce trading activity and weaken risk-adjusted performance relative to the low-cost cases. The long-short results are more fragile. Performance is strongest at 0 basis points and remains positive at 5 and 10 basis points, but the strategy becomes sparse at higher costs. At 15 basis points and above, the long-short rows fall below the 20-trade threshol …

- **p.29** (BM25 -7.173):
  > t strategy with OHLCV+TA+EGARCH features, MSE loss, andλ = 2.0. Positions are regenerated separately for each transaction-cost level. ARC, ASD, and MD are percentages; MLD is reported in years; SR, IR∗, and IR∗∗ are ratios. Bold values indicate the strongest reliable outcome within each mode.† denotes fewer than 20 trades; these rows are descriptive and excluded from formal conclusions. The results show that transaction costs materially affect performance, but the adaptive cost-aware filter prevents the strategy from collapsing immediately as costs rise. In the long-only case, ARC falls from 82.51% at 0 basis points to 65.34% at the main 10 basis point assumption, and remains positive throug …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
