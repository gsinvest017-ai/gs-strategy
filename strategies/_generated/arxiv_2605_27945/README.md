# Stochastic Volatility, Jumps, and Rates: A Unified Framework for Option Pricing and Term-Structure Simulation

Auto-generated bundle from `arxiv:2605.27945`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.27945v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.27945",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.27945")`.

### Auto-retrieved passages

- **p.6** (BM25 -5.394):
  > 4.2 Step 2 – Mid-Term (60-Day) Bates Calibration and Put Pricing 4.2.1 Bates Model Calibration via Lewis (2001) Fourier- Based Approach To incorporate jump discontinuities in the underlying stock dynamics, we extend the calibrated Heston model to the Bates (1996) framework. We again use the Lewis (2001) Fourier transform pricing method for European call options. Calibration was performed by minimizing the mean squared error (MSE) between observed market and model prices of SM 60 - day call options. A sequential calibration approach was applied: 1. Calibrate Heston stochastic volatility parameters 2. Fix those values and estimate jump parameters 3. Jointly re-optimize all parameters (Cont & T …

- **p.3** (BM25 -4.701):
  > 5; Storn & Price, 1997) 4.1.1 Calibration (Lewis 2001 Approach) The model parameters were estimated by minimizing the mean squared error (MSE) between observed market prices and model-implied prices: 𝑀𝑆𝐸 = 1 𝑁 ∑(𝐶𝑖 𝑚𝑜𝑑𝑒𝑙 − 𝐶𝑖 𝑚𝑎𝑟𝑘𝑒𝑡) 2 𝑁 𝑖=1 The resulting calibrated parameters are presented in Table 2. Table 2. Calibrated Parameters Parameter Symbol Value Mean reversion ( 𝜅 ) 0.3981 Long-run variance (𝜃) 0.08748 Vol-of-vol (𝜎) ≈ 0 Correlation (𝜌) 0.9906 Initial variance (𝑣0) 0.1016 (Heston 1993; Lewis 2001; Storn & Price 1997). The fitted σ≈0 suggests near-deterministic volatility over 15–120 day maturities. Pricing performance remained strong which means market does not require stochastic v …

- **p.7** (BM25 -4.648):
  > hen jumps are added, the estimated parameters, jump intensity λ≈0, jump volatility σJ≈0, and mean jump size μJ≈−0.5%, suggest that the market does not expect frequent or large jumps over a 60-day horizon. The small negative μJ mild downside risk but no strong evidence of crash-like events. Overall, the calibration indicates a stable market regime where con tinuous diffusion dominates and jump risk is negligible (Bates, 1996; Pan, 2002; Cont & Tankov, 2004). 4.2.2 Bates Model Calibration via Carr Madan (2001) We obtain calibrated Bates (1996) parameters in table 16. Table 16 Bates parameters (FFT) Parameter Symbol Calibrated Value Mean reversion (𝜅𝑣) 15.643 Long-run variance (𝜃𝑣) 0.15858 Vol- …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
