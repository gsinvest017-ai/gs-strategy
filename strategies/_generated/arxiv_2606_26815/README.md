# Data-Driven Duration Management -- Term Structure Forecasting Using Machine Learning

Auto-generated bundle from `arxiv:2606.26815`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.26815v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.26815",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.26815")`.

### Auto-retrieved passages

- **p.16** (BM25 -7.069):
  > parameters are reused, and full recalibration occurs only during the global re-estimation step to keep the forecasting process computationally feasible. Table A1 summarizes all the 43 models that are tested. All inputs and outputs for NNs and AEs are normalized to have unit variance. The NNs and AEs are implemented in Python using the keras and tensorflow libraries. The RMSprop optimizer and Mean Squared Error (MSE) loss are used for training. 3 Model Performance In this section, we describe the procedure adopted for hyperparameter tuning of both the autoencoders AEs and the NNs used for factor-based and direct rate forecasting. Before detailing the model optimization process, we first outli …

- **p.15** (BM25 -6.758):
  > ws a two-tier strategy: • Global Re-estimation:Every two years (104 weeks), the model is retrained from scratch for multiple epochs with random weight initialization. This periodic retraining helps the model avoid local minima and adapt to long-term patterns (Tashman, 2000). • Local Updates:On a weekly basis, the model is updated only with the new data by training for a single epoch. For models that combine AFNS with a NN, the computationally intensive optimization of AFNS parameters is not repeated at every training epoch. Instead, previously estimated 15

- **p.19** (BM25 -5.685):
  > of Bayesian Optimization (BO) and the scalability of Hyperbands (HB). It uses BO to select promising hyperparameter configurations instead of random sampling and employs the HB suc- cessive halving strategy to allocate computational resources, quickly discarding poorly performing configurations and dedicating more resources to promising ones (Falkner et al., 2018). We optimized the hyperparameters for three distinct model components: the AEs for factor extraction, the NNs for forecasting factors, and the NNs doing direct zero-rate prediction. 3.3.1 Autoencoders for F actor Extraction The primary optimization objective for the AEs was to find the set of hyperparameters that minimized the MSE  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
