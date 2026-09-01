# Lead-Lag Relationships in Financial Markets: A Comparison of Multiple Clustering Algorithms

Auto-generated bundle from `arxiv:2608.24703`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.24703v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.24703",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.24703")`.

### Auto-retrieved passages

- **p.5** (BM25 -4.861):
  > 9%, showing excellent risk-adjusted returns. In comparison, DTW-KMedoids and KShape algorithms, although stable, are slightly inferior in the combined performance of returns and drawdowns. In terms of robustness, the ensemble algorithm stands out, mainly because it performs consistently across both datasets without ex- tremely poor outcomes. It even achieves the best performance under the lag strategy in the dataset containing 679 assets. The cumulative return plots of the lead strategy under different algorithms are shown in Figure 4, while the cumulative returns of the lag strategy are shown in Figure 5. The plots clearly demonstrate the outstanding performance of the MiniRocket-KMeans alg …

- **p.4** (BM25 -4.782):
  > days to generate trading signals. 4.3 Backtesting Metrics The backtesting metrics quantify strategy performance across four dimensions: profitability (annualized return 𝑅annual), risk (annual- ized volatility 𝜎annual, maximum drawdown 𝑀𝐷𝐷 ), risk-adjusted Algorithm 1Trading Strategy Input:Time series matrix𝑋 𝑛×𝑇 . 1: Extract sub-time series using a sliding window of fixed length 𝑙=21, obtaining𝑋 𝑛×𝑙 for each window. 2: Cluster the sub-time series within each window using the four proposed clustering algorithms. 3: For asset pairs within each cluster, apply the DTW-based lead- lag detection algorithm to divide them into Leader L and Lag- gerG. 4: Compute the trading signal as the sign of the  …

- **p.7** (BM25 -4.392):
  > hms for the lag strategy. −0.03 −0.02 −0.01 0 0.01 0.020 20 40 60 80 100 120 140 DTW_KMed_Mod DTW_KMed_Med KShape_Mod KShape_Med MiniRocket_KMeans_Mod MiniRocket_KMeans_Med Ensemble_Mod Ensemble_Med lead DTW_KMed_Mod DTW_KMed_Med KShape_Mod KShape_Med MiniRocket_KMeans_Mod MiniRocket_KMeans_Med Ensemble_Mod Ensemble_Med 1.05 1.055 1.06 1.065 1.07 1.075 1.08 1.085 P/L Ratio (a) Lead strategy on 679 assets. −0.03 −0.02 −0.01 0 0.01 0.02 0.03 0.040 20 40 60 80 100 120 DTW_KMed_Mod DTW_KMed_Med KShape_Mod KShape_Med MiniRocket_KMeans_Mod MiniRocket_KMeans_Med Ensemble_Mod Ensemble_Med lead DTW_KMed_Mod DTW_KMed_Med KShape_Mod KShape_Med MiniRocket_KMeans_Mod MiniRocket_KMeans_Med Ensemble_Mod En …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
