# Herding and Liquidity in Order-Book Markets. II. Fundamental Anchoring and the Resilience of Liquidity

Auto-generated bundle from `arxiv:2607.16970`.

Template: **mean_reversion**

Matched keywords: `mean-reversion`

Paper URL: http://arxiv.org/abs/2607.16970v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.16970",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.16970")`.

### Auto-retrieved passages

- **p.4** (BM25 -15.668):
  > h bids and asks reappear atft and draw the price back, sopt mean-reverts tof t. The replenishing depth is posted at a fixed distance fromft regardless of how farp t has strayed; we characterise the resulting mean reversion by its effect on the order parameter below rather than by a displacement-dependent rate, and refer to it simply as a restoring force. Momentum herders.A fraction of the flow comes from chartist agents whose order sign follows the recent price momentum. Two parameters govern them: an intensityϕ∈[0,1], the propensity to act on the momentum signal, and a couplingκthat correlates the herders with one another. When ϕandκare large the herders act in concert: a run of upticks pro …

- **p.14** (BM25 -14.778):
  > 7 Conclusion We have identified, quantified, and causally confirmed an intrinsic stabilising mechanism in an order-book market: fundamental-value anchoring of liquidity provision acts as a restoring force that reverts a shocked price to the fundamental and refills the book with two-sided depth after a shock. Dialling the anchor down removes the restoring force, the receiver loses its mean-reversion, and a leverage-driven fire-sale self-sustains–the direct causal confirmation that the anchor is the stabiliser. Separately, we coupled two anchored markets and attempted to transmit a herding-driven liquidity crisis from one into a calm neighbour through a hierarchy of progressively stronger chan …

- **p.1** (BM25 -13.485):
  > Herding and Liquidity in Order-Book Markets. II. Fundamental Anchoring and the Resilience of Liquidity Jan Novotny∗ Centre for Econometric Analysis, Bayes Business School 106 Bunhill Row, London EC1Y 8TZ, United Kingdom jan@novotny.one July 21, 2026 Abstract An order-book market whose liquidity provision is anchored to a fundamental value carries a restoring force: the price mean-reverts to value and the book refills after a shock. We show this restoring force is a robust intrinsic stabiliser and identify it causally–dialling the anchor down removes the mean-reversion, and a leverage-driven fire-sale then self-sustains. Separately, we ask whether a stressed market transmits its liquidity str …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
