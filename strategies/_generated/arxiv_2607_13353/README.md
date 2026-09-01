# Is Deep Hedging Reinforcement Learning?

Auto-generated bundle from `arxiv:2607.13353`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.13353v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.13353",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.13353")`.

### Auto-retrieved passages

- **p.2** (BM25 -3.943):
  > e of deep hedging: it is a Monte Carlo, actor-only, pathwise-gradient method, and not a temporal-difference or value-based one. Where the present note departs is in the inference drawn from that feature, namely that it places deep hedging outside reinforcement learning. Section 2 revisits the definition of RL given by Sutton and Barto (2018), whose textbook is widely regarded as a standard reference in the field. This foundation is used in Section 3 to directly address the two arguments described above and explain why deep hedging is best understood as falling under the RL umbrella. 1

- **p.3** (BM25 -3.335):
  > 2 Reinforcement Learning According to Sutton and Barto (2018) Sutton and Barto (2018) frame reinforcement learning as a way for an agent to learn, through interacting with an environment, which actions to take in order to maximize a cumulative reward signal – discovering good behavior through trial and error rather than being told the correct action. They frame the underlying problem as a Markov decision process (MDP) – an agent interacting with an environment through states, actions, and rewards over time – and identify exploration versus exploitation as a tension intrinsic to the problem, since the agent must balance acting on what it already believes to be good against trying alternatives …

- **p.3** (BM25 -3.308):
  > of which is part of the definition of RL itself. The first axis is value-based versus policy-based: some methods learn an explicit value function and derive a policy from it, others learn a policy directly with no value function at all. The second axis isMonte Carlo versus temporal-difference: some methods update only once an entire episode has been simulated to completion, using the single realized return for that episode, while others bootstrap from an intermediate value estimate at every step. Sutton and Barto (2018) present Monte Carlo control – simulating a full episode and updating from its terminal return alone – as a foundational RL method in its own right, prior to introducing TD le …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
