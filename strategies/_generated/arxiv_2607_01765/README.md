# A Cap-Axis Integral Diagnostic of Factor Models

Auto-generated bundle from `arxiv:2607.01765`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.01765v3

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.01765",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.01765")`.

### Auto-retrieved passages

- **p.14** (BM25 -4.843):
  > total returns. To update holdings, I separate the ex-dividend return RET Xi,t from the dividend- inclusive return RET ADJi,t. The ex-dividend position value is H x i,t+1 = Hi,t(1 + RET Xi,t), and portfolio-level dividend cash is DivCash t = X i Hi,t (RET ADJi,t −RET X i,t).(36) This cash is reinvested in proportion to positive ex-dividend position values: Hi,t+1 =H x i,t+1 +DivCash t H x i,t+1P j H x j,t+1 .(37) The calculation is rescaled when necessary to preserve the portfolio’s total post-return 14

- **p.4** (BM25 -3.589):
  > y moving through the market portfolio in capitalization order. 3.1 The implemented finite-market bridge Let τ(t) denote the most recent formation date before return date t. At τ(t), eligible stocks are sorted in descending order of formation-date market capitalization, and the ordering is held fixed until the next formation date. Index the stocks in this order byi= 1, . . . , N t. Let Hi,t|τ(t) be the beginning-of-period value of stock i’s position under the formation-and- holding rule. Define its normalized market weight by wi,t = Hi,t|τ(t) PNt j=1 Hj,t|τ(t) , NtX i=1 wi,t = 1.(1) 4

- **p.37** (BM25 -3.26):
  > ion is narrower than pricing every raw size portfolio. Because the empirical bridge uses whole stocks, its realized exposure st(p) varies as portfolio weights evolve, so zero alpha on the bridge and market does not mechanically imply zero alpha on the unscaled prefix return. The diagnostic instead asks whether each capitalization prefix differs systematically from an equal-exposure position in the whole market. The functionals distinguish different features of the curve: SA measures directional tilt; IAE measures magnitude without sign cancellation; ISE emphasizes concentrated distortions; and SU P records the largest local error. The coherence ratio separates predominantly one- signed curve …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
