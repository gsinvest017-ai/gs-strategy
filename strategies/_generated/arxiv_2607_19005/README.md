# Observable Matrix Dynamics of Stocks

Auto-generated bundle from `arxiv:2607.19005`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.19005v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.19005",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.19005")`.

### Auto-retrieved passages

- **p.31** (BM25 -2.772):
  > rm-specific factors, together with the higher-order memory of the transitions, can be built in as exogenous drivers of the transition matrix. A state- dependent chain of this kind would add realism. Coupled to the persistence and leadership structure documented here, it points toward dynamic portfolio management, where a rank- based or transfer-entropy-informed strategy that buys the followers when the defensives lead connects these observables to stochastic portfolio theory [19, 20]. More broadly, the matrix-based formalism itself applies to portfolio construction and op- timization. The effective dimension and correlation geometry of the distance matrix inform covariance estimation and ris …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
