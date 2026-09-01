# Scenario Generation for Time Series and Curves: A Comparison of Nonparametric and Semiparametric Bootstrap

Auto-generated bundle from `arxiv:2606.11859`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.11859v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.11859",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.11859")`.

### Auto-retrieved passages

- **p.23** (BM25 -5.717):
  > tive rates are considered, this amount can be held or reinvested up to𝑇2 without losing value, and is therefore sufficient to cover the payment due on the short position. The strategy thus generates a positive initial inflow without requiring any net future outlay, constituting an arbitrage opportunity. Operationally, the analysis is carried out in two stages. First, the percentage of simulated curves that exhibit non-negative rates at all maturities considered is computed. Subsequently, within this subset, the share of curves that violate the monotonicity condition of the discount factors is determined. The results are reported in Table 11. Method Absence of negative rates Presence of arbit …

- **p.9** (BM25 -3.149):
  > introduces an additional curvature factor and a second decay parameter. Such an extension allows greater flexibility in the representation of the term structure, in particular in cases in which the curve exhibits more than one relevant inflection. In the present work, however, the Svensson model is not adopted. The increase in flexibility offered by such a specification in fact entails an increase in the number of parameters to be estimated and, consequently, a greater complexity of the calibration procedure. In light of the objectives of the analysis, it has been preferred to retain the Nelson-Siegel formulation in the dynamic variant of Diebold and Li, which provides a parsimonious, interp …

- **p.6** (BM25 -2.904):
  > n the notation. Consider 𝑛𝑥 price factors and 𝑛𝑦 rate factors, and define 𝑛 = 𝑛𝑥 + 𝑛𝑦. We introduce the state vector x𝑡 = r𝑡 y𝑡 ! ∈ R𝑛, where r𝑡 ∈ R𝑛𝑥 is the vector of returns of the price factors at time 𝑡, while y𝑡 ∈ R𝑛𝑦 is the vector of levels of the rate factors. In this formulation, the price component is therefore represented in terms of returns, while the rate component is represented in terms of levels. The V AR(1) model is defined as x𝑡 = a0 + 𝐴1x𝑡−1 + 𝜼𝑡, (1) where a0 ∈ R𝑛, 𝐴1 ∈ R𝑛×𝑛 and 𝜼𝑡 ∈ R𝑛 is a vector of zero-mean residuals. Once the model parameters have been estimated on the historical sample, the corresponding residuals are defined as b𝜼𝑡 = x𝑡 −ba0 − b𝐴1x𝑡−1. (2) The simul …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
