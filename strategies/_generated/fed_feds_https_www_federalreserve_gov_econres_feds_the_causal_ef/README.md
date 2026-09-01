# FEDS Paper: The Causal Effect of Debt on Interest Rates

Auto-generated bundle from `fed_feds:https://www.federalreserve.gov/econres/feds/the-causal-effect-of-debt-on-interest-rates.htm`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: https://www.federalreserve.gov/econres/feds/the-causal-effect-of-debt-on-interest-rates.htm

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
