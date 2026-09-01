# A Per-Component Diagnostic Protocol for Neural HJB-PIDE Solvers under Control-Dependent Lévy Jumps

Auto-generated bundle from `arxiv:2606.01122`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.01122v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.01122",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.01122")`.

### Auto-retrieved passages

- **p.23** (BM25 -4.991):
  > he fitted parameters below are stored verbatim indata/mle_parameters.json. MLE setup.We calibrate a Variance Gamma model to S&P 500 daily returns from January 4, 2010 to December 29, 2023 (𝑛= 3,522trading days), derived from a user-supplied daily close series. The VG parameters are estimated by maximum likelihood and standard errors come from a finite-difference Hessian: Parameter Estimate Std. error Interpretation 𝜇7.35×10 −4 1.31×10−4Daily drift 𝜎1.05×10 −2 1.98×10−4Diffusive scale 𝜃−3.22×10 −4 2.20×10−4Negative skew (not significantat conven- tional levels,𝑡≈−1.46) 𝜈1.179 0.059VG kurtosis parameter 23

- **p.23** (BM25 -4.62):
  > now-explicit admissible set𝒰= [0, 1], and the corrected long-only setting produces only modest tail-metric movement. We retain the calibration so the data pipeline and the figure caption are honest. Data provenance and reproducibility.The S&P 500 calibration uses daily close data for 2010–2023 obtained from a user-provided lawful data source. To avoid redistributing third- party index data, the supplement includes the calibration scripts, the expected CSV schema, and the fitted parameters used in the reported audit, but not the raw index levels or derived return series. The reported numbers can be reproduced by placing a lawfully obtained daily close series atdata/sp500_user.csv and running  …

- **p.11** (BM25 -4.517):
  > 4.1 Experiment 1: Diffusion-Only Validation Setup: Standard Merton parameters with no jumps: •Risk-free rate𝑟= 0.02, expected return𝜇= 0.08, volatility𝜎= 0.2 •Risk aversion𝛾= 2.0, horizon𝑇= 1year •Lévy measure: Compound Poisson with intensity𝜆= 0(no jumps) Analytical benchmark: Merton ratio𝑢* = 0.08−0.02 2.0×0.22 = 0.75. Results(5 seeds, mean±std): Method Optimal𝑢Mean|rel. err|Per-seed range Analytical (Merton) 0.7500 – – Neural Solver0.762±0.011 1.6% [0.750,0.774] The neural solver recovers the Merton ratio with a 5-seed mean error of1.6%(𝑢= 0.762± 0.011), validating the basic methodology before introducing jumps. 4.2 Experiment 2: Variance Gamma Jumps Setup: Same base parameters, but with  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
