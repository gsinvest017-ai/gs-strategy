# FinanceHarness: Autonomous Financial Deep Research Framework

Auto-generated bundle from `arxiv:2607.27853`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.27853v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.27853",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.27853")`.

### Auto-retrieved passages

- **p.41** (BM25 -4.189):
  > convexity is nearly exact.The second-order Taylor approximation reproduces the exact reprice within $0.0001 per $100 face for a±50 bp parallel shift, confirming that convexity of 37.0 is well-calibrated for this bond at this yield level. 4.DV01 interpretation.A 1 bp move in yield changes the clean price by approximately $0.0557 per $100 face. For a $10 million position, that is ~$5,570 per bp. 41

- **p.2** (BM25 -3.486):
  > constructFinanceGym, a large-scale, expert-validated financial deep research benchmark. We build an entity graph from the corpus and sample financial situations from this graph to ground each research question and its rubric. Drawing on input from financial practitioners, we generate an investment thesis and paired pre-cutoff and post-cutoff rubrics for every question. A multi-stage filtering pipeline then removes low-quality records, and expert annotators validate the rest to form the final benchmark. Building on this new environment, we proposeFinanceHarness, an expert-knowledge-guided agent harness for financial deep research (Section 4). Following the common definition in the community,F …

- **p.37** (BM25 -3.221):
  > FinanceHarness: Autonomous Financial Deep Research Framework •Using Full Peer Median Composite P/E (25.43x): Implied Stock Price=$19.84×25.43=$504.53per share Implied Market Cap / Equity Value=$504.53×12.20B shares=$6,155.27billion($6.16T) 2. Valuation Implied by Peer-Median EV / EBITDA (16.25x) •TTM EBITDA Baseline ($173.16 billion): Implied Enterprise Value=$173.16B×16.245=$2,812.98billion Plus Net Cash Position=+$121.68billion Implied Equity Value=$2,812.98B+$121.68B=$2,934.66billion($2.93T) Implied Stock Price= $2,934.66B 12.20B shares =$240.55per share •Forward Projected EBITDA Composite Baseline:When applying the 16.25x peer median to consensus forward EBITDA projections (~$368B implie …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
