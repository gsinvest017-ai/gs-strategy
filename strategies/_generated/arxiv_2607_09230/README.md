# When Does Order Flow Matter? State-Dependent L2 Liquidity-State Transitions in Crypto Futures

Auto-generated bundle from `arxiv:2607.09230`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.09230v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.09230",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.09230")`.

### Auto-retrieved passages

- **p.3** (BM25 -4.34):
  > work [10] models jumps and price discovery in the Treasury market, not a liquidity-state transition. Our task is the specific combination none of them occupies: a supervised, out-of-sample post-event L2 macro-event window pre-event L2 state spread / depth-20 / imb-20 post-event liquidity regime calm / mixed / stressed Figure 1: We predict the post-event L2 liquidity-state transi- tion, not price direction; both states are built from spread, depth, and imbalance with train-fold-only tercile thresholds. liquidity-state transition, conditioned on a scheduled macro calen- dar. Taken together, the three lines leave an unoccupied position whose least-occupied point is a within-asset, regime-condit …

- **p.3** (BM25 -3.205):
  > e twenty levels per side into a fixed-width representation and derive, at each minute, three descriptors of the book: the relative bid-ask spread, the total depth across the top twenty levels, and the order- book imbalance across those levels. These three descriptors are the basis for the liquidity-state definition in Section 3.2. The macro calendar is a standard commercial economic-event feed covering the major economic regions, and we use only the scheduled release timestamps. The modeling universe entering the scored results is 47,513 windows per horizon, 18,631 of them event windows (BTC 9,330, ETH 9,301) against 28,882 matched non-event windows, from 9,773 unique scheduled events across …

- **p.4** (BM25 -3.155):
  > n-order fill probability, sub-second market-order impact, or a replay-grade execution simulator; those require order-by-order data that is a different research program (Section 2), and we make no such claim. 3.2 The liquidity-state definition We summarize the book at each minute by a single discrete liquidity state with three levels, which we label calm, mixed, and stressed. The state is built from the three book descriptors of Section 3 (rela- tive spread, top-twenty depth, and top-twenty imbalance) aggre- gated over the pre-event window. Each descriptor is first oriented so that a higher value is a less liquid book: spread and absolute imbalance are taken as is, while depth is negated, sin …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
