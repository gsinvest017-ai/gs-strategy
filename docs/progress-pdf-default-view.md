# Surface downloaded PDFs by default on the dashboard

## 背景

使用者跑 `quant-crawl fetch-pdfs` 後，`data/pdfs/` 從 2 → **34** 個本地 PDF，
要求「更新 dashboard 上的本地 PDF 超連結」。

## 關鍵事實：連結是即時的，不需要重建

dashboard 每次 request 都即時掃 `data/pdfs/`（`stats.has_local_pdf` /
`pdfs_downloaded`），沒有快取或 build 步驟。驗證（34 個 PDF）：

- `GET /api/summary` → `pdfs_downloaded: 34`
- `GET /api/papers?pdf=local&limit=500` → 34 筆，皆帶 `pdf_local`
- `GET /files/pdf/arxiv_2604_19107.pdf` → HTTP 200 application/pdf 16.6MB

→ 本地超連結已自動反映全部 34 個 PDF。

## 真正要修的：預設視圖看不到

papers 面板預設顯示「指定日期(今天)新增」→ 今天無新增 → fallback 最新 15 筆，
而那 15 筆是無 pdf_url 的 wiley → 使用者第一眼仍看不到 PDF，得手動切
「只看本地 PDF」。前一個 fix 的「後續方向」已標記此點。

## 修正

把 papers 面板**預設篩選器改為「有 PDF（本地或遠端）」**，載入即顯示所有有
PDF 的論文（34 個本地以 📄本地 標記、其餘有 pdf_url 的以 ⬇遠端）。保留
「全部（依日期）」與「只看本地 PDF」選項。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 驗證紀錄 | 本檔（已確認 34 PDF 即時反映） |
| M2 | 預設視圖改「有 PDF」 + 驗證 | index.html 預設選項 + loadPapers 初始 hint；瀏覽器截圖；README/docs |

## Fallback 指引

純前端預設值變更（一處 `selected` + JS 初始邏輯）。回滾：`git revert <M2>`
把預設改回「全部（依日期）」。無資料/API 變更。
