# The Quarter-Hour Effect: Periodic Algorithmic Trading and Return Predictability in Cryptocurrency Futures

Auto-generated bundle from `arxiv:2607.09426`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2607.09426v2

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2607.09426",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2607.09426")`.

### Auto-retrieved passages

- **p.14** (BM25 -4.422):
  > 61; see Gardner et al., 2006; Napolitano, 2016 for surveys), and the phase-resolved autocovariance we use is a standard object in that literature. The diagnostic tools there, however, operate in the frequency domain: Hurd and Gerr (1991) detect periodici- ties from the discrete Fourier transform, and recent high-frequency work follows suit, with Wu et al. (2025) using Fourier analysis to identify dominant periodicities in equity volumes indexed by frequency rather than by within-cycle position. Such summaries are well suited to identifyingwhichcyclic frequencies are present but not where in the cyclethe dependence concentrates, which is exactly the object of interest here: the quarter-hour b …

- **p.30** (BM25 -3.698):
  > a-low-latency data processing. Second, the forecast should be interpreted as an input to execution and liquidity provision rather than as a standalone trading strategy. The predictable component is small relative to trading costs. The sign-weighted realized forecast target,E[sign( bYt)Yt], averages about 0.5 bp per bound- ary, about one tenth of a single standard-tier taker fee and one twentieth of a round trip. 6 This quantity measures the predictable component in return units rather than the return to a directly im- plementable strategy, since the opening reference price is not necessarily attainable. The forecast is close to well calibrated, with Mincer–Zarnowitz slopes between 0.77 and 0 …

- **p.40** (BM25 -3.589):
  > int shares are imprecisely estimated. Inference therefore rests on the cross-asset replication of the rotation under the joint moving-block bootstrap, which preserves both serial and cross-asset de- pendence. These results indicate that the component associated with quarter-hour predictability changes with the return horizon. At the four-hour horizon, the contribution is concentrated in the lagged- flow component, linking short-horizon predictability primarily to the persistence of periodic order flow. At longer horizons, the public-signal component dominates in every contract. The decom- position, however, does not cleanly separate the underlying information sources. Because public signals  …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
