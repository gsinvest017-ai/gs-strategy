# Equity Strategy Backtesting: Luck or Edge? The MinervaScore as a Statistical Robustness Grade

Auto-generated bundle from `arxiv:2608.23808`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.23808v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.23808",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.23808")`.

### Auto-retrieved passages

- **p.4** (BM25 -7.832):
  > ot interpret Φ( S−c ) as a calibrated probability. Instead, we use it as a ranking measure, and§6.5 evaluates how closely it approximates a calibrated probability. Finally, the continuous scoring framework is used only to rank strategies within the same pass/fail category and never across the pass/fail boundary. 2 The Search Pipeline A trading strategy is a set of trading rules together with the parameter values used by those rules. For example, a moving-average crossover strategy specifies buying when a short moving average crosses above a long one and selling when it crosses back, with parameters such as the two averaging windows, a minimum crossover distance, and a stop-loss level. Amodel …

- **p.4** (BM25 -5.528):
  > e development. In this dataset, which contains little evidence of genuine edge, we find no evidence that the score predicts out-of-sample outcomes. We report these null results in full and explain why they replace the conclusions of an earlier study, whose null findings can be attributed to a design flaw.(5) A public audit based on 359,062 real results(§8). The audit shows that no strategy saturates the top of the scale, the pass/fail guarantee holds without exceptions, and the ranking remains largely unchanged when all tuning parameters are varied by ±20%. We also quantify the contribution of each of the five gates to the final score. Scope.We do not claim that the score has demonstrated fo …

- **p.4** (BM25 -4.473):
  > rategy, a Kalman-filter-based strategy, and a moving-average crossover strategy are different models, each with its own parameter space. The parameter search is therefore determined by the chosen model. 2.1 Where optimization enters The user first selects a trading model, an instrument (or a universe of instruments), a historical period, and a bar interval. The Minerva platform then searches for parameter values that optimize 4

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
