# Robust Hedging Valuation Adjustment under Liquidity--Demand Stress

Auto-generated bundle from `arxiv:2606.26731`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.26731v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.26731",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.26731")`.

### Auto-retrieved passages

- **p.2** (BM25 -4.113):
  > ˆ∆ t =∂SV(t,S t) = Φ(d 1),(1) where d1,2 = log(S/K) + (r±1 2σ2)(T−t) σ √ T−t . Consider rebalancing dates0 =t 0 < t1 <···< tn =T. The band widthb≥0is measured in units of underlying per option. Let∆ti(b)be the hedge position held after rebalancing atti. Initializing∆ t0(b) = ˆ∆ t0 and fori= 1,...,n−1, ∆ ti(b) = {ˆ∆ ti,if| ˆ∆ ti−∆ti−1(b)|>b, ∆ ti−1(b),otherwise. (2) At maturity the hedge is unwound by setting ∆ tn(b) = 0. We define the rebalancing trade at timeti as the change in the underlying position, ∆q i(b) = ∆ ti(b)−∆ti−1(b). A positive∆q i(b)is a purchase of the underlying, and turnover is measured by the trading volume Xi(b) =S ti|∆qi(b)|. 3 Kullback–Leibler robust HVA Letm ti≥1denote …

- **p.4** (BM25 -3.263):
  > e common settings. The band grid ranges from daily rebalancing (b= 0) to a wide no-trade band (b= 0.5). The three liquidity environments are generated with a risk-neutral Merton jump-diffusion [Merton, 1976], dSt St− = (r−λJκJ)dt+σmamdWt + (J−1)dNt,logJ∼N(µ J,σ2 J),(13) whereN t has intensityλJ andκJ = exp(µJ + 1 2σ2 J)−1. Table 2 gives the liquidity environments. They vary the half-spread, the quadratic impact coefficient, the stress multiplier, liquidity persistence, diffusion volatility, and the jump parameters. The high-liquidity case assumes a small half-spread with almost no impact. The medium- and low-liquidity cases use largersandκto represent more expensive trading. The high-liquidi …

- **p.15** (BM25 -3.149):
  > Loss samples under no-trade-band delta hedging Require:Bandb, time gridt 0,...,tn, price pathS i, target delta ˆ∆ i, discount factorsB i =e −rti, cost parameters(s,κ), illiquidity multipliersmi Ensure:Path lossL, discounted turnover summaries 1:ϕ0←ˆ∆ 0,L←0,turn1←0,turn2←0 2:fori= 1,...,n−1do 3:if| ˆ∆ i−ϕi−1|>bthen 4:ϕ i←ˆ∆ i 5:else 6:ϕ i←ϕi−1 7:end if 8:X i←Si|ϕi−ϕi−1| 9:L←L+B imi(sXi +κX2 i ) 10:turn1←turn1 +B iXi,turn2←turn2 +B iX2 i 11:end for 12:Maturity unwind:ϕ n←0,Xn←Sn|ϕn−ϕn−1| 13:L←L+B nmn(sXn +κX2 n) 14:turn1←turn1 +BnXn,turn2←turn2 +B nX2 n 15

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
