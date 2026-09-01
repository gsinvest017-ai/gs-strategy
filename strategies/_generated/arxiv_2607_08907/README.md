# Herding and Liquidity in Order-Book Markets. I. A Robust Liquidity-Stress Crossover and its Reflexive Mechanism

Auto-generated bundle from `arxiv:2607.08907`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.08907v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.08907",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.08907")`.

### Auto-retrieved passages

- **p.22** (BM25 -15.009):
  > decorrelated signal. An external open-loop signal cannot instantiate a market’s internal loop, so no directional contagion crosses. This is predicted by, and consistent with, the reflexive reading rather than an independent finding. 6.4 Limitations •Momentum’s reflexive component is robust; OFI’s is not. Momentum’s positive, self-reinforcing component reproduces against every comparator (shadow, replay, synthetic telegraph) and stays positive (≈+0.19) at a second amplitude on independent reproduction. OFI’s com- 22

- **p.11** (BM25 -14.736):
  > re 3: Rule-robustness under the OFI herding signal.Left:REALϕ ∅ rises to 0.227 in the high- φ/high-κcorner, the same diagonal region found under price momentum.Right:the scrambled-sign null is identically zero across the whole plane–the dry-up requires directionally correlated OFI- driven herding, exactly as under momentum. Axes as in Fig. 1. 11

- **p.15** (BM25 -14.66):
  > Table 6: Corner (0.9,1.0)ϕ ∅ under theamplitude-matchedshadow / replay decomposition (mean±SEM,≥6 seeds/condition; shadow uses≥3 independent driving series). Momentum’s dry-up isfar above bothits open-loop shadow and its replay (strong, comparator-robust self- reinforcement). OFI’s real value (0.195) sitsbelowthe baseline-flow shadow (0.418) butabove the loop-isolating replay (0.164), so its reflexive component flips sign with the comparator–it has no robust sign (see text). condition price-momentum (scale 2.0) OFI (scale 68.8, matched) real(closed loop) 0.338±0.003 0.195±0.003 shadow(open-loop, matched amplitude) 0.047±0.004 0.418±0.045 replay(closed-loop signal, open loop) 0.132±0.004 0.16 …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
