# Public Trader Identity: Adverse Selection and Return Predictability

Auto-generated bundle from `arxiv:2608.04373`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.04373v3

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.04373",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.04373")`.

### Auto-retrieved passages

- **p.32** (BM25 -3.242):
  > an gap traded intois the signed gap in basis points, negative when the order trades against the displacement. The final two columns restrict to orders facing a gap of at most one basis point, where there is nothing to arbitrage; these are 22% of all orders. Fama–MacBeth daily D10−D1 markout coefficients over July 11–20 average 1.72 without gap controls and 1.75 with them. Because the oracle can be up to ten seconds stale, the test bounds a slow cross-venue channel but cannot rule out a subsecond one. into, and the markout that survives in the subsample where the gap is at most one basis point. B.3 Tail Cut and Score Definition The forecasting result would be fragile if it depended on the exa …

- **p.39** (BM25 -2.928):
  > 0.2 s 0.5 s 1 s 2 s 5 s 10 s 30 s Horizon 0 5 10 15Out-of-sample R2 (%) (a) Predictability July 2026 December 2025 Benchmark + identity Anonymous benchmark 0.2 s 0.5 s 1 s 2 s 5 s 10 s 30 s Horizon 0 5 10 15 20Relative identity gain (%) (b) Identity gain July 2026 December 2025 Figure C.2: Top-decile ridge results in July 2026 and December 2025. Panel (a) compares the anonymous benchmark with the model including identity; Panel (b) shows the relative identity gain. D How Large Is the Increment? A forecasting increment is easier to judge in payoff units than inR 2, so we convert the half-second increment into a midpoint payoff per unit of gross exposure. At each grid step the position is prop …

- **p.39** (BM25 -2.576):
  > tting-window forecast-magnitude quantiles; realized acted-grid shares are reported separately. Per unit of gross exposure, the always-on identity edge exceeds the benchmark’s by 7.0% (t= 7.8). That is close to the p 11.76/10.16−1 = 7.6% implied mechanically by theR 2 gain, which is the check the exercise has to pass: the conversion should reproduce the forecasting result in payoff units, and it does. Thresholded comparisons vary across activation budgets (Table D.1). The exercise is frictionless and evaluated at the midpoint, with no book, queue, fill probability, spread, or inventory, so it is a unit conversion rather than evidence of capture. As a standalone taker strategy the gated rows’  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
