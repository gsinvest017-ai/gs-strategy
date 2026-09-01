# Herding, Momentum, and Reversal in China's A-Share Market: An Agent-Based Network Model with Information Diffusion

Auto-generated bundle from `arxiv:2607.27063`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.27063v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.27063",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.27063")`.

### Auto-retrieved passages

- **p.6** (BM25 -13.259):
  > e signal mean. As diffusion completes and beliefs become less heterogeneous, the price returns toward the signal-implied region. This experiment shows that momentum and reversal can arise from the information process alone; herding is an amplifier rather than a necessary condition. (a) Herding intensityγ=0.1 (b) Herding intensityγ=0.3 (c) Herding intensityγ=0.5 Figure 4: Cluster trading patterns under different herding intensities. 6

- **p.2** (BM25 -12.323):
  > Independently, a signal diffuses through the network and changes the beliefs of investors it reaches. Market clearing maps the resulting heterogeneous decisions into a price path. The paper makes three contributions. First, it embeds local interaction in a market-clearing model rather than imposing a representative herding coefficient at the aggregate level. Second, it separates delayed information diffu- sion from imitation, thereby clarifying why both rational underreaction and behavioral reinforcement can produce momentum. Third, it proposes a rolling distributional indicator based on transformed return tails and compares it with established CSAD and LSV measures in the Chinese market. Th …

- **p.1** (BM25 -11.081):
  > y of herding as complementary mechanisms behind momentum and reversal. Keywords:herding behavior, agent-based financial market, information diffusion, momentum, reversal, China A-share market JEL:G12, G14, D53, C63 1. Introduction Financial markets aggregate heterogeneous expectations into prices. In the benchmark efficient-market view, prices incorporate available information and past returns should not systematically predict future excess returns (Fama, 1970). In practice, however, limits to arbitrage and correlated non-fundamental demand can allow prices to depart from fundamental values (De Long et al., 1990). Momentum and reversal are two prominent manifestations of this departure: rece …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
