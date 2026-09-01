# Enhancing a Risk Model by Adding Transient Statistical Factors

Auto-generated bundle from `arxiv:2605.12977`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.12977v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.12977",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.12977")`.

### Auto-retrieved passages

- **p.32** (BM25 -4.388):
  > and Statistics, 87(3):503–522, 2005. [30] Kingsley Yeon and Mihai Anitescu. Beyond Low Rank: Fast Low-Rank + Diagonal Decom- position with a Spectral Approach.arXiv preprint arXiv:2512.17120, 2025. 32

- **p.2** (BM25 -4.272):
  > et. Under these assumptions the asset return covariance is given by the low-rank-plus-diagonal form cov(xt) =F tcov(st)F ⊤ t +cov(ϵ t),(2) wherecov(·) denotes the covariance. Because the elements ofϵ t are independent,cov(ϵ t) is a diag- onal matrix with positive diagonal entries. This structure is especially appealing in high dimensions (nin the order of hundreds or thousands), because we only need to estimateO(nn 1) parameters, instead ofO(n 2) in the case of a genericn×ncovariance matrix. The smaller number of parameters required in the low-rank-plus-diagonal structure (2) is also a form of regularization, which avoids overfitting and can improve the covariance estimate, especially for ou …

- **p.1** (BM25 -3.676):
  > hat the proposed extension captures structure in the returns that is missed by the original model. 1 Introduction The covariance of asset returns is a central quantity in several areas of finance, including Markowitz portfolio construction [2, 10, 17], risk management [18], asset pricing [27], and performance attri- bution analysis [20]. The variance of a portfolio (or investment strategy) is a linear function of the asset return covariance. An accurate (as judged by its statistical fit) asset return covariance allows investors to build portfolios with a desired level of risk and also evaluate the risk of existing portfolios. An inaccurate risk model can over-estimate or under-estimate portf …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
