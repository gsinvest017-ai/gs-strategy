# Resolution-Aware Perpetual Futures on Binary Prediction Markets: An Empirical Risk-Design Framework Using Polymarket Data

Auto-generated bundle from `arxiv:2605.10400`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2605.10400v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2605.10400",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2605.10400")`.

### Auto-retrieved passages

- **p.66** (BM25 -10.218):
  > argin M init t Initial margin requirement at timet.Total margin required to open a position of given notional. Decomposed into a continuous-volatility component and a jump-aware tiered component. (Definition 4) M maint t Maintenance margin requirement at timet.The margin level below which a position is liquidated. Set as a fractionβ <1ofMinit t . Lmax(t) Maximum allowed leverage at timet.Time-dependent under the leverage compression schedule:L max(t)((T−t))→1as(T−t)→0. (Definition 5) Ft Funding rate at timet.Periodic payment between long and short positions. Standard basis-only: Ft =c·(qt−It). Boundary-corrected variant adds a regime-dependent term nearI t→0andIt→1. (Definition 6) Λt Liquida …

- **p.24** (BM25 -9.751):
  > politics markets a0.68×ratio (genuine decline). The crypto result — a24-fold concentration of final-day activity — reflects the market structure of cryptocurrency-related event markets, where outcomes are determined by reference-asset price levels at specific times and where leverage-seeking late-stage speculation is intense. The politics result — a slight decline — reflects predictable resolution timing on calendar-bound political events: traders position before the final day because the resolution mechanism is well-known. The class-level dispersion has substantial implications for the resolution-zone protocol design: a single protocol calibrated to pooled behavior would compress leverage t …

- **p.26** (BM25 -9.344):
  > tatic-margin shortfall under terminal collapse).Under Assumption 1 and Assumption 2, consider a long position of sizex> 0taken at time t<τat leverageL under the naive crypto-perp portE0 (Definition 1). LetΠτdenote the realized loss to the position over the interval[t,τ]in the eventR = 0(the long loses). Then there exist parameter configurations ofE0 — specifically, any configuration withL >1and mσchosen such thatM init t <|x|— under which Πτ>M init t wheneverp t[τ−]−R>L−1. That is, the realized loss exceeds initial margin whenever the terminal jump is large enough to deplete the leverage buffer. The shortfallΠτ−Minit t is unbounded inL for fixedpt[τ−], in the sense that doubling the leverage …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
