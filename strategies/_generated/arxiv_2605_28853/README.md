# Financially Guided Deep Portfolio Optimization

Auto-generated bundle from `arxiv:2605.28853`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.28853v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.28853",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.28853")`.

### Auto-retrieved passages

- **p.5** (BM25 -4.218):
  > vector of portfolio allocation weightsw∈R N (N= 50) through a final softmax layer. Training Hyperparameters: All other hyperparameters other than the ones mentioned below are tuned using Optuna; 100 trials per model-loss combination. The following hyper- parameters are shared across all neural models:

- **p.4** (BM25 -3.579):
  > LCVaR +λ RP · LRP (14) Both losses are minimized during training. The hyperparame- ters control the trade-off between maximizing risk-adjusted return, controlling tail risk, and enforcing diversification. We refer to these as CustomLossA (Sharpe-CVaR-RP) and CustomLossB (Omega-CVaR-RP) respectively. We initially explored 16 combinations of financial metrics (log Returns, Sharpe, Omega, Sortino, Calmar, CVaR, MDD, Risk Parity, HHI, Entropy) as regularizers or primary objectives. Most led to overfitting or poor validation performance. The two loss functions that consistently performed well, CustomLossA and CustomLossB, are used in the experiments. D. Expanding-Window Walk-Forward Procedure To  …

- **p.1** (BM25 -2.567):
  > for portfolio allocation), our models output normalized portfolio allocation weights. Our key contribution is an integrated, end-to-end framework that combines: (i) differentiable surro- gates for financial metrics (Sharpe, Omega, CVaR, risk parity); (ii) an expanding-window walk-forward evaluation procedure that mimics real-world rebalancing; and (iii) a maximin hy- perparameter optimization strategy. Together, these elements form a robust pipeline for training neural networks directly on portfolio-level objectives. We evaluate seven neural architectures with two custom loss functions on a CRSP dataset of 50 S&P 500 constituents spanning 2007 to 2023. An expanding-window walk-forward valida …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
