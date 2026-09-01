# SHARC: SHAP-Based Interpretability in Machine Learning Risk Models for Regulatory Capital under ICAAP and CCAR

Auto-generated bundle from `arxiv:2607.05484`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.05484v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.05484",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.05484")`.

### Auto-retrieved passages

- **p.5** (BM25 -6.469):
  > 3. Methodology 3.1 Framework Foundation The SHAP analysis is applied to the Hybrid GPR-HS framework documented in Vadrevu, (2026a) and its stress testing extension developed in Vadrevu, (2026b). These works describe the full GPR architecture, kernel specification, Aggressive Noise Initialization (ANI) strategy, scenario construction methodology, Scenario-Averaged Covariance Stabilization (SACS) framework, and SVaR calculation. This paper focuses on the SHAP-specific methodology, formalised as the SHARC (SHAP for Regulatory Capital) framework, and its interpretation within a regulatory capital context. 3.2 SHAP Axiomatic Framework and Regulatory Mapping The four SHAP axioms are formally mappe …

- **p.1** (BM25 -6.276):
  > ramework fidelity and enabling auditable traceability of capital drivers. Second, under stress conditions, the mean return component (directional loss magnitude) dominates the variance component (volatility baseline) in determining capital levels, revealing a non-linear structure with direct implications for capital limit-setting, position management, and hedging strategy design. The results establish SHARC as a regulator-aligned explainability layer that transforms the Hybrid GPR-HS framework into a fully auditable capital engine, consistent with the transparency requirements of FRTB, ICAAP Pillar 2, and CCAR model documentation standards. Keywords: SHAP, SHARC, Explainable AI, Regulatory C …

- **p.10** (BM25 -4.473):
  > y directional loss magnitude rather than volatility expansion, then variance-reducing hedges (such as options positions) may not reduce the SVaR-based capital requirement as effectively as directional position reductions. Second, it validates the application of SHAP to SVaR rather than to base-case VaR. The mean dominance effect is specific to the stressed context, emerging because the scenario conditions the model on extreme directional losses. A SHAP analysis of base-case VaR would not reveal this pattern, as the base-case mean returns are approximately zero and the variance component would instead dominate the decomposition. The SVaR context is therefore not merely convenient, but the ana …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
