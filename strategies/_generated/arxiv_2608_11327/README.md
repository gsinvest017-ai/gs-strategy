# Long-Horizon Forecasting of Complete Financial Statements with Forma

Auto-generated bundle from `arxiv:2608.11327`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.11327v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.11327",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.11327")`.

### Auto-retrieved passages

- **p.11** (BM25 -5.63):
  > horizon) pair directly rather than recursively, so comparisons isolate the pipeline, not forecast strategy; the penalized regression and RF fit a separate model per pair, while the FFNNs and Forma share parameters across all pairs through a vector output head. The FFNNs are five-seed ensembles with the same heteroskedastic head and mixture treatment as Forma, so they also enter the density track. Two simple baselines anchor the table. The seasonal random walk repeats each item’s most recent value from the same fiscal quarter, the standard naive expectation for quarterly accounting series [3, 14]. The fade/AR(1) baseline fits one pre-test OLS regression per item and horizon, pooled across fir …

- **p.30** (BM25 -4.607):
  > total liabilities plus total stockholders’ equity, which by the balance identity (§ A.5) equals total assets less noncontrolling interests, up to sign conventions. The primary definition is valid when both components are reported and the sum is finite and positive; the total-assets fallback rescues 6,350 firm-quarters, and firm-quarters with no valid deflator under either definition are dropped from the panel (357,422 firm-quarters; Table4). We call the surviving firm-quartersscale- valid. For an origin (𝑓 , 𝑡), every model input and target — at every lead and lag in the window — is deflated by the origin deflator𝑧𝑓 ,𝑡; deflators at other quarters enter only the normalization statistics belo …

- **p.36** (BM25 -4.203):
  > ma canonical hyperparameters (identical across the five mixture seeds; only the seed differs). Architecture Encoder layers /𝑑model / heads 4 / 128 / 4 Feed-forward width / dropout 512 / 0.2 Trainable parameters (incl. variance head) 942,210 Optimization Optimizer AdamW (default 𝛽, 𝜖) Learning rate 10−4, constant Weight decay 0.1 (all parameters) Gradient-norm clip 1.0 Batch size 32 firm-origin sets Epochs 12 (final-epoch weights used) Precision fp32 (medium matmul precision) Seeds 60–64 (equal-weight mixture) Loss Objective Gaussian𝛽-NLL, 𝛽 = 0.5 log 𝜎 2 clamp [−10, 10] Absolute-error-track variant Laplace𝛽-NLL, 𝑏 = 𝜎 /√2 Horizon curriculum Initial → max horizon 4 → 20 quarters Step +4 per e …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
