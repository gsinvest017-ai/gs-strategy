# Recovering Structural Organization in Noisy Correlation Networks Using Financial Systems as a Testbed

Auto-generated bundle from `arxiv:2607.10297`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.10297v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.10297",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.10297")`.

### Auto-retrieved passages

- **p.18** (BM25 -4.803):
  > tasets, the proposed strategy demon- strates strong and statistically significant outperformance in equally weighted portfolios, indicating robustness under diverse market conditions. Under Markowitz-weighted port- folios, the strategy largely retains its dominance over benchmark constructions such as πF U LL c ,π ST R c , andπ HSR, although mild inconsistencies appear for smaller portfolio sizes and in comparisons with stronger benchmarks such as the market portfolio. For the S&P 500 dataset, the proposed strategy continues to exhibit strong and statistically significant 18

- **p.9** (BM25 -4.28):
  > The annualized Sharpe ratio for strategykin iterationmis computed as S(k) m = µ(k) m σ(k) m √ 252, whereµ (k) m andσ (k) m denote the sample mean and standard deviation ofR (k) m , respectively. The risk-free rate is assumed to be zero. To evaluate whether the superior performance of the proposed strategy is statistically significant, we compare its Sharpe ratio with that of each benchmark across all Monte Carlo replications. Let ∆(j) m =S (πST R p ) m −S (j) m , m= 1, . . . , M,(13) denote the Sharpe ratio difference between the proposed strategy and benchmarkjin replicationm. Since the distribution of Sharpe ratio differences may deviate from normality, we employ the nonparametric Wilcoxon …

- **p.8** (BM25 -3.885):
  > and statistical significance of the proposed strategy, we employ a Monte Carlo–based subsampling framework. LetB (k) ∈R T×W denote the matrix of out- of-sample portfolio returns corresponding to strategyk, whereT= 250 is the investment horizon andWis the number of rolling windows. The strategies under consideration are πF U LL p ,π ST R p ,π F U LL c ,π ST R c ,π HSR ,π RN D,π M KT , whereπ ST R p represents the proposed strategy. At each iterationm= 1, . . . , M(withM= 1000), we randomly select a subset of n= 500 rolling windows without replacement: Im ⊂ {1, . . . , W},|I m|= 500. For each strategyk, the corresponding returns are pooled across the selected windows to form R(k) m = n B(k) t, …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
