# Valuing American options and Flexible Forwards contracts in time-dependent models

Auto-generated bundle from `arxiv:2606.27335`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.27335v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.27335",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.27335")`.

### Auto-retrieved passages

- **p.5** (BM25 -6.036):
  > ed as follows. Section 2 details the model specification, including the formal definition of the FF contract in Section 2.1 and the computation of the joint CF for time- inhomogeneous coefficients in Section 2.2. Section 3 presents the Integral Equation approach for pricing American options, covering the computation of the joint transition density in Section 3.1 and the exercise boundary in Section 3.3. Section 6 describes a benchmark solution using modern finite-difference methods. Section 7 provides a numerical comparison between the semi-analytical solution via our IE approach and the PDE benchmark. Section 8 offers concluding remarks. 2 Model specification Consider the Heston stochastic  …

- **p.35** (BM25 -4.557):
  > run same test but withv = 0.05(panel ’a’) andρ= 0.8(panel ’b’). It can be seen that the impact is small while not negligible. Test 4. In this test, we restore time-inhomogeneity by reverting to the parameters listed in Table 1. The computed ES is relatively close to that from the previous test; therefore, rather than showing absolute values, we present the absolute difference between the results obtained here and those from the constant-parameters test. Accordingly, Fig. 4(a) displays the difference in the two ES, while Fig. 4(b) shows∆S∗(ti,v )for multiple time pointsti derived from this experiment. The American Put option price is 13.57417, which consists of the European Put price 13.5647  …

- **p.39** (BM25 -4.493):
  > rt FF contract under the time-homogeneous Heston model with S = 80,K = 80,v 0 = 0.5with model parameters from Table 1, butv0 = 0.05; a) the entire ES, b) projections of the ES for various time pointsti. Fig. 5(a) presents thus computed EB for the short FF contract with payoffK−Sand constant parameters as in the first test for American options. Here,t∈[T1,T−]. Again,S∗(ti,v )for multiple time points ti are highly nonlinear as it can be seen in Fig. 5(b). To notice, in this testfsolveMatlab solver is more efficient thanlsqnonlinto find a reasonable solution. The short FF price is -0.0966, which consists of the European price -0.0993 plus the EEP of 0.00269. The premium due to an American featu …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
