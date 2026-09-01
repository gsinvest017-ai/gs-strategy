# Tokenized but Illiquid? Evidence from Real-World Asset Markets

Auto-generated bundle from `arxiv:2606.01131`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.01131v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.01131",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.01131")`.

### Auto-retrieved passages

- **p.2** (BM25 -3.733):
  > First, it develops a multidimensional empirical framework for observed RWA liquidity that distinguishes between turnover-based activity, participation breadth, and simple active-versus-inactive states. Second, it extends the discussion beyond single-platform real-estate evidence by comparing observed liquidity across a focused sample of tokenized Treasuries, gold-backed commodities, and private-credit-related assets. Third, it proposes a feasible empirical strategy for a young and data-constrained market, combining descriptive analysis, non- parametric group tests, and exploratory panel regressions that emphasize disciplined association rather than unsupported causal claims. The remainder of …

- **p.5** (BM25 -3.654):
  > analysis uses log active addresses and an active-month indicator to capture alternative dimensions of observed liquidity. The robustness analysis also considers the active ratio, which relates active participation to the broader holder base. All continuous size and participation variables are log-transformed because the data is highly skewed, with substantial differences between small and large tokens. 3.3 Hypotheses and empirical strategy Given the variables available in the token-month panel, the empirical analysis tests three hypotheses. 1.H1:Observed liquidity differs across tokenized RW A asset classes. 2.H2:Tokens with broader holder bases exhibit higher observed liquidity. 3. H3:Large …

- **p.4** (BM25 -3.501):
  > Tokenized but Illiquid? Evidence from Real-World Asset MarketsA PREPRINT An important measurement caveat is that on-chain transfers are not equivalent to economic trades. Monthly transfer volume may reflect genuine secondary-market activity, but it may also include minting and redemption events, treasury movements, custodial rebalancing, or other operational flows. For this reason, the analysis treats transfer-based variables as proxies for observed liquidity rather than direct measures of execution quality, bid-ask spreads, market depth, or price impact. The empirical results should therefore be interpreted as evidence on relative on-chain activity and tradability across tokens and over tim …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
