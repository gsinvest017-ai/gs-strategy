---
type: progress
updated: 2026-05-28
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# Compact dashboard layout (minimize vertical scroll)

## 目標

webui dashboard 目前所有 panel 縱向堆疊，包括長表格（papers 87 列、strategies、
RAG 結果），整頁高 **25,434px @1280×720**（≈35× viewport，要狂捲）。
目標：用 **CSS grid 多欄** + **長表格內部捲動** 把整頁高壓到 ~2× viewport 內，
寬螢幕一眼可以看到所有 panel 標題與重點。

## 設計

不改 panel 內容、不增 JS、純 layout 重構：

1. **主區改 CSS grid（2 欄）**：寬螢幕 (>1100px) 雙欄並排；窄螢幕自動回單欄
   （responsive media query）。
2. **配對**：
   - Row A（全寬）：summary cards
   - Row B：來源分布 | 爬蟲 routine
   - Row C（全寬）：新增資料 papers（最大、占滿）
   - Row D：策略清單 | RAG 全文檢索
   - Row E：MCP server（全寬，矮）
3. **長表格內部捲動**：`tbody { display: block; max-height: 320px; overflow-y: auto; }`
   配 `thead/tr { display: table; width: 100%; table-layout: fixed; }`，
   讓 papers/strategies/rag-table 在固定高度內 scroll，不再撐爆頁面。
4. **summary cards 壓緊**：value 字級略縮（30→24），padding 縮。
5. **panel 之間 gap 縮小**，去掉一些 margin。

## 預期結果

- 寬螢幕（≥1280×720）：整頁高 ≤ 1.5–2× viewport，看到所有 panel 標題；
  表格內捲動瀏覽列。
- 窄螢幕（<1100px）：自動單欄堆疊（保留可用性）。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 計畫 | 本檔 |
| M2 | grid 佈局 + 表格內部捲動 + 截圖驗證 | index.html + style.css；shot-scraper 量整頁高度 |
| M3 | docs + 報告 | README 補充、本檔總結 |

## Fallback 指引

純前端 CSS/HTML 重排，不動 API/資料。回滾：`git revert <M2>`。
最差：`git reset --hard 300dc7f`（RAG dashboard M3 commit）。

## 進度日誌

### M1 — 計畫 + 基準量測 ✅
量到目前整頁高 **25,434px @1280×720**（≈35× viewport）。Commit `<M1>`。

### M2 — grid 佈局 + 表格內部捲動 ✅
- `index.html`：papers + MCP section 加 `wide` class（全寬）；3 個長表
  （papers / strat / rag-table）包進 `<div class="table-scroll">`
- `style.css`：
  - `main` 改 `display: grid; grid-template-columns: 1fr 1fr; gap: 14px`；
    全寬列用 `.cards, .wide { grid-column: 1 / -1 }`
  - `@media (max-width: 1180px)` → 單欄 fallback
  - `.table-scroll { max-height: 320px; overflow-y: auto }`，
    `thead th` 黏頂（sticky）讓表頭隨內部捲動保持可見
  - summary cards 壓緊：value 30→24, padding 16→10/14
  - `.rag-layout` 在 ≤1400px 時 sidebar 落到下方避免擠壓
- **量測結果**：整頁高 **25,434 → 1,792px**（**14× 縮減**，2.49× viewport @1280×720）
- 截圖確認：寬螢幕（1500×900）首螢一眼看到 summary+bars+runs+papers 頂部；
  捲到底見 strategies+RAG 並排 + MCP 全寬；窄螢幕（1000px）自動單欄堆疊
- panels 數量、JS、API 完全不變
Commit: `M2: compact grid layout + sticky-header table-scroll (25434px → 1792px)`

### M3 — docs ✅
README webui 段補一行新版面說明；本檔結論。

Commit: `M3: docs — note compact dashboard layout`

## 結論

純前端 CSS/HTML 重排（main → grid + 表格 wrapper），不動 API/資料/JS。
整頁高度從 35× viewport 壓到 ~2.5× viewport，寬螢幕首螢可見約 4-5 個 panel
標題，長表格不再撐爆頁面。窄螢幕自動 fallback 單欄。

## 後續方向
- 進一步：把 `main` 改 CSS Grid named areas 可細調 row 高度（例如 papers 設
  固定 row-height），達成首螢看到所有 panel 標題。
- 可加 `position: sticky` 在 topbar 與 summary cards，捲動時保持可見。
