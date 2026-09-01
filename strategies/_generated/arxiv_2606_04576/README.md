# ReSGA: A Large Tail Risk Model for Learning Value-at-Risk and Expected Shortfall

Auto-generated bundle from `arxiv:2606.04576`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2606.04576v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.04576",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.04576")`.

### Auto-retrieved passages

- **p.32** (BM25 -14.977):
  > 32 Fig 1: Group importance from ReSGA during the out-of-sample period. the concentration is even stronger for mega- and large-cap stocks, with top five groups receiving over 99% importance, whereas the top five groups in small-, micro-, and nano- stocks contribute 91%, 89%, and 94%, respectively. •The ranking of the leading groups shows both stability and systematic variation across different levels of market capitalization. Generally speaking, Low Risk and Momentum are consistently important regardless of the level of market capitalization. This is in- tuitive, as volatility- and beta-related characteristics in Low Risk are closely linked to tail risk, while Momentum captures persistent ret …

- **p.4** (BM25 -14.818):
  > apture cross-sectional variation in downside risk, which is also priced in the cross-section. Building on this insight, we propose a new size-enhanced left-side momentum signal that combines predicted ES with firm size. This signal is motivated by the “too big to fail” phenomenon in the US market: Tail risk in large firms is more likely to reflect compensated systematic risk, whereas similar tail risk in small firms often stems from idiosyncratic fragility. Based on this signal, we propose long-short portfolios for each considered model and find that all proposed non-econometric portfolios exhibit significant alphas relative to the Fama–French five-factor model. Hence, it indicates that our  …

- **p.38** (BM25 -13.307):
  > work, we propose a large tail risk model, ReSGA, which captures the nonlinear relationships between asset characteristics and VaR-ES by accounting for spatial and temporal dependencies among assets. Empirically, using nearly a century of US equity data covering over 40,000 stocks and 153 firm characteristics, we find that ReSGA consistently delivers the best out-of-sample forecasting performance among a broad set of competing models. These forecasting gains are economically meaningful: Trading strategies based on ReSGA forecasts exhibit pronounced left-tail momentum and deliver su- perior long-short decile portfolio performances using a newly proposed size-enhanced left-side momentum signal. …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
