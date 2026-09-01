# Quantifying Sub-Optimality in Routing for Automated Market Makers

Auto-generated bundle from `arxiv:2607.20762`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.20762v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.20762",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.20762")`.

### Auto-retrieved passages

- **p.11** (BM25 -3.137):
  > Quantifying Sub-Optimality in Routing for Automated Market Makers 11 much of the aggregate dollar gap reported above. Potential mechanisms include adversarial execution (e.g., sandwiching) or transient liquidity shocks, both of which can depress realized output relative to benchmark routes. 5.2 Impact of Information Staleness We measure the value of timely pool information via a controlled staleness design. ForN∈ {0,1, . . . ,10}, letω N ={ω N j }j∈J be the state usedbothto compute the benchmark and to evaluate outcomes: (i)N= 0 (oracle):ω 0 is the transaction’s execution-time state (the state at the trade’s actual execution position within its block). (ii)N≥1 (implementable):ω N is the bott …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
