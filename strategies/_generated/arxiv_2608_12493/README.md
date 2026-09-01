# Beyond the Skew-Stickiness Ratio: Transport Geometry of Spot-Driven Variance Surface Dynamics

Auto-generated bundle from `arxiv:2608.12493`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.12493v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.12493",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.12493")`.

### Auto-retrieved passages

- **p.4** (BM25 -5.139):
  > n motivates the following definition. Definition 2.1.An infinitesimal perturbationhis said to be admissible atw∈ Aif there exists ε0 >0 such thatw+εh∈ Afor every|ε|< ε 0. Thus, admissible perturbations preserve static arbitrage to first order. 2.4 Explicit Form of the Admissibility Conditions For the purposes of the dynamic theory we shall need explicit analytic forms of the static no- arbitrage conditions. Definition 2.2(Strictly admissible variance surface).A functionw∈C 2,1(R×R +) isstrictly admissibleif w(k, T)>0 for all (k, T),(2.1) ∂T w(k, T)>0 for all (k, T) (no calendar arbitrage),(2.2) g[w](k, T)>0 for all (k, T) (no butterfly arbitrage),(2.3) where the Gatheral density functional i …

- **p.15** (BM25 -4.957):
  > filev(k). Definition 5.11(Local variance jet).Forw∈C N+1 inkneark 0 ∈R, thelocal variance jet atk 0 is b(k0) n (u, T) :=∂ n k w(k0, u, T), n= 0,1, . . . , N,(5.18) 15

- **p.4** (BM25 -4.746):
  > Rather than writing these constraints explicitly at this stage, we denote byAthe collection of all variance surfaces satisfying the required static arbitrage conditions. Accordingly, A={w(k, T) :wis free of static arbitrage}. The precise characterization of these conditions will be recalled in Section 2.4. Our objective throughout the remainder of the paper is not merely to describe motions of variance surfaces, but to characterize dynamics which remain entirely within the admissible classA. 2.3 Infinitesimal Perturbations Consider a one-parameter family of variance surfaces wε(k, T) =w(k, T) +εh(k, T) +o(ε). The functionh(k, T) represents an infinitesimal perturbation of the original varian …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
