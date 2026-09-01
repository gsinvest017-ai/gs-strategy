# The Science and Practice of Trend-Following Systems

Auto-generated bundle from `arxiv:2607.19497`.

Template: **momentum**

Matched keywords: `momentum, time series momentum, trend-following`

Paper URL: http://arxiv.org/abs/2607.19497v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.19497",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.19497")`.

### Auto-retrieved passages

- **p.44** (BM25 -25.559):
  > omentum and risk adjustment. J. Altern. Invest. 18(2), 91–103 (2015) Faith, C.: Way of the Turtle: The Secret Methods that Turned Ordinary People into Legendary Traders. McGraw Hill Professional, New York (2007) Ferreira, F., Silva, A.S., Yen, J.-Y.: Detailed study of a moving average trading rule. Quant. Finance 18(9), 1599–1617 (2018) Goulding, C.L., Harvey, C.R., Mazzoleni, M.G.: Momentum turning points. J. Financ. Econ. 149(3), 378–406 (2023) Granger, C.W.J., Joyeux, R.: An introduction to long-memory time series models and fractional differencing. J. Time Series Anal. 1(1), 15–29 (1980) Grebenkov, D., Serror, J.: Following a trend with an exponential moving average: analytical results f …

- **p.7** (BM25 -25.003):
  > technical trading rules, Kaminski and Lo (2014) analyze the stop-loss exit leg, and Levine and Pedersen (2016) and Brock et al (1992) study moving-average crossover rules. We generalize this approach in Definition A.3 following the design of the turtle systems. The American system trades break-outs from ranges with binary position sizes, so the exposure is fully allocated when the signal is on and zero otherwise. 3. Time Series Momentum (TSMOM) TFsystem is based on the price momentum as in equation (A.15) or, more generally, on the momentum of the returns adjusted for volatility as in equation (A.16). This approach is commonly used in academic studies (see Moskowitz et al (2012), Hurst et al …

- **p.1** (BM25 -24.791):
  > The Science and Practice of Trend-Following Systems Artur Sepp ∗ Vladimir Lucic † This version: July 20, 2026 Abstract We present a unified approach to designing trend-following (TF) systems and classify them into European, American, and Time Series Momentum categories. For European TF systems, we derive an exact relationship between profit-and-loss, autocorrelation, and drift in volatility-normalized returns. We analyze the expected return under fractional ARFIMA processes and show that TF systems are profitable when the long-term autocorrelation is positive, even under short-term mean reversion. In the frequency domain, the expected return is represented as a Poisson-kernel reading of the  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
