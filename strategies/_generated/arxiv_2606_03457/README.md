# Hybrid News Sentiment Engine: Real-Time Market Analysis via Adaptive Ensemble Learning on News-Price Pairs

Auto-generated bundle from `arxiv:2606.03457`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.03457v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.03457",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.03457")`.

### Auto-retrieved passages

- **p.5** (BM25 -2.671):
  > Tradeflags NewsFeed API ↓ Ingest •Poll API •Dedup (exact hash+fuzzy trigram) •Write to MySQLnews_events ↓ Score •Createsentiment_signalsrows •Run FinBERT lexicon scorer •Run statistical cluster lookup •Compute ensemble score ↓ Calibrate (every 6h) •Fetch current ES price •Compute realizedpc_esf •Compute signal—realized correlations •Adjust ensemble weights •Detect market regime ↓ HTML Sentiment Gauge Figure 1: Pipeline architecture. The ingest and score stages run every 3 hours; calibration runs twice daily. 3.3.4.calibration_history Stores the rolling calibration record. Each row is a 7-day calibration window containing the Spearman correlation of each signal against realized price moves, t …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
