# disposition_rebound_tw — 處置股入獄後反彈

入獄當日買進台股處置股，持有 10 個交易日。
**這是民間說法的反向**：民間做「入獄短期空」，資料說那既做不到、方向也錯。

完整研究：[`docs/findings-disposition-rebound.md`](../../docs/findings-disposition-rebound.md)
數學規格：[`docs/math-spec-pv-technical-analysis.md`](../../docs/math-spec-pv-technical-analysis.md) §9

---

## 一句話結論

2,101 個事件（2021-01 ～ 2026-08）：扣成本後淨 **+277.5 bps／筆（t = 7.50）**，
6 年中 5 年顯著為正。在 24 個變體的聯合檢定中，是通過
Romano–Wolf StepM 家族錯誤率控制的 3 個之一；**沒有任何空方變體存活**。

---

## 為什麼不做空

| 檢查 | 數字 |
|---|---|
| 處置日同時被禁當沖 | **100.0%** |
| 融券量（處置期間／事件前）中位數比 | 0.49 |
| 處置期間融券中位數 | **6 張／日** |
| 入獄日異常報酬 | -64 bps |
| 做空來回成本 | 111 bps |

當沖放空機制上不存在；融券法律上可行但容量等於零；
而且入獄日的跌幅比做空成本還小。**淨 -46 bps（t = -3.46）。**

---

## 訊號

```
u = 0   入獄日（處置生效首日，事前已公告）→ 收盤買進
u = 10  平倉
```

事件時間的異常報酬（對動能／周轉率配對控制組，bps）：

```
 u:   -1      0     +1    +2    +4    +6     +8    +9   +10
     -16   -64.4  +38.8 +35.0 +72.4 +47.1 +117.9 +73.4 -10.5
                  └──────── alpha 在這裡 ────────┘  └ 處置期滿後歸零
```

---

## 檔案

| 檔案 | 用途 |
|---|---|
| `strategy.py` | zipline `initialize` / `handle_data`，自給自足（spec v1 §3 規則 10） |
| `manifest.yaml` | spec v1 metadata |
| `config.yaml` | `strategies/_common/runner.py` 用的舊式設定 |
| `assets/events.csv` | 2,126 筆事件行事曆，由 `scripts/export_disposition_events.py` 產生 |

### 重新產生事件行事曆

```bash
python scripts/export_disposition_events.py --end 2026-08-27
```

### 重跑完整研究

```bash
python scripts/run_disposition_study.py --json out.json
```

---

## 參數

| 參數 | 預設 | 說明 |
|---|---|---|
| `hold_sessions` | 10 | 持有交易日數，對應研究的 CAR[1,10] |
| `position_pct` | 0.04 | 每個事件的資金比例 |
| `max_concurrent` | 12 | 同時持有上限 |
| `min_strength` | `null` | 要求事件前 20 日漲幅下限（事前可知）；`null` = 全收 |
| `auction_interval_min` | `null` | `5` = 只做第一次處置、`20` = 只做第二次；`null` = 全收 |

`events.csv` 的 `realised_end` / `realised_sessions` 兩欄是**未來資訊**，
僅供診斷。`strategy.py` 在載入時就把它們丟掉（`_FUTURE_COLUMNS`），
因為處置期可被延長，實現長度在進場時不可知。

---

## ⚠️ 部署前必讀

1. **容量是真正的限制，不是統計。**
   處置期間成交在 5 或 20 分鐘一次的集合競價，成交金額大幅萎縮。
   成本模型假設 2×25 bps 競價滑價；損益兩平在約 370 bps。
   在流動性崩塌的名字上實際滑價可能達到那個水準。**上線前必須用 tick 資料量測。**

2. **最大回撤 63.3%，勝率只有 52.4%。**
   平均 +278 bps 但中位數只有 +82 bps —— 報酬右偏，靠少數大贏家。
   漏掉幾筆就沒有 edge。依規格 §8 的 $1/L^2$ 定律，這個 MDD 下可用槓桿極低。

3. **可能只在多頭有效。** 2021 與 2026 佔樣本 47%，兩年皆多頭；
   2022（唯一的空頭年）恰好打平（-6.7 bps, t = -0.05）。

4. **`bundle: tquant`（股票）不是 `tquant_future`。**
   跑之前要先 ingest 股票 bundle。

因此 `manifest.tags` 帶 `needs-review`。這是一個有統計證據的研究結果，
**不是一個可以直接接上真錢的策略**。
