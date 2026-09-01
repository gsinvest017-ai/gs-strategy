# DeXposure-Claw: An Agentic System for DeFi Risk Supervision

Auto-generated bundle from `arxiv:2606.19501`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.19501v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.19501",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.19501")`.

### Auto-retrieved passages

- **p.11** (BM25 -4.348):
  > nough pre-event history. The 2025 leaderboard runs use the 42-week monitor baseline in Appendix A. Ground-truth definition.With wt(v) =P e∋v wt(e) the total weight incident on v, the regulator-aligned stressed set at horizonhis ∆h t (v) =w t(v)−w t+h(v), S h t = topπ{v:w t(v)>0,∆ h t (v)>0}, (6) with π= 0.05 and ground-truth horizon h= 4 weeks. The final four test weeks lack the 4- week-ahead snapshot wt+4 and are not scored, leav- ing n= 29 evaluated weeks. This is the single ground-truth definition used by b2, b5, and the LLM-decision pipeline. A submission produces one JSON file per {benchmark, method} pair plus a single results.json; the harness fixes random seeds, snapshots library vers …

- **p.2** (BM25 -3.311):
  > of its interventions, and a stronger Opus 4.7 is no better (44%, false-intervention rate 0.437 even with the safety gate); over-intervention thus persists regardless of model, so safe high-severity action comes from the data-health and confidence gates and human review, not from the decision model. DeXposure-Claw is thus an auditable recall-and- explanation option for human-in-the-loop DeFi su- pervision, not a replacement for conservative rule- based systems. 2 Related Work Bench positioning and ground-truth definition. LLM-agent benchmarks (HELM (Liang et al., 2022), SWE-bench (Jimenez et al., 2024), Agent- Bench (Liu et al., 2024)) score open-ended reason- ing, software repair, and generi …

- **p.11** (BM25 -3.207):
  > umbers are kept out of the main text because the paper’s contribution is the operating point of the full pipeline, not the FM’s headline accuracy. B.3 Benchmark details Six-axis schema.The six axes are non- overlapping (a system can excel at b1 while failing b5), decomposable along the four-layer framework so that predictor (b1, b3, b6), monitor (b2), scenario ( b4), and decision ( b5) ablations report independently, and individually publishable so downstream work may extend a single axis without re-running the suite. Dataset split. Historical warning windows.The b2_warning event study is separate from the frozen 2025 leader- board split. It evaluates the shared weighted-degree monitor aroun …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
