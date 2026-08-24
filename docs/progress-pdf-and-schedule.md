---
type: progress
updated: 2026-05-27
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# 每日排程 + Dashboard PDF/Spec 超連結

> 兩件事：(1) 替爬蟲建每日系統排程，定期更新 papers.db / dashboard；
> (2) 在 webui dashboard 替「爬下來的 PDF」與「策略 spec markdown」加檔案超連結。

## 目標

### Part 1 — 每日系統排程
每天自動跑爬蟲更新 `data/papers.db`（dashboard 即時讀此 DB），並順手把新論文
的 PDF 下載到 `data/pdfs/`。用 cron 實際安裝（使用者明確要求「定期更新」）。

### Part 2 — Dashboard 檔案超連結
webui 面板：
- **論文列**：超連結到 PDF。優先本地檔（`data/pdfs/<slug>.pdf`，由 webui 經
  HTTP serve），無本地檔則 fallback 到 remote `pdf_url`。
- **策略列**：超連結到該 bundle 的 spec markdown（`README.md`）與 `manifest.yaml`，
  由 webui serve。

## 現況調查

- `data/pdfs/` **空的**；crawler 預設 `download_pdfs=False`，只存 remote
  `pdf_url`。34/87 篇有 pdf_url（arxiv/nber）。→ Part 2a 需要先實作本地下載。
- `RateLimitedSession.download(url, dest)` 已存在（stream 到磁碟）。
- 4 支 bundle 都有 `README.md`（= 策略 spec）+ `manifest.yaml`；generated bundle
  亦由 generator 寫 README.md。
- crontab 已有 `gs-claude-config night-shift`、`quantdata-daily-refresh`
  （屬 gs-scraper，非本 repo）。本任務用獨立 marker `# >>> gs-strategy daily_refresh <<<`，
  互不干擾（`install_daily_refresh.sh` 已具此 marker 邏輯）。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + plan | 本檔 |
| M2 | PDF 本地下載 | `quant_crawler/pdf_fetch.py`、`Storage.papers_with_pdf`、`quant-crawl fetch-pdfs` + tests |
| M3 | 每日系統排程 | daily_refresh.sh 接 fetch-pdfs；備份 crontab 後 `install_daily_refresh.sh --apply`；驗證 |
| M4 | dashboard 超連結 | stats 加 `pdf_local`/`spec_md`/`manifest_rel`；server `/files/pdf/*`、`/files/strategy/<id>/<f>`；前端連結 + 瀏覽器截圖驗證 |
| M5 | tests + docs | server file-route 測試、README、本檔總結 |

## PDF 檔名規則

`pdf_filename(source, source_id)` = `<source>_<sanitised source_id>.pdf`
（小寫、非 alnum → `_`、去頭尾 `_`、截 80）。例：
`arxiv 2605.01300` → `arxiv_2605_01300.pdf`。stats 與 pdf_fetch 共用此函數，
確保 dashboard 算出的本地路徑與下載寫入路徑一致。

## 安全性（file serving）

webui 新增的 `/files/*` 路由只 serve 兩個白名單根目錄：
- PDF：`config.PDF_DIR`（`data/pdfs/`）
- 策略檔：`strategies/<id>/`（僅限 `.md` / `.yaml` / `.yml` / `.py`）
每個都用 `resolve()` + `relative_to()` 擋 path traversal（與既有 `/static/` 同模式）。

## Fallback 指引

1. **移除 cron**：`./scripts/install_daily_refresh.sh --uninstall`
   （或從備份 `crontab < /tmp/crontab.backup.<ts>` 還原）
2. **回滾 PDF 下載**：`rm quant_crawler/pdf_fetch.py`；CLI/Storage 的新增方法
   `git revert <M2>`；已下載的 `data/pdfs/*.pdf` 可留可刪（gitignored）
3. **回滾 dashboard 連結**：`git revert <M4>`（純前端 + serve 路由，唯讀）
4. 最差：`git reset --hard 9a93874`（webui M5 commit）

## 進度日誌

### M1 — 計畫 + 調查 ✅

確認 `data/pdfs/` 空、crawler 預設不下載、`RateLimitedSession.download` 已存在、
4 bundle 都有 README.md、crontab 既有兩條 job 用不同 marker。Commit `<M1>`。

### M2 — PDF 本地下載 ✅

- `Storage.papers_with_pdf(limit, source)` — 撈有 pdf_url 的論文
- `quant_crawler/pdf_fetch.py`：`pdf_filename` / `local_pdf_path` /
  `has_local_pdf` / `fetch_pending`（用 RateLimitedSession 串流下載，
  per-paper try/except 隔離，跳過已存在、刪零位元組殘檔）
- CLI `quant-crawl fetch-pdfs [-n N] [-s SOURCE]`
- `tests/test_pdf_fetch.py` 9 個（檔名規則、skip/limit/failure、source filter）
- **真實下載驗證**：arxiv 2 篇 → `data/pdfs/`，`file` 確認為 valid PDF
  （3.5MB / 1.1MB），`data/pdfs/` 已 gitignore 不入版控

Commit: `M2: local PDF download — pdf_fetch + quant-crawl fetch-pdfs CLI`

### M3 — 每日系統排程 ✅

- `daily_refresh.sh` 升成 4 階段：crawl → **fetch-pdfs（best-effort，非致命）**
  → strategy_gen → validate
- **實際安裝 cron**（使用者明確要求「定期更新」）：
  - 先備份 `crontab -l > /tmp/crontab.backup.<ts>`（16 行）
  - `install_daily_refresh.sh --apply --schedule "30 6 * * *"`（6:30 錯開既有
    00:00 night-shift 與 17:30 quantdata job）
  - 驗證：三個 marker block 都在，既有兩條 job 未被動到
- 回滾：`./scripts/install_daily_refresh.sh --uninstall`

Commit: `M3: daily_refresh adds fetch-pdfs step (now 4-stage); cron installed @6:30`

### M4 — dashboard 超連結 ✅

- `stats.py`：`_paper_row` 補 `pdf_local`（本地檔名 or None）+ `pdf_url`；
  bundle record 補 `has_spec_md` / `spec_files`；新增 `bundle_dir_for(id)` resolver
- `server.py`：`/files/pdf/<name>`（限 .pdf）、`/files/strategy/<id>/<file>`
  （限 .md/.yaml/.yml/.py），共用 `_send_file` 做 resolve+relative_to 防護 +
  Content-Disposition inline
- 前端：論文表加「PDF」欄（📄本地 / ⬇遠端 / —）；策略表加「spec」欄
  （📑spec + manifest 連結）
- **curl 驗證**：本地 PDF 200 application/pdf 3.5MB、README.md 200 text/markdown、
  traversal 403 / 壞副檔名 403 / 未知策略 404
- **瀏覽器截圖**：shot-scraper 確認新欄位渲染

Commit: `M4: dashboard hyperlinks — local/remote PDF + strategy spec markdown`

### M5 — 測試 + docs ✅

- `test_webui_server.py` +7（spec md / manifest / 未知 id 404 / 壞副檔名 403 /
  PDF 404 / traversal）；`test_webui_stats.py` +3（pdf_local 掛載、
  `bundle_dir_for`、spec_files）
- 全 webui+pdf 測試 36 綠
- README 加「每日排程 + PDF 下載」與 dashboard 超連結說明
- 本檔進度日誌補完

Commit: `M5: tests for file-serving routes + pdf_local; README updates`

## 結論

- **Part 1（每日排程）**：cron 已實際安裝 @6:30，每天 crawl→fetch-pdfs→gen→
  validate；dashboard 即時反映最新 DB。可 `--uninstall` 或從備份還原。
- **Part 2（超連結）**：dashboard 論文列連 PDF（本地優先 / 遠端 fallback），
  策略列連 spec markdown + manifest，全部經安全的 `/files/*` 路由 serve。

## 後續方向

1. PDF 下載目前抓「所有有 pdf_url 但無本地檔」的論文；量大時可在 daily 用
   `fetch-pdfs -n N` 限流，避免單日對 arxiv 過量請求。
2. spec markdown 目前 serve 原始 .md（瀏覽器顯示純文字）；若要 render 成 HTML
   可在前端引一個輕量 markdown renderer 或 server 端轉換。
3. 可在 summary 卡片加「本地 PDF 數 / 有 pdf_url 數」一欄，讓下載覆蓋率一目了然。
