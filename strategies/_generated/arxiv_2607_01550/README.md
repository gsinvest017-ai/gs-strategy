# Is Trend Still Your Friend?: A Microstructural Account of the Demise of Short-Term Trend-Following

Auto-generated bundle from `arxiv:2607.01550`.

Template: **momentum**

Matched keywords: `trend-following, trend following, cta`

Paper URL: http://arxiv.org/abs/2607.01550v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **momentum** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.01550",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.01550")`.

### Auto-retrieved passages

- **p.8** (BM25 -27.728):
  > ely parallels the change in PnL of short trends reported above, and motivates our initial working hypothesis. Indeed, Corr(∆π CTA, Ibook) was negative before 2010 and positive after. In other words, the order book was thicker on the opposite side of the trend trade before 2010, meaning that liquidity was provided to trend followers during that period. Since then, liquidity has been more abundant for trades opposing the trend, which may indicate that either liquidity providers shy away from trading with trend followers, or that trend followers themselves use more limit orders to execute – or both. The correlation with trade imbalance, Corr(∆π CTA, Itrade), on the other hand, does not show any …

- **p.1** (BM25 -27.7):
  > Is Trend Still Your Friend? A Microstructural Account of the Demise of Short-Term Trend-Following Jutta G. Kurth 1, 2, Zoltan Eisler 3, Adam Rej 4, and Jean-Philippe Bouchaud 4,1,5 1Econophysics Lab, Institut Louis Bachelier, 28 Place de la Bourse, 75002 Paris, France 2LadHyX UMR CNRS 7646, ´Ecole polytechnique, 91128 Palaiseau Cedex, France 3Imperial College London, Department of Mathematics 4Capital Fund Management, 23 Rue de l’Universit´ e, 75007 Paris, France 5Acad´ emie des Sciences, 23 Quai de Conti, 75006 Paris, France July 3, 2026 Abstract Systematic trend following has, on average, been profitable for at least two centuries; yet since approximately 2009, short-term trends have cease …

- **p.20** (BM25 -26.548):
  > Strategies, 3(3):41–61, 2014. doi: 10.21314/JOIS.2014.043. A. Levine and L. H. Pedersen. Which trend is your friend?Financial Analysts Journal, 72(3): 51–66, 2016. J. C. Lorenzen, S. M. Kessler, M. Hornbach, A. tentes, K. Qian, and M. Liu. Understanding cta positioning and forecasting cta flows.Morgan Stanley Research, 2025. A. J. Menkveld. High frequency trading and the new market makers.Journal of financial Markets, 16(4):712–740, 2013. M. Mitchell and T. Pulvino. Arbitrage crashes and the speed of capital.Journal of Financial Economics, 104(3):469–490, 2012. T. J. Moskowitz, Y. H. Ooi, and L. H. Pedersen. Time series momentum.Journal of financial economics, 104(2):228–250, 2012. F. Patzel …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
