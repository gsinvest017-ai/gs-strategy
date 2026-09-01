# The Market's Conditioning Representation: Equilibrium, Crowding, and Convention Multiplicity

Auto-generated bundle from `arxiv:2608.18299`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.18299v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.18299",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.18299")`.

### Auto-retrieved passages

- **p.7** (BM25 -8.91):
  > , and a cause of the realised return. Conditioning on the established position is admissible under the stated timing because the position precedes the return innovation. By contrast, conditioning on a common effect can open a collider path. The distinction is therefore determined by timing. Proposition 1(When conditioning on the aggregate position is collider safe).Letrt+1 = µ0(zt) + I(Ft) + εt+1 with Ft measurable with respect to the decision setGt of Definition 5. Conditioning on Ft leaves the residual equal toεt+1, and preserves the immersion of the driver filtration in the price filtration, if and only if the aggregate position isconditionally mean independentof the innovation, E  εt+1  …

- **p.36** (BM25 -8.58):
  > Table C.8:Map of the results. The table separates results proved here from results whose mathematical engine is an existing theorem; the last column records the proof route. Result Establishes Status and proof Definition 1 representation, induced exposures, potential new; the response operator is the only bridge between the two spaces Definition 4 one price equation, its transitory and persistent readings new; inventory pricing in the sense of Grossman and Miller (1988) Definition 5 decision, return and certification information sets new; in text Theorem 1 clearing premium, its closed form, the crowding discount new; appendix Theorem 2 uniqueness under concave impact monotone operator theory …

- **p.18** (BM25 -7.462):
  > Definition 4(Positions, trades, and the price).Ft ∈R n is the aggregatepositionof the conditioning population, holdings and not order flow; the trade over a period is the changeFt+1 −F t. The price carries a concession proportional to the inventory the rest of the market must absorb, pt =v t +I(F t),(19) with vt the fundamental value andI the impact map of Assumption 1. The excess return over a period is the price change plus the fundamental payoff. Terminology is fixed as follows.Positiondenotes the standing holding Ft;tradeis its change Ft+1 −F t;demandis the map from the premium to the desired position,µ7→ ¯Aµ; andorder flow, the signed volume that a microstructure dataset records, is the …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
