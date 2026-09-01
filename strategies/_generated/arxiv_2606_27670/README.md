# CryptoGAT: Are Time Series Models Effective for Cryptocurrency Forecasting?

Auto-generated bundle from `arxiv:2606.27670`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.27670v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.27670",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.27670")`.

### Auto-retrieved passages

- **p.8** (BM25 -4.761):
  > m the graph model’s learning of heterogeneous pairwise relationships. VI. CONCLUSION ANDFUTUREWORK Conclusion.To our knowledge, due to bias in problem definition, pure cryptocurrency price prediction models have rarely appeared in high-quality conferences. This bias in problem definition has driven the field research toward incor- porating external and multimodal signals (such as on-chain data and sentiment features) to compensate for the limited predictive power. Our work takes the opposite approach: rather than augmenting data sources, werecast pure price-based cryptocurrency prediction from a time-series problem into a graph problem. Through the extensive and comprehensive experimental an …

- **p.1** (BM25 -3.49):
  > ude: •24/7 Operation:Operates continuously globally, without a unified trading session or market closure schedule set by a central authority. •Lack of Intrinsic Valuation:Without the support of tangible assets and fundamental disclosures. •Extreme Volatility:Driven by both market narratives and liquidity impulses, highly sensitive to sentiment feedback. •Irregular Liquidity:Many tokens suffer from inconsis- tent liquidity, exacerbating price impact and risk expo- sure. An important observation is that the fundamental reason hindering cryptocurrency prediction research lies in thebias in problem definition. Due to the significant time dependence of financial assets, they have long been treate …

- **p.3** (BM25 -3.46):
  > poral encoding with relational embeddings through a graph convolution mechanism. To better capture the dependencies between assets, ESTIMATE [38] combines hypergraphs with temporal generative filters to enable the modeling of non- pairwise market correlations. The latest state-of-the-art model, StockMixer [39], has been designed with three mixing mod- ules to effectively model technical metrics, time dependencies, and space dependencies. Although StockMixer performs well on stock prediction tasks, its effectiveness does not transfer to cryptocurrency forecasting. III. METHODOLOGY A. Problem Definition Following the setup of existing works [38], [40], we adapt the stock price forecasting fram …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
