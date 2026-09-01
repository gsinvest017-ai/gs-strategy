# The Bounce Has No Direction: Sign, Magnitude, and the Microstructure of Equity Return Predictability

Auto-generated bundle from `arxiv:2606.29591`.

Template: **mean_reversion**

Matched keywords: `mean reversion, reversal`

Paper URL: http://arxiv.org/abs/2606.29591v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **mean_reversion** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.29591",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.29591")`.

### Auto-retrieved passages

- **p.23** (BM25 -23.849):
  > . QQQ’s weeklyVR(5) = 0.975- much closer to one thanVR daily(5) = 0.850 - suggests that its short-horizon reversal at daily frequency is predominantly microstructure driven, while the long-horizon momentum (VRweekly(20) = 1.073) is structural. 9 Cross-Asset Evidence The cross-asset panel tests whether the microstructure mechanisms identified in equity markets generalise to other asset classes. If the FRI channel predictions in Table 1 are correct, the pattern of rejections should follow from each class’s market structure. Table 8: Variance-ratio evidence across seven asset classes (Bonferroni joint test, α= 5%, daily returns, 21 instruments). Rej/N: number of Bonferroni rejections out of ins …

- **p.23** (BM25 -22.678):
  > or ETF XLK, XLF, XLE, XL V, XLU 2/5 Mean reversion; all dVR<1 Intl equity EF A, EEM, EWJ 3/3 Mean reversion; EEM strongest Fixed income TLT, IEF, LQD, HYG 0/4 Treasuries revert; credit R W Commodities GLD, SL V, USO, DBC 0/4 Random walk; oil slight momen- tum FX UUP, FXE, FXY 0/3 USD/JPY weak reversal; EUR R W Cryptocurrency BTC, ETH 0/2 Closest to random walk in panel Equities: the universal pattern.Every equity instrument in the panel - 10 US names, 3 international - hasdVR(5)<1. The pattern holds across all ge- ographies, sectors, and market-cap segments. Emerging-market equities (EEM) show the strongest reversal (dVR(5) = 0.799,z ∗ <−3), consistent with the non- synchronous prediction: E …

- **p.21** (BM25 -21.755):
  > nflates both the magnitude of the bounce (wider spreads generate larger autocorrelation per the Roll formula) and the non-synchronous effect (illiquid constituents in market stress become more stale). Third,VR(60)is lowest in the calm 2010–2019 period (0.548), the era of persistentlylowvolatilityandhistoricallytightbid-askspreadsfollowingthepost- crisis microstructure improvements. This is consistent with VR mean reversion 21

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
