# Portfolio Optimization for Commodity ETFs under Heavy-Tailed Returns

Auto-generated bundle from `arxiv:2606.26625`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.26625v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.26625",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.26625")`.

### Auto-retrieved passages

- **p.8** (BM25 -6.529):
  > long–short strategies. The optimized portfolios were compared with a passive buy-and-hold portfolio (BHP), initialized with equal weights across the 30 commodity ETFs and held without rebalancing. Letr t denote the vector of daily arithmetic ETF returns at timet, and letwt denote the portfolio weight vector selected before the return realization. Portfolio returns are computed as Rp,t =w⊤ t rt. The full-investment condition requires portfolio weights to sum to one at each rebalancing date. We considered two investment strategies: long-only and long–short. Under the long-only strategy, portfolio weights satisfy 30∑ i=1 wi(tk) = 1,0≤w i(tk)≤1, wherew i(tk)denotes the weight assigned to ETFiove …

- **p.27** (BM25 -4.521):
  > ium Shares ETF 01/08/2010 0.31 DBB Invesco DB Base Metals Fund 01/05/2007 0.36 GLTR abrdn Precious Metals Basket Shares ETF 10/27/2010 0.37 PPLT abrdn Physical Platinum Shares ETF 01/08/2010 0.97 GLDM SPDR Gold MiniShares Trust 06/25/2018 7.84 SLV iShares Silver Trust 04/21/2006 11.47 IAU iShares Gold Trust 01/21/2005 31.12 GLD SPDR Gold Shares 11/18/2004 58.40 Broad Commodity Index TAGS Teucrium Agricultural Fund (Fund of Funds) 03/28/2012 0.05 USCI United States Commodity Index Fund 08/10/2010 0.12 FTGC First Trust Global Tactical Commodity Strategy Fund 10/22/2013 0.21 CMDY iShares Bloomberg Roll Select Commodity Strategy ETF 06/19/2018 0.24 BCI abrdn Bloomberg All Commodity Strategy ETF  …

- **p.8** (BM25 -4.438):
  > tw s = 1/30limits the short position in any single ETF to approximately the initial equal-weight allocation of the 30-ETF universe. This specification allowed limited short exposure while preventing any individual short position from becoming large relative to the portfolio. Under both strategies, portfolio rebalancing was governed by the turnover constraint 1 2 30∑ i=1 |wi(tk)−wi(tk−1)|<CTO. The valueC TO = 1/(30×252)was imposed to keep rebalancing tightly controlled and to prevent the optimized portfolios from relying on excessive trading. This restriction is im- portant because commodity ETFs can differ substantially in liquidity, bid–ask spreads, and implementation costs. Transaction cos …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
