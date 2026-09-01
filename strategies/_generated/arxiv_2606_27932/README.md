# (In)Efficient Market States and Rough Volatility Detected via Grunwald-Letnikov Fractional Derivative

Auto-generated bundle from `arxiv:2606.27932`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.27932v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.27932",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.27932")`.

### Auto-retrieved passages

- **p.4** (BM25 -4.192):
  > From a spectral point of view, the covariance function can be represented asKH(k) = ∫π −πeikλfH(λ)dλ, where the spectral density is fH(λ) = 1 2π ∑ k∈Z KH(k)e−ikλ = sin(πH)Γ(2H+1) π (1−cos(λ))∑ m∈Z |λ+ 2πm|−2H−1, λ∈[−π,π]. (1) WritingCH = sin(πH)Γ(2H+1) π , near zero the spectral density boils down to fH(λ)∼CH|λ|1−2H, λ→0.(2) The fGn inherits the property of self-similarity from the fBm. In particular, a fGn isH−ssin the sense of the finite-dimensional distributions { ZH at,a } t≥0 := { BH a(t+1)−BH at } t≥0 f.d.d. =a H { BH t+1−BH t } t≥0 =:a H { ZH t,1 } t≥0 . From an empirical point of view, testing the previous self-similarity property of a finite fGn process is expensive in terms of the  …

- **p.9** (BM25 -4.185):
  > Proof.To establish (11), we expand the definition of the derivative operator ∆ GL,α h and utilize the intrinsicH-self-similarity of the underlying fBm process (B H at f.d.d. =a HBH t ): ∆ GL,α h BH at = 1 hα ∞∑ k=0 ωk(α)BH a(t−kh) f.d.d. =a H ( 1 hα ∞∑ k=0 ωk(α)BH t−kh ) =a H·∆GL,α h BH t . The core operational breakthrough of this paper relies on applying this filtering technique to the crossed fGn framework defined in Section 2. The next proposition guarantees that filtering the multi-scale branches preserves the exact distributional scaling law required for our test statistic in the finite-dimensional sense. Proposition 3.3.The discrete Gr¨ unwald-Letnikov derivative∆ GL,α h of a crossed  …

- **p.4** (BM25 -4.014):
  > ollowing definition. Definition 2.1.Let { ZH t,a } t≥0 be a fGn with Hurst exponentH∈(0,1]and integer scaling parameter a≥1. AcrossedfGn is defined as GH a,r(t) :=Z H r+at,a =B H r+a(t+1)−BH r+at, r= 0,...,a−1. The unionY H a (t) = a−1⋃ r=0 GH a,r(t)represents the set of all fBm increments with laga. Clearly, fixing a branchr, a crossed fGnG H a,r(t) is anH-ss process: { GH a,r(t) } t≥0 f.d.d. = { BH a(t+1)−BH at } t≥0 f.d.d. =a H { BH t+1−BH t } t≥0 =:a H { GH 1,0(t) } t≥0 . By the previous self-similarity property, the covariance function can be written as KGHa,r(t−s) =E [ ZH r+at,aZH r+as,a ] =E[Z at,aZas,a] =a 2H E [ ZH t,1ZH s,1 ] =a 2HKGH 1,0 (t−s). Therefore, the relation between the  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
