# Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures: A Systematic Falsification Study

Auto-generated bundle from `arxiv:2605.04004`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2605.04004v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.04004",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.04004")`.

### Auto-retrieved passages

- **p.1** (BM25 -14.852):
  > Structural Limits of OHLCV-Based Intraday Signals in MNQ Futures: A Systematic Falsification Study Mathias Mesfin Independent Researcher mathiasmesfin.research@gmail.com Research Period: 2024–2026 Manuscript Date: May 2026 Abstract This paper investigates whether intraday momentum signals derived from open-high-low-close-volume (OHLCV) data generate statistically significant trading edge in Micro E-Mini Nasdaq 100 futures (ticker: MNQ) under realistic execution constraints. Using 947 regular trading hours (RTH) trading days of five-minute bar data spanning 2021 through 2025, we construct and systematically test fourteen distinct signal families. These include opening range breakouts at multi …

- **p.2** (BM25 -14.852):
  > Keywords: intraday momentum, futures markets, OHLCV, systematic falsification, walk-forward validation, market microstructure, E-mini Nasdaq, transaction costs, signal development 1. Introduction The hypothesis that short-term price patterns in equity index futures contain exploitable directional information is widely held in retail trading communities and appears frequently in early academic literature on intraday momentum (Gao, Han, Li, & Zhou, 2018; Heston, Korajczyk, & Sadka, 2010). The practical question—whether such patterns survive realistic execution costs on modern, highly liquid instruments—receives considerably less rigorous treatment. Most published retail strategy research suffe …

- **p.8** (BM25 -13.795):
  > Signal Direction N Mean Net (pts) T-Stat Win Rate Volume Spike Momentum Up spike 2,119 −1.94 +0.07 51.6% Volume Spike Momentum Down spike 2,409 −2.50 −0.64 50.1% Volume Dry-Up Exhaustion Up exhaustion 1,060 −2.42 −0.92 47.4% Volume Dry-Up Exhaustion Down exhaustion 723 −1.99 +0.03 49.7% Table 6. Volume signature signal results. All after 2-point friction. Both volume hypotheses fail cleanly. The T-statistics for all four variants are near zero, confirming that volume magnitude at the bar level does not reliably predict next-bar direction. The sample sizes here are large (over 2,000 trades in some variants), which means the near-zero T-statistics are genuine estimates of the population effect …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
