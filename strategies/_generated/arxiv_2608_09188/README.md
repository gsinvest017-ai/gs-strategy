# When Cross-Venue Agreement Is Not Price Discovery: Disclosure Frontiers for 24/7 Equity-Perpetual Oracles

Auto-generated bundle from `arxiv:2608.09188`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.09188v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.09188",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.09188")`.

### Auto-retrieved passages

- **p.13** (BM25 -3.485):
  > Oracle Disclosure Frontiers 13 event study, and an oracle-incident echo illustration—all seeded and produced byfigures/make_experiments.py. The theorems yield four observable implications that organize the empirics: row falsification through∆ v (Theorem 4, Corollary 1); limited discrimination, since a disclosed-weight row and a pure-externalw= 0baseline fit comparably under the path law (Theorem 2); a bounded live-external share, as deep-closed marks track index futures but not a crypto placebo; and reopen anchoring (The- orem 5). Each subsection below reports one, all from frozen public data. 6.1 Data Definition 1 (Anchoring type and provenance coding).Rowvisexter- nally anchoredifW v· = 0a …

- **p.13** (BM25 -3.355):
  > erivative marks and timestamped before the mark update, and Wotherwise, with provenance-ambiguous inputs (tokenized spot, validator ora- cle, external perpetual) carried under both codings. We collect frozen public five-minute candles: venue mark and index series from Binance, Bitget, Gate, and OKX; cash and extended-hours equity bars from Yahoo; and ES, NQ, and BTC futures for the comovement placebo. The sample spans April–June 2026 for four underlyings (AAPL, NVDA, TSLA, AMZN), with each endpoint snapshot frozen so an offline replay reproduces every metric under a fixed CSV SHA-256 hash. Disclosed OKX component rows are captured on two dated snapshots, and provenance-sensitive inputs are c …

- **p.3** (BM25 -3.02):
  > Oracle Disclosure Frontiers 3 public endpoint, two codings are carried throughout: the as-parsed peer coding (derivative weight0.571) and the conservative Hyperliquid-as-external coding (0.228). Cash-flow boundaries are kept separate from topology via˜zt =T tzt +c t, withT t for split, currency, and numeraire andct for dividends and corporate actions; where these are not fixed by the rule the residual is a boundary effect, not evidence aboutW, so the empirics restrict to windows where they are flat or documented. The stakes are not cosmetic: the closed-window mark sets margin, funding, and liquidation, so for hours at a time it is the operative price for every leveraged position. If the mark …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
