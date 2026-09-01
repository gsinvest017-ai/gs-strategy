# Generating Synthetic Stock Return Distributions with Diffusion Models

Auto-generated bundle from `repec:RePEc:cfi:fseres:cf627`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: https://econpapers.repec.org/RePEc:cfi:fseres:cf627?ref=nep-rmg

## RAG source context

Paper text NOT yet indexed. Run `quant-crawl fetch-pdfs` then
`quant-crawl rag-ingest` to enable formula retrieval via MCP.

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
