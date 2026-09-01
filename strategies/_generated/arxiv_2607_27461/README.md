# Are Three Matrices All You Need To Beat the Market? Observable Matrix Dynamics for Portfolio Optimization

Auto-generated bundle from `arxiv:2607.27461`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.27461v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.27461",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.27461")`.

### Auto-retrieved passages

- **p.44** (BM25 -19.431):
  > adeable book on market data with the reactive blend. The regime-aware chains of Section 2.2 change this reading in part. Ranking the same drivers with the fixed regime-aware thresholds rather than each name’s own deciles leaves the leaders themselves almost unchanged, so the leadership is a property of the market and not of the discretization. The out-of-sample forecast they carry, however, improves. A market-timing signal built from the regime-aware leaders beats the market’s own momentum on the dot-com and the recent windows, a rank correlation with the forward market of 0.20 and 0.11 against the momentum baseline’s 0.12 and 0.08, where the own-decile signal never beat momentum 44

- **p.4** (BM25 -14.612):
  > ing while momentum only follows it. Under forecast the chains diverge: the volatility ranking is pre- dictable out of sample and carries memory beyond a single step, while the return ranking stays close to unforecastable. Turned into a portfolio, a market-neutral momentum long-short blended adaptively with a long-only sleeve beats the market out of sample, and beats the clas- sical minimum-variance and maximum-diversification portfolios. A forward test over a clean, non-overlapping window from January 2025 to July 2026, which the study never saw, con- firms it at a daily-marked Sharpe of 1.32 against the market’s 1.14 and roughly double its return. Diversifying the long sleeve by residual di …

- **p.13** (BM25 -14.585):
  > exogenous risk descriptor. For momentum the net flow is negative,−4.5×10 −3, so the rank leads the characteristic rather than the reverse. This is the consistency check anticipated in Section 2.8. The twelve-minus-one momentum is a function of past returns, so it echoes the recent rank rather than anticipating it, and the directional transfer entropy recovers exactly that. The two diagnostics thus play complementary roles, the entropy-production attribution ∆σmeasuring how much directional structure a covariate resolves, and the net transfer entropy telling whether the covariate drives the ranking or trails it. 3.3 Distance-matrix predictors The return chain is hard to forecast from the mark …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
