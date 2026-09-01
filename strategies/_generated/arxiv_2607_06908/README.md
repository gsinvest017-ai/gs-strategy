# Iterative detection of global factors near the BBP phase transition

Auto-generated bundle from `arxiv:2607.06908`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.06908v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.06908",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.06908")`.

### Auto-retrieved passages

- **p.15** (BM25 -3.461):
  > (a) (b) Figure 1: Dimension-scaling analysis of the BH factor model. Panel (a) shows the mean of the first ten sample eigenvalues over 100 Monte Carlo replications forp= 200, . . . ,800, with∆p= 10andn= 400. The parameters areσ 2 b = 0.08,σ 2 f = 0.000158,σ 2 e = 0.0045, andb= 1. Shading denotes one standard deviation of the largest sample eigenvalue. The plot also shows the largest population eigenvalue, Harding’s corrections for the first four sample eigenvalues, the Marčenko–Pastur upper edge, and the critical pointpc. Panel (b) shows the weak-factor regime on a semilogarithmic scale. 15

- **p.10** (BM25 -3.274):
  > b + 4b2σ2 b) σ2 e +σ 2 f K(b2 +σ 2 b) .(18) For the parameters used in Sec. IV, we obtainCVD ≈0.0352. Thus, the diagonal entries have a dispersion of approximately3.52%relative to the typical scaled0. C. Iterative recalibration The next element consists of estimating the effective noise levelˆσ2 0 of the factor model from the empirical correlation matrix. For this purpose, we use a procedure inspired by Ref. [25], where robust estimation based on the median is proposed in the context of the singular values of a low-rank rectangular matrix contaminated with noise. The intuition is that the spikes separate from the bulk, while the median is not strongly affected by a finite 10

- **p.7** (BM25 -2.987):
  > in Eq. (2) is of orderO(p−1/3). However, with modified centering and scaling parameters, the approximation error can be reduced toO(p−2/3), which makes the approximation useful for relatively small samples [32]. Astate-of-the-arttestfordeterminingthenumberofsignificantfactorsinhigh-dimensional econometric settings was proposed by Onatski [8, 9]. Onatski showed that the distribution of the firstrcentered and scaled eigenvalues of a complex Wishart matrix converges weakly to ther-dimensional joint Tracy–Widom distribution. This result provides the basis for theRstatistic proposed in Ref. [9] to determine the number of factors in the generalized dynamic factor model (DFM) framework of Ref. [33] …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
