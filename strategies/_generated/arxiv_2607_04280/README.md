# Order Splitting and Liquidity Replenishment Are Jointly Necessary for the Square-Root Law of Market Impact:

Auto-generated bundle from `arxiv:2607.04280`.

Template: **momentum**

Matched keywords: `momentum`

Paper URL: http://arxiv.org/abs/2607.04280v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.04280",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.04280")`.

### Auto-retrieved passages

- **p.9** (BM25 -8.945):
  > (δ→ 0.386) but a weaker effect: the book still receives some resting liquidity from retail limit orders, but without active replenishment the depth is thinner and impact is larger. By contrast, perturbations that leave splitting and HFT intact barely moveδ. Price limits, momentum trading, reduced background liquidity, uni- form splitting, and front-loaded splitting all yieldδ∈[0.49,0.53]— within 9

- **p.17** (BM25 -6.836):
  > hat only the removal of order splitting (δ→0.324) or of liquidity replenishment by market makers (δ→0.386) breaks the SRL, while perturbations leaving both intact moveδ by less than10%. Order splitting and liquidity replenishment are thus jointly necessary for the SRL within this model; the splitting rule, momentum trad- ing, price limits, and background liquidity level are dispensable. Second, a per-stock comparison of three theoretical predictions (GGPS, FGLW, LOB walking) against simulatedδrejects all three on identical data: distribution- based theories over-predict, visible-book-based theories under-predict. The failure of all three single-mechanism predictions, together with the ablati …

- **p.12** (BM25 -6.706):
  > tionately more depth per unit of additional size, and the resulting impact curve is concave withδ <1/2. The precise valueδ= 0.324reflects the specific shape of the resting book at the moment of arrival — it is not a universal constant but a consequence of the model’s LOB geometry. LiquidityreplenishmentbyHFTagentsisthesecondnecessaryingredient. When HFT is removed, the book still receives resting orders from retail limit submissions, but the active two-sided quoting that refills depleted levels after each fill is gone. The LOB thins during execution, so each subsequent child order moves the price further than it would in a replenished book, producing a steeper impact curve (δ= 0.386). Changi …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
