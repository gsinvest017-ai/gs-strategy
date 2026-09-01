# Hierarchical Graph Learning for Calendar Spread Strategies in Commodity Futures Markets

Auto-generated bundle from `arxiv:2606.25811`.

Template: **mean_reversion**

Matched keywords: `statistical arbitrage`

Paper URL: http://arxiv.org/abs/2606.25811v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.25811",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.25811")`.

### Auto-retrieved passages

- **p.12** (BM25 -10.632):
  > minimize the mean squared error between̂𝑌𝑡+2,𝑐𝑑 and𝑌 𝑡+2,𝑐𝑑 for(𝑐, 𝑑) ∈ ̂𝑈𝑡+2 ∩ ̃𝑈𝑡+2. 5. Experiments We conduct experiments to address the following questions. (Q1)Can CS strategies be more effective than LO strategies for statistical arbitrage in commodity futures markets in terms of risk and risk-adjusted return? (Q2)Are TTM-dependent interrelationships among futures contracts instrumental for statistical arbitrage? (Q3)Are both inter-commodity and intra-commodity relationships instrumental? Specifically,weverifyEqs.(14)to(16)inthedata,togetherwithtradingexamplesofLObaselines,for(Q1);compare our method against benchmarks in prediction and trading for(Q2); and conduct ablation studies for( …

- **p.1** (BM25 -10.427):
  > is effective for statistical arbitrage. Keywords:Calendar Spread Strategy, Graph Learning, Statistical Arbitrage, Commodity Futures, Deep Learning 1. Introduction We address the problem of exploiting statistical arbitrage opportunities in commodity futures markets through a calendar spread (CS) strategy based on hierarchical graph learning that captures information embedded in maturity- dependent interrelationships across commodity futures. A futures contract is an agreement between two parties in which the contract price is fixed at initiation, and at maturity, one party delivers the underlying asset (or settles in cash), while the other pays the predetermined price (Hull, Treepongkaruna, C …

- **p.18** (BM25 -10.105):
  > G., 2025. Deep learning statistical arbitrage. Management Science 0. Hamilton, W., Ying, Z., Leskovec, J., 2017. Inductive representation learning on large graphs, in: Advances in Neural Information Processing Systems, Curran Associates, Inc. Hammoudeh, S.,Sari, R., Ewing, B.T.,2009. Relationships amongstrategic commodities andwith financial variables: Anew look. Contemporary Economic Policy 27, 251–264. Hendrycks, D., Gimpel, K., 2023. Gaussian error linear units (GELUs). arXiv preprintarXiv:1606.08415. Hong, Y., Kim, Y., Kim, J., Choi, Y., 2023. Index tracking via learning to predict market sensitivities, in: Proceedings of SAI Intelligent Systems Conference, Springer. pp. 111–131. Hong, Y …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
