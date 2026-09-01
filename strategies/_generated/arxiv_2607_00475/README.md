# End-to-End Parametric Portfolio Policies for Cross-Asset Futures Timing: When Do AI Models Beat Simple Rules?

Auto-generated bundle from `arxiv:2607.00475`.

Template: **momentum**

Matched keywords: `momentum, time-series momentum`

Paper URL: http://arxiv.org/abs/2607.00475v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.00475",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.00475")`.

### Auto-retrieved passages

- **p.4** (BM25 -21.959):
  > We compare the LSTM and transformer policies against three standard rules: equal weight (1/N), risk parity, and time-series momentum (TSMOM). All five strategies rebalance daily. Risk parity uses a 60-day inverse-volatility estimate, while TSMOM uses the standard 12-month signal [2]. Equal weight and risk parity are long-only. The learned policies and TSMOM are long/short with unit gross exposure. Within each universe, all strategies are evaluated over the same out-of-sample window. Because Sharpe ratios are scale-invariant, leverage does not affect the comparison. A. Performance Across Asset Classes Table II reports the out-of-sample performance of every strategy in each universe. We focus  …

- **p.1** (BM25 -19.776):
  > ithin the transformer literature, the closest papers are [4], who study attention-based futures momentum, and [9], who develop a Portfolio Transformer for Sharpe- optimized asset allocation. Our contribution is a practitioner-oriented evaluation of this end-to-end framework in a highly liquid, cross-asset investable universe. We study the sixteen most liquid CME futures across six asset classes, benchmark the learned policies against equal weighting, risk parity, and time-series momentum, and eval- uate performance under walk-forward training with realistic transaction costs. The goal is not architectural novelty, but to evaluate when an end-to-end policy improves on the simple arXiv:2607.00 …

- **p.8** (BM25 -16.283):
  > . We also study one daily frequency and two architectures, not a broader model class. The natural extensions follow directly from these limita- tions. Higher-frequency data may give the policy more signal to learn from. A larger futures universe, with more contracts per asset class and more asset classes, would give the model more breadth to exploit. Contract and asset-class embeddings could then allow one model to share information across related instruments while still learning contract-specific behavior. REFERENCES [1] Z. Zhang, S. Zohren, and S. Roberts, “Deep reinforce- ment learning for trading,” J. Financ. Data Sci., vol. 2, no. 2, pp. 25–40, Spring 2020. [2] B. Lim, S. Zohren, and S. …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
