# Semi-Analytical Pricing for General Default Intensity Models

Auto-generated bundle from `arxiv:2606.21800`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.21800v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.21800",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.21800")`.

### Auto-retrieved passages

- **p.4** (BM25 -5.837):
  > DE numerically. The parameters of the process, relevant for a stressed market scenario, are: mean-reversion speedk= 0.1, levelθ= ln 0.04, volatilityσ= 0.85, and initial default rate h0 = 0.06. Absolute errors with respect to the PDE results are shown in parentheses. In the first equation in Eq. (29),ω(¯x) appears in both the left-hand-side and, implicitly, throughαandδ γ, as defined in Eqs. (20) and (23), in the right hand side. The termδ γ also couples the first two equations which, there- fore, must be solved simultaneously. In fact, it is more convenient to solve simultaneously forωandδ γ, which are bothtime-independent, by using the first equation and the definition ofδ γ, Eq. (23), wher …

- **p.6** (BM25 -2.873):
  > nough to calibrate to market quotes for the domestic and for- eign currency CDS spreads even in regimes of stress, such as the European sovereign debt crisis of 2011 and 2012. In that study, the authors relied on a fully numerical solution of the pricing PDE for the calculation of CDS spreads. Here we also calculate survival probabilities us- ing our GTFK approximation for the BK dynamics. In particular, for the foreign currency measure, we can set λ= 1+Jand employ the simple modification of the mean reversion function in Eq. (34). The results obtained, for a set of parameters relevant for the 2011-2012 sovereign debt crisis, are shown in Table. IV. They demonstrate that the GTFK approximati …

- **p.4** (BM25 -2.843):
  > θ min, θmax] andη(t) = PNl−1 i=0 1(t≥t i), with ti =iT /N l. We see that the GTFK approximation pro- vides extremely accurate results up to very large matu- rities and volatilities. Table I illustrates that, in the time-homogeneous case, the GTFK method compares favorably with the re- sults obtained with other semi-analytical approxima- tions, namely the Exponent Expansion (EE) (Stehl´ ıkov´ a and Capriotti, 2014), and the Karhunen-Lo´ eve (KL) ex- pansions (Daniluk and Muchorski, 2016) when bench- marked against a numerical solution of the associated PDE. We have considered parameters that are relevant for periods of stress,e.g., with an implied 3-months out- turn volatility∼84%. For short  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
