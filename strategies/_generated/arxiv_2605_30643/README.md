# Quality-Adjusted Hit-Ratio Targeting in Corporate Bond Market Making

Auto-generated bundle from `arxiv:2605.30643`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.30643v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.30643",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.30643")`.

### Auto-retrieved passages

- **p.27** (BM25 -4.097):
  > Figure 21: Segment hit ratios in the multi-bond simulation. Raw hit-ratio targeting wins residual- toxic flow, while residual-quality targeting reallocates fills toward lower-residual-toxicity flow. Figure 22: Cross-inventory quote skew in a credit-factor book. A long position in one bond widens bids not only in that bond, but also in correlated bonds through the factor covariance matrix. 27

- **p.20** (BM25 -3.833):
  > d event demandI m based on maturity, rating, sector, credit alpha, and idiosyncratic noise. PositiveI m corresponds to passive clients buying from the dealer. Event demand arrives over a concentrated window, shown in Figure 9. Figure 9: Synthetic passive/index event profile used in the reduced-form extension. The sweep grid varies forecast skillρand pre-position fractionθ. Figure 10 shows that aggressive pre-positioning is costly when forecasts are weak, while moderate pre-positioning becomes attractive only when forecast quality is high. 20

- **p.18** (BM25 -3.786):
  > ate raw hit-ratio targeting under plausible flow-quality heterogeneity, but they do not estimate the magnitude of the effect on any real desk. Second, residual toxicity is only as good as the markout adjustment. If carry, rolldown, issuer- RV, index demand, or factor beta are omitted from the adjustment, the model may misclassify sophisticated but non-toxic clients as toxic. This is precisely why the residual definition (10) is central. Third, the style-aware warehousing extension and the passive/index special case are reduced- form. They illustrate inventory-recycling value but do not yet solve a full joint optimal acquisition- and-quoting control problem. The style-aware extension uses a q …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
