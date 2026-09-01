# Competition in Dealer Markets with Internalisation and Externalisation

Auto-generated bundle from `arxiv:2606.06413`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.06413v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.06413",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.06413")`.

### Auto-retrieved passages

- **p.23** (BM25 -8.587):
  > dealers in a pool of six internalisers for externalisers, on P&L and median client spread, as parameters are varied under the impact-agnostic strategy profile. 23

- **p.24** (BM25 -7.573):
  > Figure 8: The effect of swapping two dealers in a pool of six internalisers for externalisers, on P&L and median client spread, as parameters are varied under the impact-aware strategy profile. This experiment yields two takeaways. First, using the impact-agnostic strategy profile, the existence of the prisoner’s dilemma effect is robust to changes in the model parameters, although the magnitude of the effect varies. 1 Second, we see again that the prisoner’s dilemma effect only exists under the impact-agnostic case, at least as the first two dealers are swapped. A possible explanation for this is the following. The transient price impact acts as a common price signal, but one that is create …

- **p.19** (BM25 -6.998):
  > Figure 4: An example simulation under the impact-agnostic strategy profile with the parameters from Table 1. Four dealers are internalisers and two are externalisers. 3.5 Comparison of dealer combinations: impact-agnostic strategy profile As in the impact-aware case, we wish to compare different combinations of dealers present in the market. The means and 95% confidence intervals of the dealers’ P&Ls, nominal and effective spread captures, hedging costs, hedging volumes, and median client mean spread (all defined in Section 2.1) are given in Table 5 averaged across the two dealer types. We first note that results 1 and 2 also hold under the impact-agnostic strategy profile, and we can also c …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
