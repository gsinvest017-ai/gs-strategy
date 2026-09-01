# Asymmetric Nonlinear Return Extrapolation and Optimal Portfolio Choice under Stochastic Volatility

Auto-generated bundle from `arxiv:2606.10805`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.10805v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.10805",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.10805")`.

### Auto-retrieved passages

- **p.17** (BM25 -4.404):
  > te value than its myopic counterpart across the bulk of the sentiment domain. Third, the sentiment-hedging demandω∗ S always carries the opposite sign ofX, acting as a partial stabilizer that offsets the aggressive myopic position. Following a sequence of positive price shocks, the investor subjectively anticipates that sentiment will mean-revert toward zero, implying that the current elevated expected return is transient. The sentiment-hedging demand consequently paring down the long position to hedge against this anticipated decay. This in- tertemporal hedging channel is quantitatively non-trivial. Atv= ¯v, the sentiment-hedging component peaks in absolute value at intermediate sentiment l …

- **p.7** (BM25 -4.37):
  > try. The second term,ω∗ V, is the standardvariance hedging demandfamiliar from Merton (1971) and developed in the stochastic-volatility context by Liu (2007) and Chacko and Viceira (2005). Withρ <0andΨ v >0forγ >1, the term is negative: it reduces the total long position relative to the myopic component, exploiting the negative return–variance correlation to limit exposure to adverse variance shocks. This sign is consistent with the analysis of Liu (2007) for CRRA investors withγ >1under negative leverage correlation. The third term,ω ∗ S, is asentiment hedging demandthat is novel to the present framework. BecauseXpredicts future investment opportunities through its effect on the perceived d …

- **p.13** (BM25 -4.134):
  > ork com- bined with policy iteration (PINN-PI). While the algorithmic details are deferred to Appendix B, we highlight that cross-validating these two structurally distinct methods guarantees the relia- bility of our numerical solutions. Building on this robust foundation, we subsequently analyze the optimal portfolio decomposition, evaluate the welfare costs of asymmetric extrapolation, and explore parameter sensitivities. 5.1 Parameter Values Throughout the numerical analysis, we use the parameter values reported in Table 2. Rather than calibrate these parameters to a specific dataset, we adopt values that are standard in the relevant literature to produce broadly informative baseline resu …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
