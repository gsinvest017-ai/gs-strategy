# The Triadic Stress Index in Financial Markets

Auto-generated bundle from `arxiv:2608.10788`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.10788v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.10788",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.10788")`.

### Auto-retrieved passages

- **p.16** (BM25 -4.086):
  > t series (5 years, 2–3 labelled episodes), the definition of the ground- truth event list dominates the calibration result far more than the choice of hyperparameters. The 26-year, 20+-episode OFR series has enough independent events to support reliable out-of- sample calibration; 5-year, 2–3-episode series do not. 6.12. Persistent Homology The correlation-network H1 construction showed no discriminative pattern (mean 0.03–0.07 across all scenarios; calm and crisis periods indistinguishable). We attribute this to insufficient topological richness in an 8–11-node graph. 16

- **p.4** (BM25 -3.701):
  > well. To keep the financial instrument distinct from both, we write TSI throughout this paper, in prose and in equations, and reserve the other names for what they denote:FSRIfor the theoretical framework,Omega-Sfor the machine-learning line, andTSIfor the index defined here. Relation to the composition fixed in the framework paper.Equation (1) places Coex in the numerator, whereas Definition 1 of the framework paper [1] places it in the denominator, so that a high degree variance lowers the index there and raises it here. The two agree on the other three factors, including the orientation ofMas an inverse spectral gap. We keep the composition above, and we give the reason rather than leavin …

- **p.16** (BM25 -3.485):
  > TSI rose, consistent with geopolitical shocks propagating through price co-movement over weeks rather than instanta- neously. These are not detection errors butscope boundaries: TSI detects correlation-structure breaks (episodes where normally semi-independent assets suddenly co-move), not directional price events. This yields a precise, falsifiable scope claim. 6.11. Attempted Replication on Shorter Series We attempted to repeat the calibration on the bank network (train: Bear Stearns + Lehman 2008; test: European debt crisis 2011) and the AI network. Both failed to reproduce the OFR result, and not because the filter stopped working, but because the highest TSI with memory readings in the  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
