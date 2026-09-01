# Open Information: A Defining Perspective on Web Datasets for Carbon Pricing

Auto-generated bundle from `arxiv:2608.04929`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.04929v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.04929",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.04929")`.

### Auto-retrieved passages

- **p.1** (BM25 -5.413):
  > restructuring. 4 GameStop is a retailer. of web datasets is available from third -party web platforms [4]. A significant body of literature exists to demonstrate their impact on market pricing, in the capacity of new datasets arising out of sources like social media, viral headlines, or influencer marketing. Consequently, we perceive web datasets as a new source of information . Termed as Open Information (OI), w e therefore propose a defining perspective in DEFINITION 1. Open Information is the information content of a web dataset that is widely available and is not a designated form of public information. DEFINITION 1: DEFINING PERSPECTIVE ON WEB DATASETS From the definition, any form of p …

- **p.4** (BM25 -4.557):
  > tm DEFINITION 2: SAMPLE ROW FROM GDELT The configuration of datasets for testing is summarised in TABLE 3, and a sample row from GDELT is exhibited in DEFINITION 2. The relevant time series obtained from GDELT corresponding to OI and PI are summarised in TABLE 4. The counts obtained as a result of the selection are exhibited in Fig 2 and Fig 3. Even though headlines categorised as GOV could produce both OI and PI , we have categorised them as PI citing difficulty in differentiating the sub-categories. Such a misclassification weakens OI . The weakening is acceptable on the grounds that a more acc urate classification would improve the strength of OI. Therefore, if our te sts are significant  …

- **p.7** (BM25 -3.447):
  > e refer to them as informative datasets. Such datasets are then provided as inputs to investment decisions, such as those modelled with TM. Perception Informative Datasets Judgement Decision Fig. 5. Informative datasets as input to investment decisions Fig. 5 extends the defini tion of TM to add informative datasets. Given that the literature on TM has modelled management decisions, such a definition allows addressing various aspects, such as cost estimates, analysing performance, estimating returns, and making data life-cycle choices. To stress on the costs involved, the characterisation of web datasets as OI implies that their integration is considered in terms of a cost of information , i …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
