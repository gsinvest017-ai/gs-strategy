---
type: progress
updated: 2026-06-02
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# 手動批次上傳 paper/report PDF

## 目標

在 webui dashboard 加一個「上傳 PDF」面板，讓使用者透過瀏覽器 file selector
**一次選多個 PDF 檔批次上傳**。上傳的檔案存進 `data/pdfs/`、在 `papers.db`
建立 `source='manual'` 的 paper row，使其立即出現在論文清單、可被 RAG ingest。

## 設計決策

- **來源標記**：`source='manual'`，`source_id` = 檔名 slug（sanitise + 衝突加
  數字尾碼），讓它跟 crawler 來的論文在同一張表共存、可被 kind 分類 / 標籤。
- **本地檔名**：沿用 `pdf_fetch.pdf_filename('manual', slug)` →
  `manual_<slug>.pdf`，與既有 RAG ingest（`papers_with_pdf` + `local_pdf_path`）
  完全相容，上傳後 `quant-crawl rag-ingest` 就能索引。
- **paper row 內容**：`title` = 原始檔名（去 `.pdf`）、`pdf_url` 留空、
  `raw_extra={"uploaded": true, "orig_filename": ...}`、`fetched_at` = now。
- **multipart parser**：手刻最小 parser（不用 3.13 已移除的 `cgi`），從
  `Content-Type` boundary 切 part、抽 filename + bytes。
- **驗證**：副檔名 `.pdf` + magic bytes `%PDF` 開頭；單檔上限 50 MB；
  非 PDF / 過大 → 該檔 skip 不中斷其他。
- **寫入端**：dashboard 之前已有 `POST /api/labels`（有限寫入），這裡再加
  `POST /api/upload`（multipart）。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 設計 | 本檔 |
| M2 | upload 後端模組 | `quant_crawler/webui/upload.py` + `tests/test_upload.py` |
| M3 | server 路由 + 前端 panel | `POST /api/upload`、index.html/app.js/css file selector |
| M4 | docs + 驗證 | README、瀏覽器截圖、本檔總結 |

## Fallback 指引

- 純新增模組 + 路由 + 前端 panel，不動既有 crawler / RAG / 其他 webui 邏輯。
- 回滾：`git revert <M4>..<M2>`。
- 已上傳的檔案是 `data/pdfs/manual_*.pdf` + `papers` 內 `source='manual'` row；
  要清：`rm data/pdfs/manual_*.pdf` + `DELETE FROM papers WHERE source='manual'`。

## 進度日誌

### M1 — 進度檔 + 設計 ✅
確認 do_POST 既有 `/api/labels`、PaperRecord 欄位、pdf_fetch 命名規則、
Python 3.12（選擇手刻 multipart parser 以相容 3.13+，不用已移除的 `cgi`）。
Commit: `M1: 手動批次上傳 PDF 功能 — 計畫與設計`

### M2 — upload 後端模組 ✅
- `quant_crawler/webui/upload.py`：
  - `parse_boundary` / `parse_multipart`（手刻；**修掉 `strip(b"\r\n")` 誤吃
    content 結尾 `\n` 的 bug**，改逐層剝 delimiter framing CRLF）
  - `slug_from_filename`、`_unique_source_id`（衝突加數字尾碼）
  - `save_upload`（驗 PDF magic + 50MB 上限 + 存檔 + 建 manual paper row）
  - `handle_upload`（批次：parse → 逐檔 save → uploaded/skipped 摘要）
- `tests/test_upload.py` 14 案例（boundary/multipart/slug/驗證/dedup/批次/
  non-multipart/no-files）
Commit: `M2: webui/upload.py — multipart 解析 + 存 PDF + 建 manual paper row`

### M3 — server 路由 + 前端 panel ✅
- `server.py`：`do_POST` 加 `/api/upload` 分支 + `_handle_upload()`
- 前端：index.html「上傳 PDF（手動批次）」panel（`<input type=file multiple
  accept=pdf>` + 上傳鈕 + 結果明細）；app.js `uploadPdfs()` FormData POST、
  成功後刷新 summary/RAG/papers；style.css 加 panel 樣式
- **端到端驗證**：curl multipart → papers.db 建 manual row + 存 PDF；
  瀏覽器截圖確認 panel 在頂部、papers 表第一列就是上傳檔、PDF 欄「本地」連結。
  測完清掉測試資料。
Commit: `M3: 加 POST /api/upload 路由 + 前端批次上傳 panel（file selector）`

### M4 — docs + 報告 ✅
README webui 段補「手動批次上傳 PDF」+ API 清單加 `POST /api/upload`；本檔總結。
Commit: `M4: docs — README 補手動批次上傳 PDF 說明`

## 結論

dashboard 現可透過 file selector 批次上傳 PDF，自動建 manual 來源論文 + 存本地檔，
無縫接上既有 RAG ingest（上傳後跑 `quant-crawl rag-ingest` 即索引）。
65 個 upload+webui 測試全綠。

## 後續方向
- 上傳後自動觸發該檔 rag-ingest（目前要另跑 CLI）
- 拖放（drag-drop）上傳區
- 上傳時可選填 title / kind override（目前 title = 檔名、kind 自動分類）
