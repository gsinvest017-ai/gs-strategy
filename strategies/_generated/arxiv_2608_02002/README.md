# Hawkes-Driven OTC Market Making: Volterra-Riccati Approximation

Auto-generated bundle from `arxiv:2608.02002`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.02002v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.02002",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.02002")`.

### Auto-retrieved passages

- **p.14** (BM25 -2.962):
  > Table 2: Key numerical parameters for the three validation regimes. The common-mode cases use symmetric side intensities, while the directional case excites only one side of the RFQ flow. Parameter Description Benign Near-critical Directional q0 Initial inventory 10 10 0 X0 Hawkes memory 120 120 120 µb Bid RFQ intensity 10 1.5 5 µa Ask RFQ intensity 10 1.5 20 βHawkes decay 8 10 10 αHawkes excitation 5.2 9.2 9.2 ηBranching ratio 0.65 0.92 0.92 approximations are likewise obtained from finite-dimensional backward Riccati systems with bounded deterministic coefficients. The focus of the paper is therefore not a general convergence theorem, but a controlled numerical validation of the approximat …

- **p.15** (BM25 -2.916):
  > gret (with respect to the exact objective) is also reported. Table 2 reports the key parameters used in the three validation regimes. In the numerical benchmarks, one day is the unit of the chosen model clock; RFQ intensities and the volatility-derived penalty are expressed per unit of that same clock. Trade size and inventory units correspond to one million notional and price increments are in basis points. In addition, the period T = 1 day was used for all scenarios with timestep ∆ t = 10 −4. Calculations were performed on an integer inventory grid with qmax = 50 million and a 1000-point memory grid with Xmax = 800. The quote offset grid was δ∈ [−5, 20] bp with 5000 points and shadow price …

- **p.15** (BM25 -2.894):
  > Exact lifted HJB 46.20±0.10 0.000±0.000 0.000 Directional Poisson HJB 33.58±0.08 12.617±0.119 27.312 Directional Mean VR 45.04±0.10 1.154±0.054 2.498 Directional Noise-aware VR 45.20±0.10 0.997±0.049 2.159 Directional State-feedback VR 46.12±0.10 0.079±0.020 0.170 controls under the true Hawkes dynamics. All policies are evaluated under the same simulated Hawkes environments. Common random numbers are used across policies, so accuracy is reported through paired regret, i.e. the difference between the exact lifted HJB objective and the approximate policy objective, where both objectives are evaluated pathwise on the same simulated RFQ and fill randomness and then averaged. This removes most o …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
