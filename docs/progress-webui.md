# gs-strategy 管理介面 (web UI)

> 給 gs-strategy 加一個本地網頁管理介面，彙整爬蟲與策略產生 pipeline 的狀態。

## 目標

一個零外部依賴（stdlib `http.server`）的本地 web 管理面板，顯示：

1. **論文/報告總量**：總數 + 各來源 (arxiv/nber/repec/fed_feds/wiley/aqr) 分布
2. **當日爬蟲 routine**：今天（或指定日期）跑了哪些 source、items_seen/kept、
   錯誤、起訖時間（來自 `crawl_runs` 表）
3. **當日新資料**：今天 fetched 的新論文清單（title / source / published / url）
4. **策略清單**：`strategies/`（手寫）+ `strategies/_generated/`（自動產生）
   每支的 id / template / tags / requires_review / source.kind
5. **匯出狀態**：每支策略是否已匯出到 `~/gs-zipline-tej/strategies/<id>/`
   （已匯出 / 未匯出）

## 技術選擇

- **後端**：Python stdlib `http.server`（`ThreadingHTTPServer`）。venv 沒有
  Flask/FastAPI，且這是本地單人管理面板，stdlib 足夠且零新依賴。
- **前端**：單頁 vanilla HTML + CSS + JS（fetch /api/*），不引入框架。
- **資料層**：`stats.py` 純函數，讀 `data/papers.db` + 掃 `strategies/` 檔案系統，
  回 dict，方便單元測試（不經 HTTP）。
- **port**：預設 5057（避開 zipline dashboard 5000/5001、jupyter 8888）。

### 「已匯出」定義

gs-strategy 的某支 bundle（id = 目錄名）若在
`~/gs-zipline-tej/strategies/<id>/manifest.yaml` 存在 → 視為已匯出。
gs-zipline-tej strategies 路徑可用環境變數 `ZIPLINE_TEJ_STRATEGIES_DIR` 覆寫
（預設 `~/gs-zipline-tej/strategies`）。

## API

| endpoint | 回傳 |
|---|---|
| `GET /` | index.html (單頁面板) |
| `GET /api/summary` | 總量卡片：papers 總數/各源、runs 總數、strategy 數、已匯出/未匯出數 |
| `GET /api/runs?date=YYYY-MM-DD` | 指定日（預設今天）的 crawl_runs |
| `GET /api/papers?date=YYYY-MM-DD&limit=N` | 指定日新增論文（無 date 則回 latest N） |
| `GET /api/strategies` | 策略 inventory + 匯出狀態 |

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + plan | 本檔 |
| M2 | 資料層 stats.py | `quant_crawler/webui/{__init__,stats}.py` + `tests/test_webui_stats.py` |
| M3 | HTTP server + API | `webui/server.py`、`webui/__main__.py`、`scripts/run_webui.sh` |
| M4 | 前端單頁 | `webui/static/{index.html,app.js,style.css}` |
| M5 | API 測試 + docs + 報告 | `tests/test_webui_server.py`、README、本檔總結 |

## 資料來源對照

| 面板區塊 | 資料來源 |
|---|---|
| 論文總量/各源 | `Storage.count()` / `stats_by_source()` |
| 當日 routine | `crawl_runs` where `started_at LIKE 'DATE%'` |
| 當日新資料 | `papers` where `substr(fetched_at,1,10)=DATE` |
| 策略清單 | 掃 `strategies/*/manifest.yaml` + `strategies/_generated/*/manifest.yaml` |
| 匯出狀態 | 檢查 `~/gs-zipline-tej/strategies/<id>/manifest.yaml` 是否存在 |

## Fallback 指引

1. 整個 webui 是新增、獨立模組，不動既有 crawler / strategy_gen 程式：
   - 移除：`rm -rf quant_crawler/webui tests/test_webui_*.py scripts/run_webui.sh`
   - 或 `git revert <M5>..<M2>`
2. 純讀取面板，不寫 DB、不改策略檔，rollback 零副作用。
3. 最差：`git reset --hard 0aaa00e`（taxonomy M5 commit）。

## 進度日誌

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
