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

## 進度日誌

### M1 — 驗證 + plan ✅

確認 34 個 PDF 即時反映（summary 34 / pdf=local 34 筆 / 檔案 serve 200）；
釐清連結不需重建，問題在預設視圖。Commit `<M1>`。

### M2 — 預設改「有 PDF」 ✅

- `index.html`：papers-filter 預設選 `any`（選項順序也調成 有PDF / 只本地 /
  全部依日期）。`loadPapers` 已讀此值，無需改 JS。
- **瀏覽器截圖驗證**：預設載入即顯示有 PDF 的論文清單（大量 arxiv，PDF 欄
  「本地」連結），summary 卡「已下載 PDF: 34」。
- webui 測試 34 綠（後端未動）。

Commit: `M2: default papers view to "has PDF" so local links show on load`

## 結論

本地 PDF 超連結本來就即時反映（無需重建）；真正讓使用者看不到的是預設日期
視圖。把預設篩選改成「有 PDF」後，34 個本地 PDF 連結一載入就可見。

## Fallback 指引

純前端預設值變更（一處 `selected` + 選項順序）。回滾：`git revert <M2>`
把預設改回「全部（依日期）」。無資料/API 變更。
