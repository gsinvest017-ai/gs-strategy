# Generalizing Markowitz Portfolio Optimization by a Quadratic Risk Measure

Auto-generated bundle from `arxiv:2608.24449`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.24449v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.24449",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.24449")`.

### Auto-retrieved passages

- **p.34** (BM25 -3.433):
  > he theory of portfolio choice.The Journal of Finance, 38(3):745–752, 1983. [23] Hui Peng, Genshiro Kitagawa, Min Gan, and Xiaohong Chen. A new optimal port- folio selection strategy based on a quadratic form mean–variance model with trans- action costs.Optimal Control Applications and Methods, 32(2):127–138, 2011. [24] Stephen A. Ross. Mutual fund separation in financial theory–the separating distri- butions.Journal of Economic Theory, 17(2):254–286, 1978. 34

- **p.5** (BM25 -3.074):
  > del and the Fama–French three-factor model [9]. Under appropriate factor model assumptions,Qadmits the decomposition Q=βΣ F βT +D, whereβis the factor loading matrix, Σ F is the covariance matrix of the common risk factors, andDis a diagonal matrix of idiosyncratic variances. Such representations substantially reduce the number of parameters that must be estimated while preserving positive definiteness; see, for example, [10], [16, Chap. 6]. Let us turn to the linear adjustment vector ccc. The linear term has a clear geometric interpretation. SinceQis positive definite, the risk measureR P (1) can be written in the completed-square form (3). Consequently, the vectorc ccshifts the center of t …

- **p.2** (BM25 -2.981):
  > d risk measureR P gives considerably more flexibility than variance while remaining available in explicit closed form, and reveals geometric phenomena that disappear in the classical mean-variance model: the tangency portfolio is not the same as the maximum Sharpe ratio portfolio; see the comment beneath Proposition 6. To the best of our knowledge, ex- plicit closed-form expressions of this generality are not available in the existing literature for quadratic risk measures beyond variance. Let us denote the set of portfolios P= ( www:= (w 1, w 2, . . . , w n)∈R n : nX i=1 wi = 1 ) , n∈N. Thus, a portfolio is defined as a vectorw ww∈ P, where each component (weight)w i denotes the fraction of …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
