# Large Language Model-Driven Small-Capitalization Trading: Integrating Financial News Sentiment, Macroeconomic Indicators, and Technical Signals

Auto-generated bundle from `arxiv:2608.12283`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.12283v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.12283",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.12283")`.

### Auto-retrieved passages

- **p.2** (BM25 -8.238):
  > ictive signal should become portfolio weights. Equal weight- ing, risk parity (Maillard et al., 2010), and hier- archical risk parity (López de Prado, 2016) either ignore the expected-return signal or allocate pri- marily from covariance, while mean-variance op- timization (Markowitz, 1952) treats predicted re- turn and risk as fixed point estimates. Sentiment- based portfolio papers usually inject language infor- mation into expected returns or Black–Litterman views: Colasanto et al. (2022) use a BERT senti- ment score to form Black–Litterman views, Lee et al. (2025) translate LLM forecasts and predictive uncertainty into views and confidence levels, and Chen (2025) and Taheripour et al. (2 …

- **p.17** (BM25 -5.564):
  > return is R′ = R(1−x)−2x 1 +x (22) The daily equity curve is reported net of these segment-level cost charges. Portfolio metrics are computed from the resulting daily net value path; cumulative gross return is retained separately by rerunning the same strategy with transaction costs and slippage set to zero. G Baseline Portfolio Formulations Mean–variance optimization.The primary risk- aware allocator solves a constrained mean–variance problem using the model’s predicted arithmetic- return mean µt and covariance Σt, with risk aver- sion δ= 2.5 shared across all allocators that use it, wM V O t = arg max w  µ⊤ t w− δ 2 w⊤Σtw(23) −κ turn∥w−w t−∥1  , subject to full investment, non-negativity …

- **p.9** (BM25 -5.19):
  > Marcos López de Prado. 2016. Building diversified portfolios that outperform out-of-sample.Journal of Portfolio Management, 42(4):59–69. Alejandro Lopez-Lira and Yuehua Tang. 2026. Can chatgpt forecast stock price movements? return pre- dictability and large language models.Journal of Financial Economics, forthcoming. Sébastien Maillard, Thierry Roncalli, and Jérôme Teiletche. 2010. The properties of equally weighted risk contribution portfolios.The Journal of Portfolio Management, 36(4):60–70. Harry Markowitz. 1952. Portfolio selection.The Jour- nal of Finance, 7(1):77–91. Advije Rizvani, Giovanni Apruzzese, and Pavel Laskov. 2026. Adversarial news and lost profits: Manipu- lating headlines …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
