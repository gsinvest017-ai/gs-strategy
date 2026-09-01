# The Reconfiguration Premium: Co-movement Structure as an Unspanned Dimension of the Variance Risk Premium

Auto-generated bundle from `arxiv:2608.20020`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.20020v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.20020",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.20020")`.

### Auto-retrieved passages

- **p.20** (BM25 -7.526):
  > , and its apparent pricing is intensity. It is retired here rather than defended. Adjudication at daily resolution, where the observation count is not binding, is the companion paper’s subject; the answer there is also negative, for a different and more informative reason having to do with which sampling frequency the premium selects. 7.2 There is no timing alpha The index is a conditioning variable, not a signal. Scaling exposure to a short-variance position by the expanding-window standardized index,1 + 0.5zt, and comparing the result to the unconditional position at equal volatility yields a pairedt of−1.85across 329 months [08b] — against the overlay, not for it. Unconditional and scaled …

- **p.28** (BM25 -4.394):
  > h, which costs a further 36-month burn-in and leaves 293 of the 329 payoff months; 69 of them (24 percent) are flagged top-quartile in real time. Each rule is compared to the unconditional position after rescaling to equal volatility, and the reported statistic is the pairedt on the difference. Split in half, the step form gives−0.97on 2001:07–2013:08 and−0.07on 2013:09–2025:11. The step was pre-committed as a diagnostic because Table 13 suggested it, and it is reported whatever it shows. None of the three forms improves on the unconditional position, and the third — which concentrates the book into the top quartile — is significantly worse. C.4 Caveats.Three qualifications limit any strateg …

- **p.29** (BM25 -3.004):
  > Table C1:Timing rules against the unconditional short-variance position [08c].n= 293. Rule Weight Sharpe Equal-volatilityt Unconditional11.28 — Linear tilt1 + 0.5z t 1.22−0.81 Step tilt1 + 0.5·1{Q4}1.25−0.94 Top quartile only1{Q4}1.02−2.23 one-month variance-swap payoff would use the canonical construction against which the index is not priced (Section 6.4). Selling variance atVIX2 ignores the convexity correction relating the index to the fair variance-swap strike (Demeterfi et al., 1999; Britten-Jones and Neuberger, 2000), as well as transaction costs and margin. And the Sharpe ratios quoted in Section 7.2 inherit both distortions. The tables are an attribution of where the premium studied …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
