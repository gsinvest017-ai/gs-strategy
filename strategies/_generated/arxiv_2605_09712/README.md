# Quantifying the Risk-Return Tradeoff in Forecasting

Auto-generated bundle from `arxiv:2605.09712`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.09712v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.09712",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.09712")`.

### Auto-retrieved passages

- **p.29** (BM25 -2.669):
  > Harvey, D., Leybourne, S., and Newbold, P . (1997). Testing the equality of prediction mean squared errors.International Journal of Forecasting, 13(2):281–291. Hollmann, N., Müller, S., Eggensperger, K., and Hutter, F. (2022). TabPFN: A transformer that solves small tabular classification problems in a second.arXiv preprint arXiv:2207.01848. Kastner, G. and Frühwirth-Schnatter, S. (2014). Ancillarity-sufficiency interweaving strategy (ASIS) for boosting MCMC estimation of stochastic volatility models.Computational Statistics & Data Analysis, 76:408–423. Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q., and Liu, T.-Y. (2017). LightGBM: A highly efficient gradient boosting deci …

- **p.7** (BM25 -2.583):
  > and deteriorations materialize over time: whether gains are stable or erratic, whether losses are concentrated or persistent, and how severe the worst episodes of underper- formance are. 2.2 Risk-Adjusted Forecast Metrics I begin with risk-adjusted performance metrics borrowed from asset pricing and trading-strategy evaluation, introduced in increasing order of sophistication. Forecast Sharpe Ratio.The Sharpe ratio (Sharpe, 1966, 1994) is the canonical risk-adjusted performance measure in finance. I adapt it to forecast evaluation by defining the Forecast Sharpe ratio as Sharpe= ¯r sr , wheres 2 r = 1 T−1 T ∑ t=1 (rt − ¯r)2. This measure captures the average reduction in loss per unit of vol …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
