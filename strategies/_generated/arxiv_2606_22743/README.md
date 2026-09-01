# Endogenous Randomness from Adversarial Market Learning

Auto-generated bundle from `arxiv:2606.22743`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.22743v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.22743",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.22743")`.

### Auto-retrieved passages

- **p.13** (BM25 -10.585):
  > could introduce explicit trend-following traders, mean-reversion traders, run-length traders, frequency-domain traders, and volatility-regime traders. Second, position sizing can be made variable. Instead of fixed notional positions, the trader can trade πt = 2pt −1, or use a risk-adjusted position based on predicted edge and volatility. Third, one can move from binary returns to continuous capped returns. This requires a nonzero activity constraint to prevent the trivial zero-return solution. Fourth, one can study strict out-of-sample experiments in which the market adapts only on in-sample information and the out-of-sample region is reserved solely for testing. Finally, one can develop the …

- **p.4** (BM25 -4.15):
  > The trader is a neural networkD m,h that outputs a logit. The predicted probability of a positive future cumulative return is p(m,h) t =σ  Dm,h(H (m) t )  , whereσis the logistic function. In the constant-notional version, the trader takes the position π(m,h) t = ( +1, p (m,h) t >1/2, −1, p (m,h) t ≤1/2. The corresponding realized profit is PnL(m,h) t =π (m,h) t St,h. In the variable-notional version, the position is scaled by confidence: π(m,h) t = 2p(m,h) t −1. The present paper focuses on the constant-notional version, because it gives a clear measure of directional exploitable structure. The variable-notional version is a natural robustness check. The default trader population uses m∈  …

- **p.2** (BM25 -4.07):
  > lity of predictive trading strategies. Third, the adversary is an economic trader rather than a statistical real/fake discriminator. A trader observes past returns, predicts a future cumulative return, takes a position, and earns profit or loss. The market objective is to make this trading edge vanish. Therefore, the model is better described as an adversarial self-generated market model. Its purpose is not data imitation but endogenous efficiency formation. 2

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
