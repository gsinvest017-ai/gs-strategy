# Robust Control under Stationary Ambiguity

Auto-generated bundle from `arxiv:2608.04832`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.04832v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.04832",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.04832")`.

### Auto-retrieved passages

- **p.9** (BM25 -5.636):
  > cannot trade yet. Denote the normalized price process by ˜St := St S0 , t∈ {0, . . . , T}, where the division is componentwise. We consider a terminal payoffψ( ˜S1:T ) that depends on the path of the normalized price process ˜S, where ψ:R T×d →R is a payoff function. We assume that the policy can only trade in ˜S and not in any other assets or derivatives, so that Ut ∈R d represents the position held in ˜S over the time interval [t−1, t] . We parameterize controls with a neural network policy such that Ut =U θ t =f θ(Y−H+1:t−1), t= 1, . . . , T, where, as before, Y denotes the progressively observed information process and fθ is a causal sequence model with parameters θ. We implement fθ with …

- **p.2** (BM25 -5.226):
  > when we expect the parameters that best describe the real system to change over time. For example, many control problems in finance require simulating paths of asset prices or returns. The simulator parameters that describe current market conditions often drift or jump (Lamoureux and Lastrapes, 1990; Ang and Timmermann, 2012; Dangl and Halling, 2012), so beliefs about those parameters should not be expected to concentrate over time (Epstein and Schneider, 2007; Ju and Miao, 2012; Nagel and Xu, 2022). In such domains, the policy should thus maintain its robustness to the simulator parameters over time. To achieve this, we argue that ambiguity should be able to vary stochastically with the sta …

- **p.2** (BM25 -4.572):
  > vely observes but cannot affect. When the dynamics of Y are uncertain and the simulator parameters that best describe them are expected to change over time, stationary ambiguity is a natural modeling assumption. 2

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
