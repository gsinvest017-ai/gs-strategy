# Pricing options on illiquid assets using liquid market benchmarks: an application to energy markets

Auto-generated bundle from `arxiv:2607.19030`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.19030v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.19030",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.19030")`.

### Auto-retrieved passages

- **p.12** (BM25 -3.304):
  > notes the rolling average Gasoil-Brent crack spread andV(t, T m) denotes the corresponding historical volatility spread. Clustering these observations groups similar historical crack-spread and volatility-spread configurations at the tenor level, see Figure 2. Figure 2: Scatter plot of the rolling average crack spread ¯S(t, T3) versus the historical volatility spreadV(t, T 3). Each point corresponds to one historical observation date. Colors identify the clusters obtained from thek-means procedure, while black crosses denote the corresponding cluster centroids. 3 Calibration We now turn to the calibration of the processes, with the aim of recovering the parameters introduced in Section 2.1:  …

- **p.9** (BM25 -3.092):
  > me variation). Step 1. Returns and crack spreads.Fix a tenorT m. For each observation date tk ∈ T, define the one-period arithmetic returns rB(tk, Tm) :=B m(tk)−B m(tk−1), r G(tk, Tm) :=G m(tk)−G m(tk−1), for allk= 1, . . . , L. Next, define the crack spread level at datet k and tenorT m as S(tk, Tm) :=G m(tk)−B m(tk), m= 1, . . . , M. This definition is consistent with the cluster-based construction below, since both the crack levels and the historical descriptors are computed from rolling time series constructed using the same rolling procedure for Brent and Gasoil, including identical contract-switching rules. Step 2. Rolling statistical descriptors.Fix a window lengthn∈N. For each date t …

- **p.15** (BM25 -2.962):
  > In practice, however, monotonicity of the cumulative variances is not imposed explicitly during the calibration step, so small local violations may occasionally arise. In such cases, the sequence{V i,m Tm }M m=1 should be interpreted primarily as a discrete set of calibrated marginal variance parameters. The piecewise-constant volatility representation is then an ex-post dynamic reconstruction and is admissible only after enforcing non-negative variance increments. This is done by applying a mild monotone projection to the calibrated total variances before computing the levelsγ i,m. This step should not be interpreted as recovering a unique global arbitrage-free volatility surface; it only r …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
