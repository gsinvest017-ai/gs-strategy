# NatPar: Natural Parametric Modeling

Auto-generated bundle from `arxiv:2608.24871`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.24871v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.24871",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.24871")`.

### Auto-retrieved passages

- **p.15** (BM25 -4.165):
  > ted as the residual basis they leave behind, which is why in the empirical results curvature reshapes the continuous price but not the binary one. The problem becomes over-determined only if one demands moreindependentexact conditions than parameters: with two triggers a second exact condition (e.g. matching loss TVaR 0.95) uses the last degree of freedom, and a third leaves no exact solution. The design rule is that exactly-satisfiable conditions must not exceed free parameters; each added parameter (a free cap, a multi-layer attachment, an extra trigger) buys one more, which is also what lets a richer penalty curvature express itself. Two well-posedness points complete the picture. First,  …

- **p.15** (BM25 -4.15):
  > 5.3 Determinacy: parameters, conditions, and well-posedness The loss-minimisation (1) has as many free parameters as the payout provides: two for the linear ramp (s, e) (equivalently (d, q) for the continuous frost design), one for the binary trigger. How manyexactaveraging conditions a price can satisfy is bounded by that count. The symmetric-linear corner imposes one condition (E[P] = AAL, Remark 2); a two-parameter contract therefore retains one degree of freedom, which any asymmetry in weight or curvature spends on shaping the basis: min (s,e) λE[ϕ −((L−P) +)] + (1−λ)E[ϕ +((P−L) +)] (soft budgetµ|E[P]−AAL|).(2) Generically this has an isolated (locally unique) solution. The single-trigge …

- **p.35** (BM25 -3.945):
  > capped, it is capped in a way that concentrates the unspanned component into the shortfall side whenever exposure-driven severity dominates. The same conclusion holds under the occurrence (OEP-style) lens. The occurrence view is the one that bites for suitability and operational stress: even if the aggregate mismatch nets out across assets in some years, a single region can still experience a large shortfall. That is why, in addition to reporting the aggregate basisS B =P r Br, we recommend an occurrence basisM B := maxr Br as a regulatory object. Importantly, this definition should be based on the per-asset basis terms 35

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
