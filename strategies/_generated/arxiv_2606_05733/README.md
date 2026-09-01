# Zero-Copy Semantic Contagion: An In-Memory Streaming Architecture for Evolving Attention Graphs

Auto-generated bundle from `arxiv:2606.05733`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.05733v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.05733",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.05733")`.

### Auto-retrieved passages

- **p.2** (BM25 -2.954):
  > ll-clock reads at sub-nanosecond granularity without system-call overhead; on AArch64 the analogous CNTVCT_EL0 counter provides comparable resolution. Frozen Sentence Embeddings.We use the distilled MiniLM-L6-v2 model [23, 24], a 384-dimensional encoder of roughly 22 million parameters, served through the sentence-transformers library on the CPU cores of an Apple M2 SoC (AArch64). Embedding latency is ∼8 ms per article. In production deployments this cost can be reduced by INT8 quantisation or by substituting a domain-adapted encoder; we retain the float32 PyTorch path here for deterministic reproducibility. Semantic Clustering Gate.A rolling centroid buffer filters redun- dant headlines in  …

- **p.3** (BM25 -2.954):
  > librate. 5 Graph Construction The initial adjacency is built from three data-driven sources. Co-Mention Adjacency 𝐴cm.A pattern-based entity extractor identifies ticker symbols and company names in each article. 𝐴cm 𝑖 𝑗 counts the number of articles mentioning both𝑖and𝑗. Semantic Similarity 𝐴sem.Per-ticker semantic centroids are computed by averaging MiniLM-L6-v2 [ 23] article embeddings. 𝐴sem 𝑖 𝑗 is the pairwise cosine similarity, thresholded at𝜏 𝑠 =0.35. Return Correlation𝐴 corr.Absolute pairwise Pearson correlation of daily log-returns over the evaluation month. Each matrix is min-max normalised to[0, 1] with zeroed diagonal. The combined adjacency is 𝐴𝑖 𝑗 =𝑤 1 𝐴cm 𝑖 𝑗 +𝑤 2 𝐴sem 𝑖 𝑗 +𝑤 3  …

- **p.6** (BM25 -2.867):
  > ted by sector). distinguish that from the structural property each component guarantees in general. A1: w/o Bilinear Projection.Freezing the attention parameters 𝑊𝑞,𝑊𝑘,𝑊 𝑣, 𝑤 at random initialisation yields comparable detection precision as the trained full model across all five thresholds (0.151 vs. 0.151 at the 90th percentile, with ≤ 0.3percentage- point movement at any threshold; Table 2). On a 638-article corpus the bilinear weights do not learn a precision-improving signal beyond what the static adjacency already provides. We therefore donotclaim a precision benefit on this dataset. What the bilinear architecture does provide (measurable on the full model) is structural directionality: …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
