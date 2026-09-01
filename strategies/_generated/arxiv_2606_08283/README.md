# Macro Economists in the Machine: A Multi-Agent LLM Framework for Commodity-Related ETF Portfolio Construction

Auto-generated bundle from `arxiv:2606.08283`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.08283v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.08283",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.08283")`.

### Auto-retrieved passages

- **p.24** (BM25 -6.119):
  > of maintaining prompts, validating JSON outputs, and monitoring model behavior. 4.4 Evaluation Window and Sub-Period Definition The evaluation sample contains 124 weekly rebalancing dates from October 2023 through February 2026. Observations before the evaluation window are used only to initialise rolling z-scores and volatility estimates. For descriptive sub-period analysis, we divide the sample into two calendar-based macro regimes. TheRates Peakperiod covers the late-2023 environment, when U.S. policy rates and real yields were elevated and monetary tightening remained the dominant macro theme. TheSoft Landing period covers January 2024 through February 2026, when inflation moderated whil …

- **p.24** (BM25 -3.834):
  > n and are not used by any strategy in forming portfolio weights. The division is useful because it separates a tightening-dominated environment from a later period in which inflation, growth, and rate signals provided less one-sided guidance.

- **p.14** (BM25 -3.737):
  > Macro Economists in the Machine13 ible macro-state interpretation rather than to a larger information set or a different portfolio optimizer. 2.5 Performance Inference in Short Financial Samples A final related literature concerns statistical inference for trading-strategy perfor- mance. Sharpe-ratio comparisons are widely used in empirical asset management, but their sampling properties are nontrivial in short samples and in the presence of serial dependence. Lo (2002) shows that the Sharpe ratio has different asymptotic behavior under different return-generating processes and that the common square-root-of-time annualization rule can be misleading when returns are serially correlated. This …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
