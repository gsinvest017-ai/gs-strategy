# Functional integration by parts formulae for stochastic Volterra processes

Auto-generated bundle from `arxiv:2605.30068`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.30068v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.30068",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.30068")`.

### Auto-retrieved passages

- **p.12** (BM25 -5.422):
  > f strategy of the IBP formula consists in deriving it first forC 1 b,X,Lip (X) test functions and then extending by density to a space of less regular functions. We define for that purpose our targetted space of test functions, which is a weighted space inspired by the theory of generalized Feller processes [CMT26]. We fixγ∈(0, H) andp≥1 (recall thatX x −xhasγ–H¨ older trajectories almost surely for allγ∈(0, H)). Recall thatC γ ∞ is the space ofγ-H¨ older continuous functions equipped with the supremum norm∥·∥ ∞. We then define the weight functionϱ:C γ ∞ →R + as ϱ(x) := 1 +∥x∥ p γ .(2.14) As explained in [CST26, Example 2.3 (iv)], this guarantees that for anyR >0 the setsB R :={x∈ Cγ ∞ :ϱ(x) …

- **p.6** (BM25 -3.924):
  > thods, especially when the payoff is not differentiable and finite-difference methods fail [FLL +99, FLLL01, Ben01, GKH03, Gob04, GM05, CF06]. 2In the power-law caseKσ(t, s) = (t−s)H−1/2 1 s<t the latter condition restricts the range of parameters toH∈(1/4,1), see Remark 5.9 of [GP25] for an intuitive explanation. This condition can be dropped if the noise is additive.

- **p.5** (BM25 -3.693):
  > are aware, has not been given a name yet. It is nevertheless related to the notion of “forward Vega” used to denote the sensitivity to a shock in the volatility instruments (e.g. variance swaps) used to hedge one’s position. 1.3. The motivation for functional derivatives.The feedback from its past states makes a stochastic Volterra process inconsistent in time when viewed only from its own finite-dimensional state space. For an illustration, let us look at the following example where we setx(t)≡x 0 andb≡0

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
