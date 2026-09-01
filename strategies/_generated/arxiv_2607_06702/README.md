# Dynamic Causal Portfolio Choice: Hedging the Rotation of the Common-Driver Manifold

Auto-generated bundle from `arxiv:2607.06702`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.06702v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.06702",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.06702")`.

### Auto-retrieved passages

- **p.14** (BM25 -5.932):
  > ose value jumps at switch times has a nonzero purely-discontinuous component, whose L2 distance to the continuous subspace is bounded below by its own norm, so no trading strategy attains it. This unhedgeability is aninstantaneousstatement and must not be confused with unpre- dictability of the switch’sarrival. Kunita–Watanabe orthogonality says a position heldacrossa switch cannot offset the jump: at the instant it occurs, the geometry jump has zero covariation with the traded assets, so no static hedge neutralizes it. It does not say the arrival time is unforecastable. Indeed the online detector of Theorem 3.10 exploits exactly the compensator λk·(Z): the switch intensity is F Z-adapted, s …

- **p.5** (BM25 -5.219):
  > ss assumption of the static theory and rules out the degenerate unbounded-position limit discussed after Theorem 3.6). With a riskless rate rf, wealth Wt and tangent-admissible weightsw t ∈ WwithCw= 0, wealth followsdW/W= [r f +w ⊤(µ− rf1)] dt + w⊤BσZ dW Z + w⊤ diag(ς) dW idio. Let J(W, z, t) = supE [U(WT ) |W t = W, Zt = z] over tangent-admissible controls. Theorem 3.4(Myopic plus manifold-hedging decomposition).Suppose J∈C 1,2,2 solves the Hamilton–Jacobi–Bellman equation 0 = sup w:Cw=0 n Jt+JW W[r f +w⊤(µ−rf1)]+ 1 2 JW W W 2w⊤Qw+W w⊤BΛZJW z+J ⊤ z α+ 1 2 tr(ΛZJzz) o (5) with polynomial growth. Then the optimal feedback control is w∗ t = 1 Rt MC(µ−r f1) | {z } myopic tangent fund +M CBΛZψt| …

- **p.28** (BM25 -4.731):
  > an be identified from data, is established in [ 1]; here it is a maintained assumption. Definition A.2(Structural causal separator).The driversZform a structural causal separator for the returns r if there is a structural map r = f(Z, ε) in which both Z and the idiosyncratic innovation ε areroot exogenous noisesof the structural model, so that ε and Z are independent under the joint law and, being roots, remain independent under any intervention on the mechanisms of other variables; the map f is invariant to interventions on the environment, meaning interventions that alter the marginal law of Z or of variables outside the pair ( Z, ε) but leave f and the root exogeneity of Z and ε intact. U …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
