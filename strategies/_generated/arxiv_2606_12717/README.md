# Mixture-Preserving, Arbitrage-Free Interpolation for Volatility-Surface Models

Auto-generated bundle from `arxiv:2606.12717`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.12717v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.12717",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.12717")`.

### Auto-retrieved passages

- **p.2** (BM25 -5.852):
  > ostk such kernels, so eachp tk ∈ M N. The subscriptt k is adiscretelabel: thesen+1 snapshots are all we observe. The task is to fill in the density at every intermediate time, that is, to build acontinuous- timefamily (p t)t∈[t0,tn] that matches the data at the pillars,p t t=tk =p tk, by interpolating the mixture parameters (w i(t), µi(t), σi(t)) between consecutive pillars. Section 5 constructs such a family, continuous intand inside the mixture family. Definition 1(Peacock).The time-indexed collection(p t)t∈[t0,tn], all members sharing the meanF, is apeacockif it spreads out over time: for any two datess≤tand every convex functionφ, E  φ(Xs)  ≤E  φ(Xt)  ,E  φ(Xt)  = Z φ(x)p t(x)dx. E …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
