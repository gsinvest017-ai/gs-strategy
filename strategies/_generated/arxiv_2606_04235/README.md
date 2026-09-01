# A Certified Higher Order Quantum Framework for CSA and Margin-Aware Collateral Optimization

Auto-generated bundle from `arxiv:2606.04235`.

Template: **mean_reversion**

Matched keywords: `overshoot`

Paper URL: http://arxiv.org/abs/2606.04235v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.04235",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.04235")`.

### Auto-retrieved passages

- **p.13** (BM25 -9.626):
  > Certified Higher-Order Quantum Candidate Generation 13 Table 5.Higher-order collateral hyperedges and quantum optimization meaning. Term Meaning in collateral allocation xixjxk Three selected collateral blocks jointly exceed an is- suer,rating,currency,orcustodianpressurethreshold. xixjbm Two movements activate the same custody, settle- ment, or triparty batch instructionbm. xixjsd A substitution pair interacts with a surplus slack de- nomination used to absorb CSA rounding excess. xixjxkxℓ A four-action combination crosses an IM segregation, liquidity-stress, or internal concentration threshold.Q i∈G(1−x i)None of the acceptable alternatives in groupGis se- lected. whereC F is funding cost, …

- **p.26** (BM25 -9.602):
  > eduction, funding-cost movement, overshoot, shortfall, and ticket count are all reported after the same CP-SAT gate used in the algorithmic benchmark. These synthetic rows must

- **p.25** (BM25 -8.895):
  > ThesyntheticKPIrowsshouldbereadcautiously.InHIGHER_ORDER_BINDING_16, CP-SAT and CR-HO-QAOA reduce the synthetic objective by 22.04% versus the current allocation and reduce overshoot from USD 50,000 to USD 2,250. In SUBSTITUTION_BATCH_STRESS_20, the greedy allocation is not certified and the

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
