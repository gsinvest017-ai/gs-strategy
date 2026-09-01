# Overshooting the Coordinate: Where Factor Corrections Land on Characteristic Axes

Auto-generated bundle from `arxiv:2607.05091`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.05091v6

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.05091",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.05091")`.

### Auto-retrieved passages

- **p.8** (BM25 -3.456):
  > rt portfolio with linear rank weights 1 2 −u: it is long the high-characteristic side and short the low-characteristic side, with intensity increasing toward the endpoints. Changing the traversal measure changes these portfolio weights but not the logic of the construction. 3.3 Restricted characteristic-axis pricing For a fixed characteristic universe, order, and admissible measure, define Vx = span n eRA,x, Dx(p) :p∈[0,1] o .(14) Assumption 1(Regularity).All test returns and factor returns have finite second moments, andVar(f m)is nonsingular. Definition 1(Admissible measure).A formation-date measure isadmissibleif its initial weights use only information available atτ(t), place strictly po …

- **p.5** (BM25 -3.233):
  > tinuation, and investment and profitability enter later models (Fama and French, 1992, 1993; Jegadeesh and Titman, 1993; Carhart, 1997; Titman et al., 2004; Novy-Marx, 2013; Fama and French, 2015; Hou et al., 2015). I take no position on whether characteristics proxy for priced covariances or directly describe expected returns (Daniel and Titman, 1997). Instead, I treat value, operating profitability, investment, and momentum as established economic coordinates and study how model alphas vary along their full orders (Fama and French, 2008; Hou et al., 2021). The contribution is not to rediscover their average-return spreads, but to locate where factor correction leaves the returns those orde …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
