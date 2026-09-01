# On a Simple Relationship Between Order Imbalance, Skew and Width in Over-The-Counter Trading

Auto-generated bundle from `arxiv:2608.07690`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2608.07690v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2608.07690",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2608.07690")`.

### Auto-retrieved passages

- **p.3** (BM25 -3.134):
  > 1.2 Literature The dealer-inventory line begins with Garman [1], whose dealer faces genuinely asymmetric Poisson buy and sell rates, the oldest imbalanced-flow model, but sets a single static price pair, the content being ruin rather than policy. Amihud and Mendelson [2] are the closest classical antecedent in spirit: imbalanced arrivals move a preferred inventory position and monotone quotes, though the results are structural rather than closed form. Ho and Stoll [3] quote from value function differences, and theslopehalf of the slope-and-convexity characterization of Section 2.2 is implicit there and in everything since; theconvexityhalf states that the discretionary component of a dealer’ …

- **p.2** (BM25 -3.1):
  > rinciple; we make no empirical claims here. 1.1 The CWLS benchmark. Making constant width markets with skew linear in inventory. To fix terminology, a dealer’swidthis the difference between where she is prepared to bid and where she is prepared to offer, and herskewis the difference between the average of the two and her estimate of fair value. The Constant Width Linear Skew heuristic maintains a fixed width and sets skew proportional to signed inventory, with a sign that leans the dealer towards a neutral position. Motivations for CWLS range from its prima facie reasonableness to formal justification as an approximate solution of a stochastic control problem [4, 5]. These justifi- cations r …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
