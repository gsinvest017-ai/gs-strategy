# Game-Theoretic Modeling of Heterogeneous Investor Interactions for Stock Price Forecasting

Auto-generated bundle from `arxiv:2605.23953`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.23953v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.23953",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.23953")`.

### Auto-retrieved passages

- **p.6** (BM25 -3.981):
  > ndividual stocks. The event of a stock being listed on the Dragon and Tiger List reflects short-term capital enthusiasm and speculation on that stock, which exerts either a positive or negative impact on its price over a subsequent period. However, this impact gradually diminishes over time until it eventually decays to zero. Motivated by this, we incorporate a game-theoretic mechanism to model the capital gaming among different investors around individual stocks, where investors act as players whose feasible strategies comprise buying, selling, holding, or remaining in a short position. In the subsequent experiments, these strategies are encoded as -1, 1, and 0, representing selling, buying …

- **p.4** (BM25 -2.849):
  > 2 ,· · ·,s N }, each si ⊆S has historical trading data on trading day t represented as the vector X t Si . Additionally, Given a graph G= (V,E,A,R) , where V denotes the set of entity vertices of all distinct types in the graph, and E represents the interactive relationships among different entities. We set a looking back windows L, our task in to use the relation graph G and the historical data of S during day T−(L−1) to T , donated as X T−(L−1):T S ={X T−k si |i= 1,2, . . . , N;k=L−1, L−2, . . . ,0} , to predict the relative price change of all stocks in the stock poolSon the next trading dayT+ 1, donated asy T+1 S . Mathematically, this can be formalized as ˆ yT+1 S =f(X T−(L−1):T S ,G; Θ …

- **p.4** (BM25 -2.779):
  > gure 1: Overview of our GameStock architecture. as G= (V,E,A,R) , where each node v∈ V is associated with a node type ϕ(v)∈ A , and each heterogeneous edgee∈ Ecorresponds to a relation typeψ(e)∈ R. Game TheoryIn our framework, all investors in the stock market are categorized into three types, namely institutions, hot money, and retail investors. The strategic and capital games surrounding the target stock are conducted among these three types of investors, which are regarded as players. The set of strategic actions available to them is denoted asAction={Buy,Sell,HoldorBear position}, 3.2 Problem formulation Following the setup of existing works [Xia et al., 2024; Fan and Shen, 2024; Huynh e …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
