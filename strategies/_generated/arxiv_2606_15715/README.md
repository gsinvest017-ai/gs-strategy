# Trading in the Sunshine or in the Shade: Market Impact and Adverse Selection on Hyperliquid

Auto-generated bundle from `arxiv:2606.15715`.

Template: **buy_and_hold**

Matched keywords: `(none)`

Paper URL: http://arxiv.org/abs/2606.15715v1

## RAG source context (use to extract the correct formula)

This paper's full text is indexed. Below are the top passages auto-retrieved
for the **buy_and_hold** signal — verify the formula against them.
For a targeted lookup, query the `gs-strategy-rag` MCP server:

```
get_paper_context(source="arxiv", source_id="2606.15715",
                  query="<the signal/factor formula you need>")
```
or `get_paper_fulltext("arxiv", "2606.15715")`.

### Auto-retrieved passages

- **p.26** (BM25 -3.259):
  > tivity rather than a diffuse pattern of metaorders being executed passively. After excluding these top-40 passive-volume addresses, the same-direction maker-fill rate falls to about31%. We therefore keep the market-orders-only definition as the main object and treat the filled-limit-order evidence as a contamination and classification caveat, rather than as a correction to metaorder size or participation. Second, the contrast between native TWAPs and statistical metaorders is observational. Traders choose whether to use the protocol-native TWAP tool, and this choice is strongly tied to trader identity. In an out-of-sample horse race, a pair-only model has AUC0.674, adding pre-start book stat …

- **p.3** (BM25 -3.104):
  > native TWAP are visible from inception, these orders provide a natural form ofsunshine trading in a traditional electronic market. Alongside them, we reconstructstatistical metaorders, i.e., executions carried out without a protocol-native mechanism and instead implemented through proprietary execution methods. We identify them by aggregating sequences of same-sign market orders from the same address under a standard splitting hypothesis [22, 23, 24]. This allows us to compare automated TWAP programs, whose parent-order parameters are observable from inception, with latent metaorders reconstructed ex post, whose intended size, horizon, and execution rule are not directly observed. Our main f …

- **p.3** (BM25 -2.992):
  > Fi is therefore a useful laboratory for studying the costs and benefits of transparency. In this paper, we investigate the role of sunshine trading in price impact and transaction costs by using the unique environment provided by the Hyperliquid blockchain [21]. Hyperliquid is a market for spot and perpetual futures based on a fully on-chain central limit order book (CLOB), i.e., the standard market mechanism in traditional finance. Its architecture makes market activity observable at high frequency: order flow, executions, account-level activity, and the address initiating each action can be reconstructed from public data. More importantly, traders on Hyperliquid can use protocol-native TWA …

## Review checklist

1. Pull the paper's real formula from the RAG MCP server (above).
2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.
3. Verify default params match the paper (lookback, thresholds,
   instruments, etc.).
4. Confirm cost / slippage / position-sizing assumptions.
5. Set `manifest.requires_review: false` only after sign-off.
