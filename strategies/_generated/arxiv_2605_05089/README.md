# Dynamic Collateral Control for Permissionless Spot Perpetual Basis Trading

Auto-generated bundle from `arxiv:2605.05089`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.05089v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.05089",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.05089")`.

### Auto-retrieved passages

- **p.23** (BM25 -7.601):
  > APPENDIXE FUNDING-ENVIRONMENTBACKTESTSUMMARIES This appendix reports the full ticker-level historical-validation summaries used in Section IX. The calibrated control rule, historical target parameters, and Hyperliquid margin architecture are held fixed; only the funding input is changed between the Binance-funding and Hyperliquid-funding runs. Fig. 14: Normalized strategy NA V across all tickers under the two funding environments. Solid lines denote Binance funding; dashed lines denote Hyperliquid funding.

- **p.16** (BM25 -4.068):
  > ity Let q∗ buy(t) and q∗ sell(t) denote the trade sizes implied by the dynamic control rule when the strategy attempts to move from the realized state αt back toward the benchmark target α†. A lower-side intervention is operationally feasible only if αt < α L andq ∗ buy(t)∈ Q buy(t),(63) whereas an upper-side intervention is feasible only if αt > α U andq ∗ sell(t)∈ Q sell(t).(64) Hence, a control trigger is operationally valid only if the re- quired rebalancing size lies inside the corresponding admissible liquidity set. To translate this condition into strategy capacity, write the required rebalancing size on the sidesas q∗ s(t) =ϕ s(αt, α†)Vt, s∈ {buy,sell},(65) where Vt is the equity in  …

- **p.14** (BM25 -3.961):
  > ly exposed to short horizon spread volatility. This motivates two practical implementation parameters. The first is a minimum trade size. Based on the observed fixed transaction-cost layer and the fixed Hyperliquid withdrawal charge, we adopt an empirical lower bound of approximately $10k for economically meaningful rebalances. The second is the execution buffer b, which absorbs the quote-to-fill execution error and also acts as protection against misspecification in the effective funding gain available at the moment of rebalancing.

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
