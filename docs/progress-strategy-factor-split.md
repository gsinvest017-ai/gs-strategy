# Strategy vs Factor 分類 + 雙 panel dashboard

> 依 `architecture.drawio` 設計（"Strategy/Factor scraper, factor class" +
> "Raw strategy/factor pool"），讓 paper/report scraper 區分爬到的論文屬於
> **strategy（交易策略）** 或 **factor（因子）**，dashboard 分兩個可切換的
> panel，各自支援子類別（自動分類 + 手動新增標籤）。

## 目標

1. **自動 kind 分類**：每篇 paper/report 判為 `strategy` 或 `factor`。
2. **子類別**：每個 kind 有自己的子類別 taxonomy（自動偵測）。
3. **手動標籤**：使用者可在 dashboard 替任一 paper 手動新增/移除子類別標籤，
   也可手動覆寫 kind（修正誤判）。手動標籤須**跨 re-crawl 持久化**。
4. **雙 panel UI**：dashboard 論文區分「策略」「因子」兩個 tab，可切換查詢；
   每個 panel 內可依子類別篩選。

## 資料模型決策

- **kind + 自動子類別** 由 title/abstract 即時推導（純函數，不入庫）——
  分類器改良時自動套用、不需 migration。
- **手動標籤 + kind 覆寫** 存新表 `paper_labels`，與 crawler 的 `papers`
  upsert 解耦，re-crawl 不會洗掉人工標註：

```sql
CREATE TABLE paper_labels (
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    kind_override TEXT,                      -- NULL=用自動; 'strategy'|'factor'
    manual_subcats TEXT NOT NULL DEFAULT '[]', -- JSON list
    updated_at    TEXT,
    PRIMARY KEY (source, source_id)
);
```

- 有效 kind = `kind_override or auto_kind(paper)`
- 有效子類別 = `auto_subcats(paper) ∪ manual_subcats`

## 分類器設計（`quant_crawler/paper_class.py`）

### kind 判定（binary，預設 strategy）

掃 title+abstract+keywords+categories，比較兩組關鍵字分數：
- **factor-leaning**：factor(s) / cross-sectional / anomaly / characteristic /
  risk premi / fama-french / factor model / factor zoo / smart beta /
  return predictab / expected returns / betting against beta / style investing
- **strategy-leaning**：trading strategy/rule/system / backtest / execution /
  market timing / technical indicator / trend follow / pairs trad /
  market making / order book / high-frequency trading / signal / overlay

`kind = "factor" if factor_score > strategy_score else "strategy"`（平手或皆 0
→ strategy，沿用 repo 原始用途）。回傳 score 供透明化。

### 子類別 taxonomy（多標籤）

- **FACTOR_SUBCATS**：value / size / momentum / quality / low-volatility /
  profitability / investment / liquidity / carry / growth / dividend /
  reversal / sentiment / macro / esg / betting-against-beta
- **STRATEGY_SUBCATS**：trend-following / mean-reversion / breakout /
  pairs-trading / statistical-arbitrage / market-making / event-driven /
  volatility / options / technical / time-series-momentum /
  cross-sectional-momentum / machine-learning / high-frequency / arbitrage

## API

| endpoint | 用途 |
|---|---|
| `GET /api/papers?kind=strategy|factor&subcat=<tag>&...` | 依 kind/子類別篩選（沿用既有 pdf/date/limit） |
| `GET /api/taxonomy` | 回 factor/strategy 兩組子類別詞彙（給前端 filter 選單） |
| `POST /api/labels` | 手動標註：`{source, source_id, op, value}`，op ∈ add_subcat/remove_subcat/set_kind |

`POST` 讓 dashboard 從唯讀變成可寫（僅限 paper_labels 表，使用者明確要求手動標籤）。

## UI

- 論文區頂部加「策略 / 因子」tab 切換（預設 策略）。
- 每個 panel：子類別篩選下拉（該 kind 的 auto+已用 manual 子類別）。
- 每列：顯示子類別 chips（自動 + 手動，手動以不同色）；一個小輸入框 + 按鈕
  可手動加子類別；一個小選單可覆寫 kind。
- summary 加 strategy/factor 篇數統計。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 設計 | 本檔 |
| M2 | 分類器 | `paper_class.py`（kind + 子類別）+ `tests/test_paper_class.py` |
| M3 | 手動標籤儲存 + stats 整合 | `paper_labels` 表 + Storage、`list_papers` 支援 kind/subcat、papers 帶 kind/subcats/manual + tests |
| M4 | server + 前端雙 panel | GET kind/subcat、`/api/taxonomy`、POST `/api/labels`；前端 tab + 子類別篩選 + 手動標籤 UI + 瀏覽器驗證 |
| M5 | POST 測試 + docs | server POST/label 測試、README、本檔總結 |

## Fallback 指引

- kind/子類別自動分類純函數，回滾不影響資料。
- `paper_labels` 是新表，移除：`DROP TABLE paper_labels` 或 `git revert <M3>`。
- 前端/ POST：`git revert <M4>`。整段：`git reset --hard 92ed4a5`（stale-server fix M3）。

## 進度日誌

### M1 — 設計 ✅
資料模型（auto 即時推導 + `paper_labels` 存手動）、binary kind 分類、雙子類別
taxonomy、API、UI 規劃。Commit `<M1>`。

### M2 — 分類器 ✅
`quant_crawler/paper_class.py`：`classify_kind`（factor vs strategy 關鍵字計分，
平手→strategy）、`subcategories`（per-kind 多標籤，保守 pattern 防誤判）、
`classify`、`subcat_vocabulary`。16 測試。真實 87 篇 → 69 strategy / 18 factor。
Commit: `M2: strategy/factor classifier + per-kind subcategory taxonomy`

### M3 — 手動標籤儲存 + stats 整合 ✅
- `quant_crawler/storage/labels.py`：`paper_labels` 表 + `LabelStore`
  (get/all_labels/add_subcat/remove_subcat/set_kind)，與 papers upsert 解耦
- `stats._paper_row` 改成附 kind/kind_auto/kind_overridden/subcats_auto/
  subcats_manual/subcats；`list_papers` 加 kind+subcat 篩選（任一 filter 跨全部
  論文）；`kind_counts`；summary 加 `papers_by_kind`；labels 批次載入避免 N+1
- 7 labels 測試 + 6 stats 整合測試
Commit: `M3: paper_labels store + stats kind/subcat integration & filters`

### M4 — server + 前端雙 panel ✅
- server：`/api/papers` 加 kind/subcat 參數、新增 `/api/taxonomy`、新增
  `do_POST /api/labels`（add_subcat/remove_subcat/set_kind）
- 前端：策略/因子 tab 切換、子類別篩選下拉（依 kind 動態）、每列子類別 chips
  （自動灰 / 手動紫 + ×移除）+「+標籤」輸入（datalist 自動補全）+ kind 覆寫
  下拉；summary 加「策略/因子」卡
- 重啟 5057 server；瀏覽器驗證：strategy tab 69 筆 / factor tab 18 筆、
  UI 加標籤端到端寫入成功（POST→reload→chip 出現），測後清除
Commit: `M4: dual strategy/factor panels + subcat filter + manual tag/kind UI + /api/labels POST`

### M5 — POST 測試 + docs ✅
- `test_webui_server.py` +6（taxonomy / kind filter / POST roundtrip+cleanup /
  bad op / missing fields / POST 404）
- 全 webui+分類+labels 測試 78 綠、確認無 DB 標籤污染
- README 加 strategy/factor 雙 panel + 手動標籤段落；本檔總結
Commit: `M5: server POST/taxonomy tests + README strategy/factor section`

## 結論

依 architecture.drawio 落實 strategy/factor 分流：scraper 端有自動分類器，
dashboard 分雙 panel 切換，各支援自動 + 手動子類別標籤（手動標註持久化、
re-crawl 不洗）。dashboard 從唯讀加上有限寫入（僅 paper_labels）。

## 後續方向
- kind 分類目前 binary（無 unknown）；若要更精準可加信心門檻 + 「未分類」桶。
- 子類別 taxonomy 可持續擴充（在 paper_class 加一列 + 補測試 sample）。
- 手動標籤可加「常用標籤」快捷鍵；目前靠 datalist 自動補全。
- factor pool 可進一步接 architecture.drawio 的 "Factor for selector" 流向
  target selector（目前 drawio 標 TODO）。
