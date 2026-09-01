# AlphaZeroBeta: Deep Reinforcement Learning for Market-Neutral Portfolios

Auto-generated bundle from `arxiv:2607.18001`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.18001v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.18001",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.18001")`.

### Auto-retrieved passages

- **p.29** (BM25 -11.825):
  > aseline), averaged across the 22 walk-forward folds and the seven mar- kets. The marginal drops are 37% (price/momentum), 18% (volatility/regime), 12% (macro/cross-asset), and 9% (sentiment/flows); the remaining 24% reflects interaction effects and redundancy across blocks. Integrated gradients, averaged over 256 random test-window evaluations per market, confirm that price/momentum and volatility sig- nals dominate the policy logits, while macro and sentiment features mainly modulate position sizing. These diagnostics are consistent with the factor loadings in Table 5: AlphaZero- Beta behaves as a trend-following policy modulated by volatility-aware sizing, with significant momentum loading …

- **p.44** (BM25 -5.816):
  > self.prices, self.features = prices, features self.cost_lookup = cost_lookup # date -> bps per side self.capital = float(capital) self.reset() def reset(self): self.t, self.position = 0, 0 # position in {-1, 0, +1} self.cash = self.nav = self.prev_nav = self.capital return self._get_state() def _get_state(self): return np.concatenate([self.features[self.t], [self.position, self.cash / self.capital]]) def step(self, action): p_t, p_next = (float(self.prices["close"].iat[i]) for i in (self.t, self.t + 1)) dpos = action - self.position tc = self.cost_lookup(self.prices.index[self.t]) * 1e-4 * abs(dpos) * p_t self.cash -= tc + dpos * p_t self.position = action self.nav = self.cash + self.positio …

- **p.21** (BM25 -5.51):
  > 5.3.3 Maximum Drawdown Maximum drawdown (MDD) quantifies the largest historical peak-to-trough loss during the investment horizon: MDD = min t∈[0,T]  Vt −V max Vmax  ,(14) whereV t is the portfolio value at timetandV max = max τ≤t Vτ is the run- ning maximum. MDD provides a measure of capital risk under worst-case historical scenarios [17]. 5.3.4 Cumulative Return Cumulative return measures the total profit or loss accrued over time without account- ing for risk. It is computed as the cumulative sum of portfolio-level profit and loss: Ct = tX s=1 ∆Ps,(15) where ∆P s denotes the change in portfolio value at times, computed as the inner product of asset price changes and lagged position size …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
