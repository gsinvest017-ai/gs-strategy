# Retail Trader's Ruin: An Anatomy of Popular Signal Failure

Auto-generated bundle from `arxiv:2607.20093`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.20093v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.20093",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.20093")`.

### Auto-retrieved passages

- **p.10** (BM25 -14.722):
  > lied to five catalogue-representative retail signal families plus a diversified momentum calibration benchmark, we find four of six candidates REFUTED (oscillator, volume, calendar, candlestick), two INCONCLUSIVE (trend, momentum), and none SUPPORTED on our sample:H 1 (at least one of the five families is SUPPORTED on all three gates) is rejected, andH 2 (the momentum benchmark is SUPPORTED on gate (a) with a Sharpe gap comparable to prior diversified-momentum evidence) is not supported — though Section 7 shows gate (a) is itself underpowered at this sample size for an effect of typical momentum magnitude, and critically, the benchmark lands INCONCLUSIVE rather than REFUTED at every material …

- **p.8** (BM25 -12.397):
  > (log) A. Liquidity-tilted momentum vs matched benchmark Momentum 12-1 decile (CAGR 9.2%) Exposure-matched market (CAGR 6.0%) 0 50 100 150 200 250 300 Month 0.0 0.1 0.2 0.3 0.4 Drawdown B. Momentum-crash risk (max DD 46.4%) E27: Cross-Sectional Momentum Positive Control Figure 2: Left: EU replication grid (six country ETFs×three indicators), Sharpe-gap point estimates and 95% CIs. Right: momentum calibration benchmark’s crash diagnostics — drawdowns amplify sharply under 2x/3x leverage stress, consistent with known momentum crash risk. Heterogeneity.A 62-cell sector- and instrument-level grid (11 sectors×OBV; 17 instruments×3 indica- tors, spanning equities, bonds, commodities, and crypto ETF …

- **p.5** (BM25 -12.16):
  > breakout/channel rules, chart patterns beyond candlesticks, single-name momentum, and guru/copy-trading signals — the latter two are money-management folklore or non-deterministic guru signals, not testable market-timing rules. Momentum calibration benchmark.A liquidity-weighted, long-only top-decile Jegadeesh–Titman 12-1 momentum strategy (Jegadeesh and Titman, 1993), dollar-volume-weighted per Korajczyk and Sadka (2004) rather than naively equal-weighted, on the point-in-time S&P 500 with Shumway (2001) delisting-return cor- rection (Shumway, 2001). This benchmark is run through the identical joint pipeline as the five tested families, so that its own classification is informative about th …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
