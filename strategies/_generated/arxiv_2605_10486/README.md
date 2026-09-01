# Manipulation, Insider Information, and Regulation in Leveraged Event-Linked Markets

Auto-generated bundle from `arxiv:2605.10486`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.10486v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.10486",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.10486")`.

### Auto-retrieved passages

- **p.26** (BM25 -12.811):
  > uire the manipulator to influence either the oracle outcome (no outcome manipulation, in the sense of Section 3.2) or the venue index (no market-price manipulation in the trade-based sense). The channel runs entirely through the venue’s risk-allocation structure. Three observations on the bad-debt-shifting channel: Position-taking is not manipulation in the traditional sense.The manipulator is not engaging in spoofing, wash trading, or marking-the-close behavior. They are taking a directional position consistent with their beliefs and sizing it against the venue’s structural risk-allocation policy. The behavior is observationally indistinguishable from a high-conviction directional trader’s  …

- **p.15** (BM25 -7.868):
  > collapse this distinction: the underlying real-world event can be subject to manipulation by parties whose costs are within the leveraged-profit range of position-takers. Whether the introduction of event-linked perpetuals materially changes the incentive landscape is the question. 5.1 Cost-benefit framework Definition 3(Outcome-manipulation cost-benefit).Let E be a binary event with two possible outcomes (YES, NO). LetπYES,πNO be the prevailing market-implied probabilities at the time the manipulator establishes their position (withπYES +πNO = 1in the binary case). Let the manipulator’s position be long YES with notional exposureN and leverageL, where the trader’s capital at risk isC=N/L. T …

- **p.21** (BM25 -7.853):
  > unleveraged, the leveraged equivalent earnsL·r, before accounting for any leverage-specific costs (financing, margin maintenance). Risk-adjusted rent and Sharpe ratio.Leverage increases the volatility of the position by factorL as well, so the Sharpe ratio of the leveraged strategy approximately equals the unleveraged Sharpe (with adjustments for funding and financing costs). The leverage does not improve the strategy’s information content; it amplifies both the return and the variance. The implication is that informed traders who have positive expected returns unleveraged can earn larger absolute profits through leverage at the same Sharpe ratio. This is attractive only if their capital is  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
