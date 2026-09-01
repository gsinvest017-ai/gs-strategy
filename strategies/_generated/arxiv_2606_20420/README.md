# Advanced Calibration Analysis and Tools: Identifying Influential Observations in Stochastic Interest Rate Model Calibration

Auto-generated bundle from `arxiv:2606.20420`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.20420v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.20420",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.20420")`.

### Auto-retrieved passages

- **p.24** (BM25 -5.582):
  > Figure 5:PCA Biplot of Calibration Parameters.The points represent daily calibrations colored by year. The vectors (arrows) indicate the loading of the original parameters on the principal components. ThehorizontalPC1capturesmarketvolatility(σ x,σ y), whiletheverticalPC2captures structural parameters such as mean reversion and correlation. 24

- **p.26** (BM25 -4.82):
  > This vertical expansion indicates that the structural parameters, which were previously relatively stable, began to fluctuate more strongly. This period of expansion in the PCA space closely aligns with the increased switching observed in the Effective Degrees of Freedom (Figure 4), marking a phase in which the calibration more frequently moved between interior and boundary solutions. The 2025 data consolidates into a vertical cluster, where the amplitude of the daily variation along PC2 has significantly decreased compared to the 2022–2024 phase. This indicates a marked shiftinthecalibrationmechanics: inthecurrentmarketenvironment, thevolatilityscaleisrelatively stable, while the daily fluc …

- **p.7** (BM25 -4.75):
  > analyze the stability and uncertainty of the resulting calibration. 2.4 The Challenge of Non-Linearity While the optimization problem above provides a point estimateˆΠ, the relationship between model parameters and observable market prices is inherently non-linear, and this non-linearity poses sub- stantial conceptual and numerical challenges. To illustrate this point, it is useful to contrast the calibration problem with standard linear regression. In a linear setting, model outputs depend linearly on the parameters, and the resulting least-squares problem admits a unique global minimum with well-understood statistical properties. Small changes in the data lead to small and predictable chan …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
