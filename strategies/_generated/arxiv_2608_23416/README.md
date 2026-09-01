# The Axiomatic Trader: Latent Regularity, Information Budgets, and the Canonical Form of a Quantitative Investment System

Auto-generated bundle from `arxiv:2608.23416`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.23416v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.23416",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.23416")`.

### Auto-retrieved passages

- **p.2** (BM25 -10.971):
  > . . . . . . . . . . . . . . . . . . . . . . . . . . . . 37 8.4 The third cost: reading regimes through noisy blocks . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 39 9 Sizing: robust Kelly and the half-Kelly fixed point . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 42 9.1 Deploy an ensemble, not a fit . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 43 9.2 When the procedure can return a position at all . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 44 10 The canonical form . . . . . . . . . . . . . . .  …

- **p.42** (BM25 -10.054):
  > criterion class, not an estimation error awaiting a better estimator, and what stays open is a criterion outside that class, not a patch inside it. 9 Sizing: robust Kelly and the half-Kelly fixed point Proposition 9.1 (Robust fractional Kelly). Let the edge estimate satisfy 𝜇̂= 𝜇+ 𝜏𝜎 𝜉 with 𝜉 ∼ 𝑁(0,1) independent of 𝜇, and let the prior over edges induced by the strategy universe be 𝜇 ∼ 𝑁(0,𝑠2𝜎2). A bettor taking ℎ= 𝑓𝜇̂/𝜎2 attains expected log growth 𝑔(𝑓)= 𝑓𝑠2 − 1 2𝑓2(𝑠2 + 𝜏2)+ 𝑂(𝑓2𝑠4 + 𝑓3(𝑠2 + 𝜏2)3/2), maximised at the growth-optimal fraction of the J. L. Kelly [69] solution, 𝑓⋆= 𝑠2 𝑠2 + 𝜏2. (9.1) Adding Axiom A3 replaces 𝜇̂ by 𝜇̂− 𝜆(Λ)sdblk(𝜇̂), where the dispersion charged is the larger o …

- **p.8** (BM25 -9.367):
  > 𝒵︀, never observed, on a standard Borel space. Write ℱ︀obs 𝑡 = 𝜎(𝑋𝑠,𝑌𝑠−𝐻 : 𝑠 ≤ 𝑡) for the information a trader actually has at 𝑡, where 𝐻 is the label horizon. Definition 3.1 (Strategy). A strategy is a measurable map ℎ: 𝒳︀→ 𝒜︀⊆ ℝ, where ℎ(𝑥) is the signed position taken when the observed feature is 𝑥. A loss is a measurable 𝐿 : 𝒜︀× 𝒴︀→ ℝ. Two families matter: the predictive loss 𝐿(𝑎,𝑦)= (𝑦 − 𝑎)2 and the economic loss 𝐿(𝑎,𝑦)= − log(1+ 𝑎𝑦) or its mean–variance approximation −𝑎𝑦 + 𝛾 2𝑎2𝑦2. All results below hold for any 𝐿 bounded on the relevant range, and we write 𝑀 ≔∥ 𝐿 ∥ ∞ ; boundedness is a real restriction and we return to it in §13. 3.1 Past and future Fix an estimation window {1,…,𝑛} (“ …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
