# Infinite Horizon Optimal Consumption: Intertemporal Hedging under Epstein-Zin Preferences

Auto-generated bundle from `arxiv:2606.02945`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.02945v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.02945",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.02945")`.

### Auto-retrieved passages

- **p.15** (BM25 -4.991):
  > Proposition 6.1.The candidate value function ˆV(x,y) = x1−γ 1−γg(y)m with candidate controls(ˆπ,ˆl)(given by(4.3)) satisfies ˆV(x,y) =E   ∫ ∞ 0 (X ˆπ,ˆl t ˆlt)1−δ 1−δ ( (1−γ)ˆV(X ˆπ,ˆl t ,Yt) )1−1 θ dt ⏐⏐⏐⏐X0 =x,Y0 =y  , and hence is the unique solution to the BSDE(3.9)for the candidate controls. Introduce the processZε t =X π,l t +εˆXt, whereε>0,(π,l)∈Aare arbitrary, andˆX is the wealth process under the candidate optimal controls(ˆπ,ˆl)started from unit wealth (i.e., ˆX0 = 1). Then the dynamics ofZεare dZε t Zε t =r+ (πz)⊤dRt−lzdt,(6.1) where (πz t )⊤= Xtπ⊤ t +εˆXtˆπ⊤ t Zε t ;l z t = Xtlt +εˆXtˆlt Zε t = Cε t Zε t . We prove thatˆV(Z ε t,Yt)is a supersolution of (3.9) for the consumpti …

- **p.14** (BM25 -3.776):
  > whereλ= 2 + b a2 + ( 1−1 γ ) ρ aσ> 1 2 andC >0is a normalising constant. It is straight- forward to check that Assumptions 3.1-3.5 hold. The optimal policies are π∗(y) = y γσ2 + aρ(1 +y2) σ(γ+ (1−γ)ρ2) g′(y) g(y) ;l ∗(y) =g(y) −γ (γ+(1−γ)ρ2)δθ. Figure 3: Optimal consumption ratiol∗(y) =g(y) −ν(left panel) and optimal portfolio weightπ∗(y)(right panel) as a function of the state variabley(within a99%confidence interval for the long-run stationary density ofY), for(γ,δ) = (2,9)(dotted lines),(γ,δ) = (2,5)(dashed lines) and(γ,δ) = (4,5)(solid lines). Parameters:r= 0.02,β= 0.05, σ= 0.15,b= 0.50,¯µ= 0.06,a= 0.05,ρ=−0.30. In Figure 3, to facilitate comparison with markets exhibiting fat-tailed exc …

- **p.6** (BM25 -3.323):
  > f “proper” utility processes; the general theory was then applied to solve the optimal consumption problem in a Black-Scholes-Merton market. The caseθ <0was studied in (Dang, 2021; Shigeta, 2026). Next we introduce the class of admissible strategies. Definition 3.1.The set of admissible policies, denoted byA, consists of(Ft)t≥0-adapted processes(π,l)such that: 1.πis integrable with respect toR. 2.l t≥0almost surely fort≥0. 3. There exists a unique strong solutionXπ,lto(3.7). 4.c t =X π,l t lt is progressively measurable. The dynamics (3.7) automatically ensureXπ,l t ≥0almost surely; hence non-negativity of the associated consumption stream is guaranteed. Thus, for any policy pair(π,l)∈A, 5In …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
