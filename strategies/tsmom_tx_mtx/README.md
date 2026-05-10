# 時序動量 (TSMOM) 應用於 TX + MTX

**論文**: Wiley JFM fut.70093, "Curve Momentum in China" (2026, EarlyView)
**理論支援**: Moskowitz/Ooi/Pedersen (2012); Hurst/Ooi/Pedersen (2017).

> 註: fut.70093 的 abstract 在 RSS feed 為空 (僅標題 + 期數)。
> 本策略採古典 12-1 TSMOM 規格，與 paper 主題對齊但未複製其曲線特定設定。

## 規則

1. 每月初 evaluate (`date_rules.month_start()`)。
2. 對每個 root (TX, MTX)：
   - 訊號：log(P_{t-21}) − log(P_{t-273}) → sign 即多空方向
   - sigma：60 日 center-of-mass EWMA vol，年化
   - 權重：sign × (target_vol / sigma) / N_assets
3. 總槓桿不超過 `max_gross_leverage` (預設 1.5)
4. 換成口數：weight × portfolio_value / (price × point_value)
   - TX point_value = 200 NTD
   - MTX point_value = 50 NTD

## 為什麼選 TX + MTX

- 同樣標的（加權指數）但 point value 比 4:1，能在不同資金規模做細部 sizing
- 流動性最高的兩支台灣指數期貨
- 換月日大致同步，便於統一處理

## 限制

- 大盤指數的時序動量 paper 顯示 sharpe ~0.5 級距，比商品 momentum 弱
- 12-1 lookback 對 2020 疫情急殺與 2022 急彈反應遲滯，可考慮加 6-1 overlay
- 與 vgrsi_tx / cubic_momentum_tx 同時跑時注意總曝險合計

## 跑回測

```bash
cd strategies
python -m _common.runner \
    --strategy tsmom_tx_mtx/strategy.py \
    --config   tsmom_tx_mtx/config.yaml \
    --output   /tmp/tsmom.pkl
```
