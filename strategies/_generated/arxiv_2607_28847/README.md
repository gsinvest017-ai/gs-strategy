# Effort-Centric Fairness in Lending Decisions

Auto-generated bundle from `arxiv:2607.28847`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.28847v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.28847",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.28847")`.

### Auto-retrieved passages

- **p.10** (BM25 -5.227):
  > hallenge, consider the fairness loss based on feature-independent effort disparity. Substituting the definition of∆FI(θ)from Eq. (5) into the learning objective 10

- **p.51** (BM25 -3.702):
  > ploys theS-twin to assess theeffortrequired to change that prediction. K.1 Individual Effort Parity Group-level criteria ensure thataverageefforts are balanced but permit individual-level disparities. A stronger notion requires that each rejected applicant face the same effort as their counterfactual S-twin. Definition 3(Individual Effort Parity).A classifier satisfiesindividual effort parityif, for every rejected applicantv O∈D−, the minimal causal effort equals that of their counterfactualS-twin: r∗(vO) =r∗(vO S ),∀vO∈D−.(49) This embodies a strong notion of fairness; an individual’s path to approval should not depend on their demographic group membership, conditional on all other causally …

- **p.9** (BM25 -3.494):
  > proval. We quantify such violations via thefeature-independent effort disparity: ∆ FI(θ) = ⏐⏐⏐¯c∗(Ω− 0 )−¯c∗(Ω− 1 ) ⏐⏐⏐.(5) 3.3.2 Causal Effort Parity Analogously, theaverage causal effortfor groupsis: ¯r∗(Ω− s ) = 1 |Ω−s| ∑ vi∈Ω− s r∗(vi).(6) Definition 2(Causal Effort Parity).A classifier satisfiescausal effort parityif the average minimal causal efforts are equal across protected groups: ¯r∗(Ω− 0 ) = ¯r∗(Ω− 1 ).(7) The correspondingcausal effort disparityis: ∆ GC(θ) = ⏐⏐⏐¯r∗(Ω− 0 )−¯r∗(Ω− 1 ) ⏐⏐⏐.(8) 3.3.3 Why Equalise Effort? An effort gap is not by itself evidence of unfair treatment: rejected applicants in one group may lie farther from a risk-based boundary because of repayment-releva …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
