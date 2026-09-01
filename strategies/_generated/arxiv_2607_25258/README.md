# Robust Hedging Valuation Adjustment for Deep Hedging Policies under Market Frictions

Auto-generated bundle from `arxiv:2607.25258`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.25258v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.25258",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.25258")`.

### Auto-retrieved passages

- **p.15** (BM25 -5.041):
  > rton bandb= 0.15 -0.01846 -0.000288 0.000008 -0.01874 -12.7% 16.7% Low Liquidity Merton bandb= 0.2 -0.03372 -0.000608 0.000030 -0.03430 -23.3% 45.0% D Initial-position sensitivity The main classical rule begins at q−1 = 0 and projects a zero starting position to the nearest point of the initial band. This sensitivity check instead establishes the center target at inception and applies the same projected rule, as reported in Table 11. The base width is held fixed at the inherited b0 = 0 .10, so the comparison isolates initialization rather than width selection. Starting from the center target raises total adjustment in every environment. Table 11: Initial-position sensitivity. The main rule p …

- **p.15** (BM25 -4.797):
  > ind. The continuation rule instead assumes the desk already holds the position it needs at date 0. Table 13 shows that the difference is small in High Liquidity and material when spread and impact are large. 15

- **p.2** (BM25 -4.535):
  > ncertainty. Neagu et al. (2024) embed convex and persistent market impact in a deep reinforcement-learning policy. Huang and Lawryshyn (2025) evaluate reinforcement-learning hedgers under market impact, slippage, and transaction costs. Shinozaki (2024) reviews deep hedging and deep calibration as practical deep-learning tools for finance. A learned hedge’s position can also function as a statistical-arbitrage trade. Horikawa and Nakagawa (2024) relate the difference between deep and delta hedging to statistical arbitrage in a complete-market setting. Fran¸ cois et al. (2025b) show in an incomplete-market experiment that the speculative position depends on how strongly the risk measure penali …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
