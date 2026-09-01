# Train Often, Deploy Selectively: Forward-Gated Model Replacement in Crypto Markets

Auto-generated bundle from `arxiv:2607.28577`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.28577v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.28577",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.28577")`.

### Auto-retrieved passages

- **p.8** (BM25 -3.306):
  > riments. InAdvances in Neural Information Processing Systems, Vol. 33. Curran Associates, Inc., Virtual Event, 1106–1116. https://proceedings.neurips. cc/paper/2020/hash/0c72cb7ee1512f800abe27823a792d03-Abstract.html [10] Štěpán Davidovič and Betsy Beyer. 2018. Canary Analysis Service: Automated Ca- narying Quickens Development, Improves Production Safety, and Helps Prevent Outages.ACM Queue16, 1 (2018), 35–57. doi:10.1145/3194653.3194655 [11] A. Philip Dawid. 1984. Present Position and Potential Developments: Some Personal Views: Statistical Theory: The Prequential Approach.Journal of the Royal Statistical Society: Series A (General)147, 2 (1984), 278–290. doi:10.2307/ 2981683 [12] Francis  …

- **p.2** (BM25 -3.025):
  > e. At the scheduled bound- ary, the incumbent first processes every label whose availability time has passed. The challenger is then cloned and fitted using only examples mature at that boundary. Predictions from both branches are recorded during the following trial, but neither branch can use a trial label before its 300-second delay expires. The gate is evalu- ated only after all eligible trial labels have matured. This ordering prevents training-window overlap from leaking future labels into the release decision. The two branches see the same examples in the same order, yet their mutable states remain separate. Each branch carries its own normalizer and delayed queue; head updates on one  …

- **p.6** (BM25 -2.843):
  > s; policy-level evidence comes from the complete recursive replays. 0.00 0.08 0.16 Relative NLL reduction (%) 48-week time 20-asset breadth Supervised objective Calendar Blind Maint. Figure 4: Breadth evidence. Primary time breadth, earlier 20-asset breadth, and topology-matched objective transfer with pointwise 95% four-week block intervals. gains establish forecast value. Converting them into executable profit is a separate strategy-level estimand requiring prespecified trading costs, fills, and market impact. 5 Inference and Interpretation 5.1 What the block intervals quantify The inferential sample is 48 aggregate UTC weeks; the millions of forecasts determine service-scale impact but ar …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
