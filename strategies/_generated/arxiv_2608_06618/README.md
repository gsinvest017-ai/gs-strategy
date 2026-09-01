# Beyond Co-Movement: Locality by Exposures Enables a Joint Factor-Graph Framework for Portfolio Diversification

Auto-generated bundle from `arxiv:2608.06618`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.06618v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.06618",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.06618")`.

### Auto-retrieved passages

- **p.5** (BM25 -4.124):
  > the Global Industry Classifica- tion Standard (GICS) sectors [24] while remaining agnostic to the partitioning during training. This is illustrated in Figure 4. Covariance denoising.Imposing a low-rank prior on the represen- tation induced covariance, ˆ𝚺𝑅, reduces the number of parameters required for estimation, and thus reduces the estimation error in finite-data settings. This lower sensitivity to artefacts improves

- **p.3** (BM25 -3.476):
  > To this end, in the present paper, we propose MINGLE, a unified ADMM framework that en- forcesmutual consistencyacross the factor and graph domains so that each corrects for the inductive bias of the other. 3 Methodology Assets with similar exposures to latent risk drivers are expected to respond similarly to systematic market perturbations and therefore offer limited diversification benefit to one another. For the purpose of diversification, we define graph locality in the factor-exposure domain, with asset neighbourhoods reflecting similarity in expo- sure profiles, rather than in-sample co-movements. This definition of locality implies amutual consistencyof the graph and factor domains, w …

- **p.8** (BM25 -3.313):
  > Chehabet al. Regime-conditional performance.Figure 7 shows the decom- position of portfolio performance by VIX-classified market regime. Contagion Cut and Adaptive CutV on ˆ𝚺𝑅 outperformed the base- lines inCalmandElevatedmarkets. InCrisis, representation-based approaches registered the least negative Sharpe ratio. This negative Sharpe reflects the long-only constraint, which cannot profit from a market-wide decline. Remark 3.The learnt representation models historical returns as arising from 𝑘 factors. InCrisis, returns load onto fewer risk drivers [18], yet the model is constrained to populate all 𝑘 dimen- sions. This can introduce artefacts into the learnt representation, rendering the fa …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
