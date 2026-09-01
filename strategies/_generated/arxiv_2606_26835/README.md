# A sharp order-three obstruction to the aggregation of conditional price-of-risk attribution

Auto-generated bundle from `arxiv:2606.26835`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.26835v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.26835",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.26835")`.

### Auto-retrieved passages

- **p.10** (BM25 -8.67):
  > t masking—a single field or pair that reveals a future innovation—breaks immersion but is detected by a lower-order screen. Table 2 summarizes the two models. Table 2: The two ingredients across the two models. Model Masking Anticipation Immersion failure Theorem 17 (external revelation) yes yes yes Crowding (Definition 19) yes no no Definition 19(Discrete crowding model).On (Ω,F,P) fix a two-date filtrationF 0 ⊆ F 1. Let s1, s2, cbe independent Rademacher (±1, fair) random variables, allF 0-measurable, and set the third desk’s position by theF 0-measurable hedging rules 3 :=s 1s2c. LetR >0 be a strictly positive random variable withER 2 <∞,F 1-measurable and independent of (s 1, s2, c). At  …

- **p.12** (BM25 -6.661):
  > zed premium versus inadmissible diagnostic premium).Let a portfolio have excess-return incrementdr t =σ tλt dt+σ t dWt withσ t >0andG t-measurable.(i) TheG-measurable positionϕ ⋆ t =E[λ t | G t]/σt realizes expected premiumE R T 0 ϕ⋆ t drt =π(G); the attainable projection is exactly what an information-responsive strategy realizes.(ii)IfGis ad- missible(F,→ G), this isadmissible realized premium: intervention-stable up to the confounding wedge of Theorem 10, and no strategy realizes premium from future information.(iii)If a pooled book filtration fails admissibility through the order-three masking relation of Theorem 17, then the same algebra, applied to the pooled signalε 1ε2ε3 =Z, computes …

- **p.2** (BM25 -3.52):
  > the identification assumption) from the generic-nonzero converse (Theo- rem 11, requiring faithfulness). Third (Sections 4–5), it identifies a minimal order-three obstruction to admissible aggregation that is invisible to every singleton and pairwise screen: each one- and two-driver sub-book is immersed while the pooled book reveals a future innovation, the filtration- theoretic analogue of Bernstein’s pairwise-but-not-mutually-independent triple, minimal relative to pairwise diagnostics (Definition 16, Theorem 17). Fourth, it separates masking from anticipation (Remark 18): adapted crowding reproduces the algebra of the obstruction without breaking immer- sion, so the obstruction requires b …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
