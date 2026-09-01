# Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement

Auto-generated bundle from `arxiv:2608.21888`.

Template: **mean_reversion**

Matched keywords: `mean reversion, reversal`

Paper URL: http://arxiv.org/abs/2608.21888v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.21888",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.21888")`.

### Auto-retrieved passages

- **p.1** (BM25 -25.831):
  > Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement Nadav A. Kitron Independent researcher nadav.k@eshqol.com Jonathan M. Wengrowicz Independent researcher yonatan.wengrowicz@gmail.com August 2026 Abstract At 15-minute horizons, directional mean reversion is far stronger and more pervasive in cryptocurrency markets than in US equities: scored under one matched, strictly out-of-sample protocol, 90% of 183 Binance pairs carry significant directional reversal against 2.7% of 187 US stocks and ETFs, in every focal coin-year since 2021. The signal lives in signs, not magnitudes: lag-one return autocorrelation is near zero on the major coins, yet simply betti …

- **p.1** (BM25 -20.707):
  > (95% CI[+0.008,+0.014]) under the most conservative accounting, clear of zero either way. Keywords:market efficiency; mean reversion; price discovery; exchange-traded funds; order flow; limits to arbitrage JEL classification:G14; G12; C58 1 Introduction Market efficiency is a matter of degree [21, 26, 41]: different markets absorb information at different speeds, and the residual predictability left behind is a measurable signature of their microstructure. This paper measures that residual at the shortest horizons, at population scale, across today’s two most different market structures. Scored under one matched, strictly out-of-sample walk-forward, 183 cryptocurrency pairs carry a pervasive …

- **p.1** (BM25 -19.602):
  > underlying’s reversal, including its absence, from their first months of trading; stocks merely correlated with the same underlyings inherit nothing: descriptive evidence that a wrapper’s tape reads like the process it wraps, not the venue it prints on. On the originating tape, the reversal concentrates after moves driven by aggressive taker flow and grows with flow intensity, while the order-book depth a move consumes conditions nothing: a conditioning consistent with compensated liquidity provision, not a test that selects it. The gross edge peaks near 1.3bp per trade against a 5bp round-trip cost: large enough to detect, too small to clear benchmark spot capture costs. The contrast surviv …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
