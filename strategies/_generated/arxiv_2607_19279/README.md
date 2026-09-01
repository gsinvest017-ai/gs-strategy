# Gaussian Boson Sampling for Asset Clustering in Statistical Arbitrage Portfolios

Auto-generated bundle from `arxiv:2607.19279`.

Template: **mean_reversion**

Matched keywords: `statistical arbitrage, statarb`

Paper URL: http://arxiv.org/abs/2607.19279v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.19279",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.19279")`.

### Auto-retrieved passages

- **p.2** (BM25 -21.048):
  > ts), characterised by a correlation matrix. To obtain a (weighted) adjacency matrix struc- ture, we zero the main diagonal of a correlation matrix. B. Statistical Arbitrage & Trading Portfolio Construction Quantitative trading strategies utilise mathematical models to identify and exploit predictable price move- ments in financial assets. A prominent example is Statis- tical Arbitrage (StatArb), which relies fundamentally on mean reversion. This strategy assumes that price devi- ations, whether from an asset’s historical average or rel- ative to highly correlated assets, are temporary anoma- lies that will tend to revert to their mean. These devi- ations can persist for days or resolve in su …

- **p.2** (BM25 -17.882):
  > erently misses some mar- ket correlations. However, when coherent displacement is introduced in the presence of loss to stabilise mean photon numbers, we find that performance recovers. Moreover, this economic advantage is prevalent when the sample period contains a volatile market. In the presence of experimental imper- fections, an empirical exponential quantum advantage is not expected. Nevertheless, industries like finance still find empirical polynomial quantum advantages valuable, even in the presence of such imperfections. II. STRATEGY OVERVIEW We provide an overview of the main components of our GBS application into statistical arbitrage (StatArb). A workflow diagram can be seen in F …

- **p.9** (BM25 -16.037):
  > lify StatArb returns. An alternative cluster evaluation metric could leverage the Ornstein-Uhlenbeck process to quantify the strength of alpha signals [29, 41, 43, 56]. By modelling spread dy- namics as a stochastic differential equation, a linear au- toregressive model can estimate the mean-reversion speed θfor each cluster, thereby prioritising subgraphs with faster trading opportunities. Notably, assuming uniform latent factors and idiosyncratic noise within a cluster, the optimal WD to maximise expected returns is 2/3. Although this setting is idealised, this analytically un- derscores that maximising intra-cluster correlation does not monotonically increase economic returns. Regarding Q …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
