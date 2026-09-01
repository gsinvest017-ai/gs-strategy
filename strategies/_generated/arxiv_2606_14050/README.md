# Battery Bidding under Price Uncertainty in Wholesale Electricity Markets

Auto-generated bundle from `arxiv:2606.14050`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.14050v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.14050",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.14050")`.

### Auto-retrieved passages

- **p.21** (BM25 -4.127):
  > Table 2:λopp⋆ t by uncertainty levelκand starting SoCs16 in simulation 1. κ\s16 8 16 24 32 1 68.37 58.83 51.00 43.32 1.25 76.38 63.32 51.69 40.88 1.5 84.77 67.64 52.62 38.26 (4pm–10pm), varying the starting SoC{0,4,12,16,24}at the beginning of the charging window. Across all panels in Figure 3, the battery is effectively driven toward a common full inventory position before the discharge window begins, and then empties before the discharge window ends. When the battery starts the day with little energy, it is willing to buy at substantially higher midday prices in order to rebuild inventory before the evening peak. When it starts with more energy, its buy bid prices fall sharply and can even …

- **p.3** (BM25 -3.199):
  > enue against downside risk. A natural formulation of this problem is a mixed-integer linear program (MILP), because market clearing depends on whether realized prices cross submitted bid prices. We show that, for the sampled-scenario model, these integer decisions can be removed exactly. The key observation is that with finitely many sampled prices, only the relative position of each bid price among those sampled prices matters for clearing. Therefore, bid prices can be restricted to the sampled price set without loss of optimality, and the resulting clearing patterns can be precomputed and embedded as fixed coefficients. This yields an exact linear programming (LP) reformulation. Operationa …

- **p.21** (BM25 -3.138):
  > ch more stable across the panels because the battery enters the discharge block all from n full SoC position in each case. Uncertainty reinforces this mechanism, but again depends on the starting SoC. When the battery begins the day with low SoC, i.e.,{0,4}, a higherκ raises the value of securing inventory for the evening peak, so the battery is willing to charge even at less favorable midday prices. Under these initializations, uncertainty increases the(EMOV-charge), because future high-price discharge opportunities are valuable and inventory is scarce. By contrast, when the battery starts with a high SoC, i.e.,{12,16,24} , this scarcity largely disappears. Additional charging then becomes  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
