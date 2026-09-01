# How to spot outliers: an Ensemble Anomaly Detection Framework

Auto-generated bundle from `arxiv:2606.20079`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.20079v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.20079",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.20079")`.

### Auto-retrieved passages

- **p.22** (BM25 -3.614):
  > 22 The first strategy, Weighted Average Aggregation, computes the ensemble score as a weighted sum of normalized method scores: ScoreA =∑ ( ScoreL × WeightL), where L indexes the active methods and weights are calibrated to reflect method-specific detection profiles. Methods with high precision (low false-positive rates) receive higher weights; methods with high recall but lower precision receive lower weights. The final quality flag is determined by comparing Score_A to empirically set thresholds: Green (< 0.70), Amber (0.70–0.95), Red (≥ 0.95). The second strategy, Voting Aggregation, classifies an observation as anomalous based on the count of methods that individually flag a RED score: V …

- **p.5** (BM25 -3.51):
  > . Section 6 discusses implications for practice and regulation. Section 7 concludes. An Appendix provides additional results for all four datasets. 2. Institutional background and related literature 2.1 Operational Risk in Investment Banking The modern study of operational risk in banking has moved from a primarily regulatory exercise to a substantive empirical literature. Following the original Basel II definition – "the risk of loss resulting from inadequate or failed internal processes, people and systems or from external events" (Basel Committee on Banking Supervision, 2006) – early academic work established that operational losses at financial institutions were larger, more frequent and …

- **p.34** (BM25 -3.208):
  > 34 banks propagate through correlated channels into system-wide risk. By detecting valuation errors before they cascade through reporting chains, capital calculations and hedging decisions, frameworks such as EQAF represent a preventive operational control that, if widely adopted, could reduce the correlation of operational failures across the financial system. We hope this paper contributes to both the academic literature on operational risk and anomaly detection, and to practitioner efforts to raise the quality and reliability of the risk infrastructure on which financial stability ultimately depends. References 1. Aggarwal, C.C., 2013. Outlier ensembles: a position paper. ACM SIGKDD Explo …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
