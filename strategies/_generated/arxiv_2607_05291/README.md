# Forecasting Realized Volatility with Time Series Foundation Models: A Comparison with Econometric Benchmarks

Auto-generated bundle from `arxiv:2607.05291`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.05291v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.05291",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.05291")`.

### Auto-retrieved passages

- **p.24** (BM25 -6.068):
  > r at h = 22, where the HAR family undershoots (Tab. 9). The GR test shows that relative performance against Log-HAR is time-varying (Fig. 3). The wide heterogeneity across foundation- model architectures, from TTM’s consistent frontier position to the parity-or-worse loss ratios of Chronos-Bolt, TimesFM 2.5, and Moirai-MoE-S, indicates that pretraining-data composition and output mechanism matter far more than membership in the foundation-model class. 7 Robustness Checks The results in Secs. 5 and 6 establish model rankings and their statistical significance. A natural question is whether these rankings are stable across market regimes, estimation choices, and evaluation parameters. We asses …

- **p.36** (BM25 -4.73):
  > er-only model with patch-plus-residual tokenization (200M parameters), outputting a mean forecast plus nine quantiles per step; it was pretrained on a mixture of Google Trends and public time series corpora. We use the TimesFM 2.5 checkpoint17 and take the conditional mean as the point forecast. Toto (Cohen et al., 2024).Datadog’s decoder-only model (151M parameters), pretrained primarily on observability metrics (CPU usage, request latency), the training domain furthest from finance in our study. Its decoding head parameterizes a Student-t mixture; because that predictive distribution is heavy-tailed, we take the analytic conditional mean rather than a sample mean for numerical stability. W …

- **p.36** (BM25 -4.63):
  > Moirai-MoE (Liu et al., 2024a).Extends Moirai with a sparse MoE layer, so only a fraction of parameters are active per input: the small checkpoint has 117M total parameters, roughly 11M active per forward pass. Like Moirai 2.0 it uses patch tokenization and outputs nine quantile levels. We use this checkpoint15 and take the conditional mean as the point forecast. Lag-Llama (Rasul et al., 2024).A decoder-only model based on LLaMA that, unlike the patch-based models above, tokenizes each step with lag features (the current value and a fixed set of lagged values) and parameterizes a Student-t distribution per step. We use the pretrained checkpoint16 (8 layers, 9 attention heads, 16-dimensional  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
