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

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
