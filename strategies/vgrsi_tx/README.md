# VGRSI on TX (Visibility Graph RSI 台指期策略)

**論文**: Rafał Rak, "Visibility graphs can make money in financial markets",
arXiv:2605.01300 (2026).

## 核心概念

把過去 N 根的收盤價映射成可見性圖 (Visibility Graph)：節點 i, j 之間有邊
若且唯若中間每根 k 都嚴格在 (i,P_i)-(j,P_j) 連線下方。對最後一根 t 的
入連線中：

- **up_deg**: 來自更低收盤的可見邊數
- **down_deg**: 來自更高收盤的可見邊數

VGRSI = 100 × up / (up + down)，落在 [0, 100]。

## 交易規則

| VGRSI | 動作 |
|---|---|
| < 30 (lower_threshold) | 多單持倉 = +1 口 TX |
| 30 ~ 70 | 持倉不動 |
| > 70 (upper_threshold) | 平倉；若 allow_short = true 則 -1 口 |

每日收盤前 evaluate；換月用 `roll='calendar'` 在到期前 10 個交易日換到下月。

## 對應論文成果

Rak (2026) 在 DJI30、EUR/USD、XAU/USD 三種商品 503 個交易日測試，年化獲利
USD 340k/USD 1k 倉位，Sharpe 2.55-3.6，回撤 10-18%。本策略單純地把同樣
規則放到 TX，未做 in-sample 重新調參。

## 假設與限制

- 用日頻 close 計算 VG (paper 也是日頻)
- 滑價 6 點是 TX 較保守估計 (1 點 = 200 NTD)
- 多空門檻 30/70 直接沿用 paper 設定，未對 TX 重新優化
- VG 構建為 O(N²)，N=30 時每日只算 ~450 次距離測試，非瓶頸

## 跑回測

```bash
cd strategies
python -m _common.runner \
    --strategy vgrsi_tx/strategy.py \
    --config   vgrsi_tx/config.yaml \
    --output   /tmp/vgrsi_tx.pkl
```
