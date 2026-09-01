# Synthetic American Option Pricing via Jump-HMM-Driven Heston Implied Volatility

Auto-generated bundle from `arxiv:2605.13998`.

Template: **mean_reversion**

Matched keywords: `mean-reversion`

Paper URL: http://arxiv.org/abs/2605.13998v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.13998",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.13998")`.

### Auto-retrieved passages

- **p.3** (BM25 -19.625):
  > frequently than a Gaussian copula would imply. 2.2 Heston stochastic variance model The Heston model Heston [1993] specified the instantaneous return variancevof the underlying asset (i.e., the variance rate of its log-returns) as a mean-reverting square-root process: dv=κ(θ−v)dt+σ v √v dWv (1) whereκwas the mean-reversion speed controlling how quickly the variance returned to its long- run level,θwas the long-run variance target, andσ v was the vol-of-vol governing the amplitude of stochastic fluctuations inv. In the standard formulation, the asset price and variance processes were coupled through a correlationρbetween their driving Brownian motions, producing the leverage ef- fect in which …

- **p.1** (BM25 -19.141):
  > d facts and cross-asset tail de- pendence; a modified Heston stochastic variance process whose mean-reversion target depended on regime state, days to expiration, moneyness, and an aggregate market-mood indicator converted those paths into implied-volatility paths; and a recombining binomial lattice priced American options from the resulting surface with early exercise. A central design choice was initializing the variance pro- cess at its mean-reversion target for each strike-expiration pair, so that the smile, skew, and term structure emerged automatically without external calibration. We calibrated the shape function through a hierarchy of representations spanning a parametric baseline, a …

- **p.2** (BM25 -18.96):
  > i-asset price paths with realistic heavy tails, negligible linear autocorrelation, and persistent volatility clustering Cont [2001], with cross- asset dependence imposed via a Student-tcopula Demarta and McNeil [2005]; a modified Heston stochastic variance process Heston [1993] that converted those price paths into IV paths, where the mean-reversion targetθwas a function of the HMM regime state, days to expiration (DTE), money- ness, and an aggregate market mood indicator; and a Cox-Ross-Rubinstein (CRR) binomial tree Cox et al. [1979] that converted the pre-computed IV into American option prices with early exercise. The central innovation was a hybridθ-function that linked the Heston mean- …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
