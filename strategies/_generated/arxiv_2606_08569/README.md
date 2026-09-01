# Stock Investment: The p-index Approach

Auto-generated bundle from `arxiv:2606.08569`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2606.08569v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.08569",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.08569")`.

### Auto-retrieved passages

- **p.17** (BM25 -15.315):
  > 17 Figure 9 Comparisons of p-ratio-efficient-contrarian, p-index-inefficient-momentum and p-index-efficient-contrarian strategies Market trading volume can serve as a proxy for investor sentiment, where elevated levels signal heightened market activity and strong sentiment. As demonstrated in Figure 10's synthesis of weekly trading volume data with Figures 6-7, a distinct pattern emerges: The p-index-efficient-contrarian strategy consistently outperformed its p-index-inefficient-momentum counterpart during the 2018-Q2 2020 period (weekly volume: RMB13.3429B), but underperformed thereafter (post-Q2 2020 weekly volume: RMB18.9739B), reflecting a 42% surge in market participation. This inverse  …

- **p.15** (BM25 -14.496):
  > ile the momentum strategy incurred substantial losses (−9.69% annualized rate of return). From Figures 2-7, we conclude that among the fifty stocks in the SSE 50 index, efficient (outperforming) stocks failed to sustain their momentum, while inefficient (underperforming) stocks exhibited no mean reversion. Both inefficient-momentum and efficient-contrarian investment strategies yielded significant returns. Among all momentum and contrarian strategies, p-ratio-efficient-contrarian strategy generated the highest annualized rate of return, at 9.97%.

- **p.19** (BM25 -14.313):
  > 19 Figure 11 S&P 500 p-ratio-efficient-momentum Figure 12 S&P 500 p-ratio-inefficient-contrarian Figure 13 S&P 500 p-index-efficient-momentum Figure 14 S&P 500 p-index-inefficient-contrarian Figure 15 S&P 500 beta-efficient-momentum Figure 16 S&P 500 beta-inefficient-contrarian

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
