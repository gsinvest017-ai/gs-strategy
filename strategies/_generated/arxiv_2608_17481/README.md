# A generic nonparametric value-at-risk estimator for high dimensions

Auto-generated bundle from `arxiv:2608.17481`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.17481v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.17481",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.17481")`.

### Auto-retrieved passages

- **p.2** (BM25 -7.634):
  > rithm for an ensemble of 500 portfolios with random positions across 49 different futures of different expirations, in VIX, equity indexes, government bonds, interest rates, and the main liquid commodities (energy, livestock, agriculture, softs). We test 9 different variations of the algorithm’s input parameters to confirm the stability of results for a wide range of inputs. By definition, 1 percent of all days should experience a loss that exceeds the 99% daily VaR. This translates to roughly 2 to 3 days per year and should be directly observable. 95% of the 500 portfolios have between a 0.5% to 1.5% rate of loss exceeding the 99% VaR estimate. 68% of all portfolios have a 0.7% to 1.3% rate …

- **p.12** (BM25 -7.497):
  > would happen if the trading strategy is wrong?" It is therefore dangerous to answer this question according to how successful the strategy was in the past. Analyzing risk based on past behavior of the position alone, without relying on the trader’s selection power, is the algorithmic embodiment of the physical separation of the risk management and alpha-generating departments within an organization. All risk managers should be skeptical if a trader approaches with the argument “Trust me, I was right in the past, and so my current positions are not risky." Likewise, risk estimation algorithms should be skeptical of past performance (or worse, back-tested past performance) as an indicator of l …

- **p.14** (BM25 -6.321):
  > y light and needs no a priori knowledge of the underlying asset classes. Hence, the algorithm can serve as a benchmark VaR estimator in the absence of any manual analysis of the specific assets or the complex relationships between assets in high-dimensional space. We tested the algorithm with an ensemble of 500 portfolios with daily random positions in 49 different liq- uid futures, expiration combinations (long/short, front+back expiry, VIX, equity indexes, government bonds, interest rates, energy, metals, livestock, agriculture, and softs) in section 5 and 6. All VaR estimation is made blind to the future at all points in time. The algorithm is accurate for this high number of instruments  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
