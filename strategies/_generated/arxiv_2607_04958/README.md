# Look-Ahead-Freedom as Temporal Non-Interference: A Verifiable Correctness Property for Backtesting and Agentic Trading Pipelines

Auto-generated bundle from `arxiv:2607.04958`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.04958v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.04958",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.04958")`.

### Auto-retrieved passages

- **p.20** (BM25 -8.606):
  > unbounded length. Because every operator is causal and pointwise (Section 5.2)— scan depends only on positions ⪯𝑝 , window on a bounded suffix, and we use no unbounded-lookback resample—each element ¯𝑒[𝑝] is finitely determined even when the series is infinite. No evaluation ever forces a completed infinite series; the infinity resides solely in the epoch quantifier of Definition 8. Proof. Let 𝑀 be a Turing machine (run on blank input; the general case is identical). We construct a term𝑒 𝑀 ∈ Uwith 𝑀halts⇐ ⇒𝑒 𝑀 isnotlook-ahead-free, which reduces the halting problem to non-look-ahead-freedom and hence establishes undecidability. Simulating 𝑀 with a causal fold.Identify the position domain wit …

- **p.15** (BM25 -8.494):
  > aggregated into it—for example, the minutes composing daily bar𝑝: {𝐼⊢ ¯𝑒[𝑞] ⇓ ⟨𝑣 𝑞, 𝛼𝑞⟩ }𝑞∈𝜌 ← (𝑝) 𝐼⊢resample 𝜌 (¯𝑒) [𝑝] ⇓ agg( [𝑣𝑞]),max 𝑞∈𝜌 ← (𝑝) 𝛼𝑞 (E-Resample) The rule 𝜌 iscausalif max𝜌 ← (𝑝) ⪯𝜄(𝑝) , where 𝜄(𝑝) is the source position identified with output 𝑝’s emission point; that is, an output bar aggregates only source positions at or before its own close. Up-sampling requires the dual (each output maps to a unique source position ⪯ it). A non-causal 𝜌 is the classic resample leak, which the checker rejects (clause (4) of Definition 4). ACM Trans. Softw. Eng. Methodol., Vol. 0, No. 0, Article 0. Publication date: July 2026.

- **p.20** (BM25 -8.223):
  > 0:20 Xavier Fonseca (M1) Value-conditioned availability. U admits, as the availability argument of a stamping con- struct, a pipeline term of sort Time computed from data values—in particular a total condi- tional such asif val(𝑒)>𝑐then𝜏 1 else𝜏 2. This is exactly the extension definingU (Definition 2), whose own illustrative instance is a value-conditionedTimeterm. (M2) Configurations as values.A value ( Val) may hold a finite string, so a Turing-machine configuration—control state, head position, and finite tape—is a Val, and one step of the machine is a total, pure function Val→Val , consistent with Assumption 1. The step function is total; we never ask a value operation to decide halting …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
