# Continuous Cash-Overlay Filters for a Static Growth--Defensive Risk Sleeve: Slow-Tail Compensation, V-Shape Crash Brakes, Walk-Forward Validation, and Max-Cash Combination

Auto-generated bundle from `arxiv:2606.09025`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.09025v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.09025",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.09025")`.

### Auto-retrieved passages

- **p.5** (BM25 -6.306):
  > 90% / -8.03% 2.55% / 0.00% 32.90% / -8.03% 32.39% / -8.03% 32.39% / -8.03% 0.57% 2020 23.82% / -33.59% 0.62% / 0.00% 23.82% / -33.59% 44.55% / -15.11% 44.55% / -15.11% 7.64% 2021 31.04% / -4.92% 0.00% / 0.00% 31.04% / -4.92% 29.36% / -4.92% 29.36% / -4.92% 0.84% 2022 -17.06% / -23.78% 1.29% / 0.00% 2.41% / -13.55% -17.06% / -23.77% 2.41% / -13.55% 24.29% 2023 28.14% / -9.73% 5.13% / 0.00% 27.26% / -9.73% 28.14% / -9.73% 27.26% / -9.73% 3.01% 2024 22.51% / -8.88% 5.17% / 0.00% 22.51% / -8.88% 18.60% / -7.93% 18.60% / -7.93% 3.28% 2025 17.31% / -19.66% 5.13% / 0.00% 17.71% / -19.66% 15.79% / -14.64% 16.18% / -14.64% 7.87% 2026 8.61% / -7.95% 1.03% / 0.00% 8.61% / -7.95% 6.64% / -7.86% 6.64% /  …

- **p.23** (BM25 -5.638):
  > drawdown control with selective return improvement. The full-sample max-cash combination improves both CAGR and maximum drawdown. In walk-forward OOS tests, the main-window expanding and rolling combinations also improve both CAGR and maximum drawdown. Post-2022, expanding improves both metrics, while rolling lowers drawdown but sacrifices CAGR, suggesting that rolling se- lection can over-defend after recent stress regimes. The main limitation is data mining. Variables, interactions, and policy structures were developed on the available sample. The walk-forward tests re-select parameters from past data, but the current study does not yet perform real-time expanding re-screening of variables …

- **p.12** (BM25 -3.396):
  > favor high cash convexity, which means cash exposure is not increased linearly for ordinary stress. Instead, the rule waits for an extreme brake score before allocating substantial cash. This is consistent with the intended use case: the module should be quiet most of the time and aggressive only when crash-like conditions appear. Table 10: V-Shape Event Diagnostics Event Strategy Ret. 100%RRet. Excess Avg. Cash Max Cash Days COVID crash -14.66% -33.17% 18.50% 58.64% 74.88% 24 April 2025 crash -10.17% -14.40% 4.23% 19.33% 74.32% 11 Slow 2022 window -12.43% -12.43% 0.00% 0.00% 0.00% 22 COVID recovery 19.75% 27.21% -7.46% 12.50% 67.54% 28 April 2025 recovery 5.49% 9.90% -4.41% 41.91% 74.54% 16 …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
