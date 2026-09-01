# Almost stochastic dominance via optimal transport

Auto-generated bundle from `arxiv:2607.28215`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.28215v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.28215",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.28215")`.

### Auto-retrieved passages

- **p.8** (BM25 -8.811):
  > +|g(X)|]<∞} for the set ofE-valued random variables for whichcandgare integrable. We are now in a position to define the central notion of this paper. Definition 3.1.ForX, Y∈ L c,g(E)withE[g(X)]≤E[g(Y)]we define γ∗(X, Y;g) := OTc(X, Y) E[g(Y)]−E[g(X)] + OT c(X, Y) ,(2) with the convention0/0 = 0. Definition 3.2.Letγ∈[0,1]. ForX, Y∈ L c,g(E)we say thatYdominatesXin the sense of(γ, g)-almost stochastic dominance (denoted byX≤ γ,g Y) ifE[g(X)]≤ E[g(Y)]andγ ∗(X, Y;g)≤γ. 7

- **p.7** (BM25 -3.937):
  > thd +(x, y) = (x−y) + so that the corresponding partial order is the classical ordering of real numbers: x≤ d+ yif and only ifx≤y. A natural extension of this is given by a general Banach lattice as described e.g. in the book of Schaefer (1974), see Example A.2. 2.2 First-order stochastic dominance and Strassen’s theorem Throughout this section we consider a partially ordered Polish space (E,≤) with closed order relation. Definition 2.4.For twoE-valued random variablesX, Ywe define X≤ st Y⇐ ⇒E[f(X)]≤E[f(Y)]for all bounded measurable increasingf:E→R. 6

- **p.10** (BM25 -3.887):
  > E) =L d(E). Proof.Note thatcis a quasi-pseudo-metric anddis a metric onE. Furthermore, c(x,0) +c(0,x) =d(0,x) and|g(x)| ≤d(0,x) , soL c,g(E) =L d(E) . Lastly, (X,Y)7→ OTc(X,Y) + OTc(Y,X) is a metric modulo equality in distribution by Lemma 5.1 and Proposition 2.6. The claim follows. We make the following definition, which is a special case of what is considered in M¨ uller et al. (2025). Following the same convention, we use the notationufor the test functions, as they often have an interpretation asutility functionsin applications. 9

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
