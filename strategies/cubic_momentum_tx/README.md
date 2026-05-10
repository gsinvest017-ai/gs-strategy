# Cubic Momentum 趨勢與崩盤策略 (TX)

**論文**: Yoshida (2026), "Dynamics of Periodic Bubbles and Crashes:
Modeling Market Overheating and Panic Selling via Cubic Momentum",
arXiv:2605.00854.

## 核心概念

論文提出極簡的離散時間模型：
- **動量** = lookback 期內價差總和
- **過熱訊號** = 動量 + α × 累積超量交易 (Hawkes-like)
- 交易方向由三次方函數決定：
  ```
  f(m) = a·m - b·m³
  ```
  - 在中等動量區趨勢追隨
  - 動量超過臨界值 |m_c| = √(a/3b) 後翻轉 → 模擬「過熱崩盤 / 恐慌賣壓」

## 本實作

- 把動量正規化為 z-score (除以 sigma×√lookback) 讓 a/b 與 regime 解耦
- 設臨界 z_crit = 1.5 (paper 暗示 1.0~2.0)
- f(z)/f(z_crit) 線性映射到 [-max_contracts, +max_contracts]
- z 在 0~1.5 區間：多單部位漸增
- z > 1.5 cubic 翻轉：多單漸減 → 過頂後反向開空 (allow_short=true)

## 何時失效

- TX 多年大牛市時 z 經常徘徊 1.0 附近，cubic 機制少觸發
- 短線跳空導致 sigma 跳升，z 被低估 → 訊號鈍化
- 適合做為 trend + mean-reversion 混合策略的元件，不建議單獨高槓桿

## 跑回測

```bash
cd strategies
python -m _common.runner \
    --strategy cubic_momentum_tx/strategy.py \
    --config   cubic_momentum_tx/config.yaml \
    --output   /tmp/cubic_momentum_tx.pkl
```
