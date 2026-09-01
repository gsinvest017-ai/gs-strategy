# Realtime price impact detection

Auto-generated bundle from `arxiv:2606.13419`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.13419v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.13419",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.13419")`.

### Auto-retrieved passages

- **p.5** (BM25 -4.193):
  > e of day, or a common signal many par- ticipants act on is handled. The locally estimated ˆλrides the busy or quiet period, so a fast print ar- riving merely because the market is active is cor- rectlynotsurprising. Self-excitation triggered by the fill itself– our fill is a print, and in a responsive market a print begets more prints. This - by our definition in Sec- tion 3 - is impact. Flagging it is a true detection, not a false alarm. 5

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
