# 個股期橫斷面動量 + RMT 複雜度 Gap regime filter

**論文**:
- Mukhia, Ansari et al. (2026), "Structural Dynamics of G5 Stock Markets
  During Exogenous Shocks: A Random Matrix Theory-Based Complexity Gap
  Approach", arXiv:2604.19107.
- Jegadeesh & Titman (1993) 經典橫斷面動量.

## 訊號

### 1. Cross-Sectional 6-1 Momentum

對個股期 universe (TEJ `get_stock_futures_universe`) 連續月合約：

```
score_i = log(P_{i, t-21}) - log(P_{i, t-21-126})
```

每月初做 ranking，做多 top 10%，做空 bottom 10%，等權，月度再平衡。

### 2. RMT Complexity Gap (regime filter)

論文核心：用過去 60 日報酬建相關矩陣 C，
```
complexity_gap = lambda_max(C) / N - mean(off-diagonal C)
```

- **Pre-shock**: gap > 0 (結構豐富，多因子主導) → 全倉
- **During-shock**: gap → 0 (單一因子同步) → 砍倉
- **Recovery**: gap 緩慢回升

| gap | 倉位係數 |
|---|---|
| ≥ rmt_threshold (0.20) | 1.0 (全倉) |
| 0.05 ~ 0.20 | 0.5 (半倉) |
| < 0.05 | 0.0 (空倉) |

### 3. TX 對沖

`hedge_with_tx=true` 時，TX 連續月空單張數對齊「淨權重」總和，把市場 beta
中性化。如果做多權重 = 做空權重，net_w ≈ 0，幾乎不需 TX。

## 為何匹配台灣個股期

- 個股期相對股票多空雙邊都簡單 (現股做空被券限影響)
- TQuant-Lab 直接提供 `get_stock_futures_universe` helper
- 個股期保證金率比股票低，做橫斷面 L/S 資金效率較高
- universe 約 200+ 支，符合 RMT lambda_max 統計需求 (N >> 1)

## 限制

- 個股期流動性不齊：盤中無法成交大量小型股期 → 實盤滑價較大
- TEJ helper 取得的 universe 隨時間變動，回測時 look-ahead 風險小但要小心
- 對沖 TX 是粗略 beta 中性化，不真正控制 sector exposure
- RMT gap 的 0.20 / 0.05 閾值是估計值，實盤前要用 in-sample 重新校準

## 跑回測

```bash
# 先 ingest 個股期 (universe 較大)
export ticker="IR0001 IX0001"
export future="$(python -c "from zipline.TQresearch.futures_package import get_stock_futures_universe; _, u = get_stock_futures_universe(st='2020-01-01', et='2026-04-30'); print(' '.join(list(u) + ['TX', 'MTX']))")"
export mdate="20200101 20260430"
zipline ingest -b tquant_future

cd strategies
python -m _common.runner \
    --strategy xsmom_stkfut_rmt/strategy.py \
    --config   xsmom_stkfut_rmt/config.yaml \
    --output   /tmp/xsmom.pkl
```
