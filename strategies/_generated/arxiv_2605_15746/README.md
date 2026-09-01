# The Privacy Subsidy: Kyle's $λ$ under Noise-Perturbed Order-Flow Observation

Auto-generated bundle from `arxiv:2605.15746`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.15746v5

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.15746",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.15746")`.

### Auto-retrieved passages

- **p.15** (BM25 -4.296):
  > signers is that fee schedules and privacy parameters cannot be chosen independently. References 1. Aase, K.K., Øksendal, B.: Strategic insider trading equilibrium with a non-fiduciary market maker. arXiv preprint arXiv:1908.08777 (2019) 2. Bender, C., Kraut, J.: Renegade whitepaper, protocol specification v0.6. https: //whitepaper.renegade.fi/(2024), accessed 2026-05-15

- **p.4** (BM25 -3.633):
  > =y+ε. The MM is acommitted Bayesian AMM: a smart-contract pricing rule that mechanically computes p(˜y) =E[v|˜y] without imposing zero expected profit on its own position. In contrast to Kyle’s competitive risk-neutral MM, the committed Bayesian AMM is not free to choose its pricing rule strategically; the rule is fixed by the mechanism, and any expected loss is absorbed by the protocol’s LP pool. We motivate this departure from Kyle’s competitive MM in Section 3.4.

- **p.1** (BM25 -2.996):
  > esigns all alter what the liquidity-providing role — whether an LP pool, an arbitrageur, or a smart-contract pricing rule — observes about order flow. Classical microstructure theory [ 11] gives the equilibrium price-impact coeffi- cient λ and informed-trader strategy β in closed form when the market maker observes the full aggregate flow y = x + u. None of these classical results extend, however, to the case where the market maker observes only a noise-perturbed signal ˜y=y+ε, as arises naturally in privacy-aggregated exchange designs. Contributions.This paper provides three results, each of which is absent in or distinct from textbook Kyle. arXiv:2605.15746v3 [cs.GT] 26 May 2026

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
