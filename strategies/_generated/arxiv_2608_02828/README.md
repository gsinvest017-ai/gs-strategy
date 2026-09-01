# Proper-score observation-driven filters: local geometry, estimation, and continuous-time limits

Auto-generated bundle from `arxiv:2608.02828`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.02828v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.02828",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.02828")`.

### Auto-retrieved passages

- **p.53** (BM25 -5.507):
  > PROPER-SCORE OBSER V ATION-DRIVEN FILTERS 53 log density-power 0.00 0.01 0.02 0.03 0.04 0.05 0.06 RMSE deterioration: jumps ¡ clean (a) clean-fit parameters frozen log density-power (b) parameters refitted under jumps Gaussian density Student-t6 density Figure 11.Misspecification by one-sided half-normal jumps: paired jump-minus-clean de- terioration in the root-mean-square error of filtered log-variance against the latent diffusive component, with±1 paired stationary-block-bootstrap standard-error bars. The bootstrap holds fitted parameters and realised clean/jump paths fixed and resamples paired post-fit errors. (a) Parameters fitted on clean training data and frozen across the paired arms …

- **p.56** (BM25 -4.764):
  > 56 LIVIERI AND PALMARI The second is a genuinely online joint estimator of static and dynamic parameters, rather than the batch estimator analysed here.

- **p.16** (BM25 -4.646):
  > functionΓ : Λ→(0,∞) is monotonic and differentiable and acts on aF t−1-measurable time-varying parameterλ t. The law of motion ofλ t is a first-order autoregressive scheme: we add an interceptωand an autoregressive parameterφto the scaled scoring-rule update of Definition 2.4. For the logarithmic scoreS≡S log, the link between the

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
