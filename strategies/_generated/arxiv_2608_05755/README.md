# Cross-Sectional Heterogeneity in LSTM Networks for Financial Time Series

Auto-generated bundle from `arxiv:2608.05755`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2608.05755v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.05755",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.05755")`.

### Auto-retrieved passages

- **p.24** (BM25 -14.483):
  > Figure 15: Impact of the learned sector embeddings on stock selection into the long short portfolio in 2003. Figure 16: Average cumulative returns of the top and flop 10 stocks picked for the Long-Short Portfolio. reversal signature documented by Jegadeesh (1990) and Lehmann (1990), recovered here endogenously from the LSTM’s temporal component. To summarize the findings in chapter 4.3, the sector LSTM coincides with the finding by Jegadeesh and Titman (2011) that the momentum of individual stocks is defined by short horizon return reversals while the industry momentum benefits from auto-correlation in portfolio returns. The strength of the industry momentum signal is not uniform over the fu …

- **p.3** (BM25 -13.661):
  > ded in- ternationally by Asness et al., 2018. Moskowitz and Grinblatt, 1999 provide the foundational result for the present paper: a substantial share of individual stock momentum profits is attributable to industry momentum, with high-momentum industries outperforming low-momentum industries by economically meaningful amounts over the subsequent six months. Grundy and Martin (2001) further decompose the momentum return and show that industry-level autocorrelation is a primary source of the strat- egy’s profitability, in contrast to the short-horizon return reversal that characterizes individual-stock momentum (Lewellen, 2002). The robustness of industry momentum is, however, conditional on  …

- **p.23** (BM25 -13.051):
  > 5 quantifies the resulting portfolio distortion. Utility stocks constitute 63.8 percentage points more of the long portfolio than the short portfolio, and Healthcare a further +7.3 pp, while Technology stocks are concentrated in the short portfolio with a bias of−68.0 pp. This configuration is precisely the one most exposed to a momentum crash: the short leg appreciates substantially while the long leg only has small returns, generating negative overall returns. This mechanism aligns with the findings of Daniel and Moskowitz (2016), who identify the outperformance of prior losers, held in the short portfolio, as the primary driver of momentum crash losses. 4.3.5 Short-T erm Reversal from the …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
