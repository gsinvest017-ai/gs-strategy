# A Taxonomy of Event-Linked Perpetual Futures: Variant Designs Beyond the Single-Market Binary Case

Auto-generated bundle from `arxiv:2605.10428`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.10428v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.10428",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.10428")`.

### Auto-retrieved passages

- **p.7** (BM25 -12.233):
  > Definition 3), the jump-aware tiered margin (Definition 4), the leverage compression scheduleLmax(t) (Definition 5), the resolution-aware funding rule (Definition 6), the resolution-zone protocol (Definition 7), and the eligibility framework. Paper 1’s CC-008 empirical evaluation establishes a scope distinction between two of these components that is consequential for variant inheritance: Definition 4 (jump-aware tiered margin) addresses terminal-jump bad-debt risk by sizing maintenance margin against the bounded-event terminal-collapse magnitude, whileDefinition 7 (resolution-zone protocol) addresses execution-channel risk by halting trading before the terminal collapse occurs. The two risk …

- **p.35** (BM25 -11.138):
  > (sized to cover terminal jumps) do not apply. Margin requirements for the funding-only contract should be sized to cover funding-rate volatility plus inventory-holding-period cost. This is similar to interest-rate-derivative margin sizing rather than event-contract margin sizing. Open interest dynamics.Without a settlement event, positions can accumulate indefinitely. Position limits and open-interest caps should be venue-side decisions; without them, open interest can grow without natural ceiling, with potential implications for funding-rate stability. 11.4 Microstructure No primary market for the underlying.The funding-only contract’s underlying (Ifund) is not directly traded; it is comput …

- **p.34** (BM25 -7.68):
  > • Roll-mechanism choice unresolved.Cliff, linear-weight, or volume-weighted transi- tions each produce valid variants with different microstructure. The choice is venue-side; this paper does not commit to one. • Constituent-list specification.The variant is well-defined only for events with regular schedules. Irregular events cannot be rolled cleanly. • Roll-basis handling unresolved.Re-anchor, maintain-notional, or cash-settle ap- proaches each have rationale; the choice has implications for trader experience and market-maker behavior. 11 Variant H: Funding-Only Event Derivative The funding-only event derivative (Variant H) departs from Paper 1’s framework structurally: there is no settleme …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
