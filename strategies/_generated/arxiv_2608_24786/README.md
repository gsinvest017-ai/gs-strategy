# Harvesting the Volatility Risk Premium: A Learning-to-Rank Approach

Auto-generated bundle from `arxiv:2608.24786`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.24786v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.24786",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.24786")`.

### Auto-retrieved passages

- **p.7** (BM25 -15.534):
  > ture pipeline and the position-sizing layer. The selected position is held to expiration and closed against the official PM cash settlement. The day’s gross profit and loss for a short put position is P&Lgross =Q·multiplier·  pentry −max(K−S settle,0)  ,(3) where pentry is the per-share entry premium received, Q is the contract count selected by the sizing layer, and the SPXW multiplier is 100. 3.2 Ranking Target Construction The ranker is trained against a per-day per-strategy score that reflects both realized premium collection and intraday drawdown stress. The score is constructed in four steps: per-bar profit-and-loss, aggregation into a Sortino-on-bars score,SKIPinjection, and ordinal …

- **p.37** (BM25 -14.704):
  > Figure 5. Feature-group ablation impact bars across sizing methods. 2.5 2.0 1.5 1.0 0.5 0.0 0.5 1.0 Sharpe calendar morning SPX index VIX macro vol surface RV/IV higher moments VIX curvature trend position greeks per-strategy stats entry liquidity intra-strategy regime sensitivities FMU 2 1 0 1 2 Sharpe VT 3 2 1 0 1 Sharpe SRS 3 2 1 0 1 Sharpe EA 2.0 1.5 1.0 0.5 0.0 0.5 1.0 1.5 Sharpe calendar morning SPX index VIX macro vol surface RV/IV higher moments VIX curvature trend position greeks per-strategy stats entry liquidity intra-strategy regime sensitivities GB 5 4 3 2 1 0 1 Sharpe HK 5 4 3 2 1 0 1 2 Sharpe QK WF Sharpe OOT Sharpe Note:Per-method horizontal bar charts of ∆ Sharpe relative to …

- **p.24** (BM25 -13.531):
  > these survive across all four walk-forward windows and the out-of-time window, and are common to every fitted model. The remainder are window-specific or window- frequent, and Section 6.3 quantifies the marginal contribution of each base group. 5 Empirical Results 5.1 Setup The strategy is evaluated over the period 2017–2025. The 2017 calendar year provides warm-up data for rolling features and per-strategy statistics, and the initial training window covers 2018–2020. The four-window walk-forward (WF) with annual retraining on an expanding window spans 2021–2024, and the 2025 calendar year is reserved as an out-of-time (OOT) hold- out, never used during training, hyperparameter search, or mo …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
