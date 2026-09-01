# Trends, Volatility, Correlations, and Critical Phenomena in Financial Markets

Auto-generated bundle from `arxiv:2606.20145`.

Template: **mean_reversion**

Matched keywords: `mean-reversion`

Paper URL: http://arxiv.org/abs/2606.20145v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.20145",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.20145")`.

### Auto-retrieved passages

- **p.1** (BM25 -16.607):
  > uantified by quadratic polynomials of today’s trend strengths, which refine common mean-reversion models of volatilities and correlations. Our results improve the prediction of market risk by accounting for market trends. They also support a recent proposal to model financial markets by a lattice gas near its critical point. arXiv:2606.20145v1 [q-fin.ST] 18 Jun 2026

- **p.1** (BM25 -12.714):
  > Trends, Volatility, Correlations, and Critical Phenomena in Financial Markets Sara A. Safari 1, 2 and Christof Schmidhuber1 1Zurich University of Applied Sciences, School of Engineering, Technikumstrasse 9, CH-8401 Winterthur, Switzerland 2University of Zurich, Department of Mathematical Modeling and Machine Learning (DM 3L), Winterthurerstrasse 190, CH-8057 Zurich, Switzerland June 19, 2026 Abstract We forecast future volatilities and correlations of financial markets based on the current trends in these markets. This complements previous work that models future expected returns by a cubic polynomial of the current trend strength. Empirically, we observe that volatilities and correlations t …

- **p.31** (BM25 -12.459):
  > , 49(3), p.435. [37] Schmidhuber, Christof (2020), “Data for: Trends, Reversion, and Critical Phenomena in Financial Markets”, Mendeley Data, V1, doi: 10.17632/v73nzdt7rt.1 31

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
