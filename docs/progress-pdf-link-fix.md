# Fix: Dashboard PDF hyperlinks all show "-"

## 症狀

使用者回報：dashboard「新增資料」面板裡，所有論文的 PDF 欄都顯示 `—`，
看不到已下載 PDF 的本地連結。

## Root cause（已重現，非臆測）

1. 前端 papers 面板查的是「指定日期 fetched 的論文」，預設日期 = 今天
   (`#runs-date` 預設今天)。
2. 但 `data/papers.db` 87 篇**全部** `fetched_at = 2026-05-10`，今天 (2026-05-27)
   沒有任何新增 → `new_papers_on(today)` 回 0 筆。
3. 前端 fallback 改顯示 `latest_papers(15)`（依 `fetched_at DESC, published DESC`）。
4. 這最新 15 筆**剛好全是 wiley 論文，且 wiley TOC RSS 不提供 `pdf_url`** →
   `pdf_local` 與 `pdf_url` 都空 → 前端邏輯落到 `—`。
5. 真正有本地 PDF 的 2 篇 arxiv（`2605.05089` / `2605.04004`）在排序中位於
   **rank 53-54**，遠超出顯示的 15 筆，使用者永遠看不到。

驗證指令（重現）：
```
curl -s "http://127.0.0.1:5099/api/papers?limit=15" → 15 筆全部 wiley, pdf_url 空
curl -s "http://127.0.0.1:5099/api/papers?limit=100" → rank 53/54 才是有本地 PDF 的 arxiv
```

→ 這不是 `pdf_local` 計算錯誤（機制本身正確，M4 已驗證），而是**可見性問題**：
下載 PDF 的論文不在預設顯示的子集內。

## 修正方向

讓使用者能跨「全部論文」篩出有 PDF 的：

1. **後端**：`/api/papers` 加 `pdf=local|any` 篩選參數（跨全部論文、忽略日期），
   `stats.list_papers()` 統一查詢 + 篩選 + 限量；`summary` 加 `pdfs_downloaded`
   （`data/pdfs/` 內 .pdf 檔數）。
2. **前端**：papers 面板加篩選下拉（全部 / 有任意 PDF / 只本地 PDF）；
   選非「全部」時跨全部論文查；summary 加「已下載 PDF」卡片。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + root cause | 本檔 |
| M2 | 後端篩選 + 計數 | `stats.list_papers` / `pdfs_downloaded`、`/api/papers?pdf=` + tests |
| M3 | 前端篩選器 + 卡片 + 驗證 | 篩選下拉、已下載卡、瀏覽器截圖、README/docs |

## 進度日誌

### M1 — root cause ✅

重現確認：今日無新增 → fallback 最新 15 筆剛好全是無 pdf_url 的 wiley；
有本地 PDF 的 2 篇 arxiv 在 rank 53-54，超出顯示範圍。非 pdf_local 計算 bug，
是可見性問題。Commit `<M1>`。

### M2 — 後端篩選 + 計數 ✅

- `stats.list_papers(date, limit, pdf)`：`pdf=local|any` 時跨全部論文掃描
  （忽略日期），附 pdf_local 後在 Python 端篩選
- `stats.pdfs_downloaded()`：數 `data/pdfs/*.pdf`（排除零位元組）
- `summary` 加 `pdfs_downloaded`
- `/api/papers?pdf=local|any` 路由參數
- tests：list_papers local/any/date、pdfs_downloaded、summary 欄位、
  server `pdf=local|any` route — 全綠
- live 驗證：`pdf=local` 回 2 篇 arxiv 本地檔；`pdfs_downloaded=2`

Commit: `M2: papers PDF filter (any/local) + pdfs_downloaded summary count`

### M3 — 前端篩選器 + 卡片 ✅

- papers 面板加「PDF」篩選下拉（全部依日期 / 有 PDF / 只看本地 PDF）；
  選非「全部」時跨全部論文查 `?pdf=` limit 300
- summary 加「已下載 PDF」卡（值 = pdfs_downloaded）
- 無新增日的 fallback hint 補上「有本地 PDF 的論文請用上方 PDF 篩選器」
- **瀏覽器截圖驗證**：選「只看本地 PDF」後，2 篇 arxiv 正確出現且 PDF 欄為
  「本地」連結（不再是「-」）；卡片顯示已下載 PDF 2

Commit: `M3: papers PDF filter dropdown + downloaded-PDF card`

## 結論

PDF 欄顯示「-」不是 bug 而是可見性：下載的 PDF 對應論文不在預設（今日/最新15）
顯示範圍內。加 PDF 篩選器（跨全部論文）+「已下載 PDF」卡片後，使用者選
「只看本地 PDF」即可看到所有已下載 PDF 的本地連結。

## Fallback 指引

純前端 + 唯讀 API 變更，無資料寫入。回滾：`git revert <M3>..<M2>`，
或 `git reset --hard f39b774`（前一任務 M5 commit）。

## 後續方向

- 可考慮把 papers 面板預設改成「有 PDF」而非「今日新增」，讓有資料的連結
  第一眼就看得到（目前預設仍是日期視圖 + fallback 最新 15）。
- 下載更多 PDF：`quant-crawl fetch-pdfs`（34 篇有 pdf_url，目前下載 2）。
