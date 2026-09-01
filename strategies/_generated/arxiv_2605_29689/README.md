# Beyond TVL: An Explainable Risk Scoring Framework for Tokenized Real-World Assets

Auto-generated bundle from `arxiv:2605.29689`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.29689v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.29689",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.29689")`.

### Auto-retrieved passages

- **p.5** (BM25 -3.06):
  > Table 2: Raw RWA.xyz variables used in pilot metric construction Ticker Category Asset value Holders Active addr. Transfer vol. Transfer count BUIDL Treasury2,487,654,577 108 24 1,092,239,594 88 BENJI Treasury823,165,231 1,106 17 10,063,830 19 OUSG Treasury612,494,992 55 15 110,807,065 34 USTB Treasury721,054,020 99 21 285,750,617 709 USDC Stablecoins72,102,491,659 42,268,158 18,527,278 4,204,621,116,056 721,150,802 USDY Treasury2,143,889,939 14,495 4,325 566,702,395 158,269 HLSCOPE Private credit4,359,598 45 6 123,534 3 STAC Structured credit101,323,883 4 1 3,549,447 1 PAXG Gold4,215,207,035 83,949 11,385 3,765,680,650 263,339 XAUT Gold2,591,487,591 56,487 17,589 4,239,912,225 173,584 Table …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
