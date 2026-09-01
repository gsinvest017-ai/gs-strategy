# A Validated Volatility-Volume-Gap Classifier for Regime Identification in MNQ Intraday Data

Auto-generated bundle from `arxiv:2605.11423`.

Template: **mean_reversion**

Matched keywords: `reversal`

Paper URL: http://arxiv.org/abs/2605.11423v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.11423",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.11423")`.

### Auto-retrieved passages

- **p.11** (BM25 -16.196):
  > reflects a specific macro regime rather than a robust structural edge. 4.4 Strategy 3: Intersection Reversal with Regression Filter This configuration applies a more rigorous entry filter: enter only on days where all three classifier conditions are simultaneously in the top tercile AND the ordinary least squares regression of the first-30-minute return predicts a reversal above a minimum confidence threshold. This is the “intersection reversal” signal referenced in Section 3. Mesfin (2026) | 11

- **p.11** (BM25 -15.949):
  > Table 8. Strategy 1: Reversal entry results. The reversal strategy fails primarily on statistical significance: T = 0.86 does not approach the 2.0 threshold. The directional asymmetry—long side (+5.20 pts) materially outperforming short side (−2.38 pts)—reflects MNQ’s structural bullish bias, which partially offsets the reversal signal’s short-side predictions. Year stability is also absent: 2022 is negative, 2023 and 2024 trend positive but never individually reach T = 2.0. The aggregate T of 0.86 is consistent with a small positive effect dominated by noise. 4.3 Strategy 2: Continuation Entry (Trade Opening Direction) The continuation hypothesis is the mirror of the reversal: enter in the  …

- **p.13** (BM25 -13.33):
  > ies underpowered 1.10 n/a FAIL — T = 1.10 Table 11. Strategies 4–8: Additional tested configurations. All fail institutional threshold. The close fade at 15:30 is the most structurally motivated entry given the 77.6% peak reversal rate documented in Section 3.3. However, the small number of trades (fewer than 30 even with 40 classifier days, due to session time constraints and valid signal filtering) makes it impossible to evaluate statistically. The T = 1.08 result on 8 trades is directionally consistent with the reversal hypothesis but provides no meaningful evidence given the sample size. The midday continuation strategy (T = 0.33) and volatility regime split (T = 1.10) both produce posit …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
