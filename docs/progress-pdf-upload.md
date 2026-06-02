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

（每完成一個 milestone 在下方追加 `## Mn — <title>` 段落。）
