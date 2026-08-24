---
type: progress
updated: 2026-06-02
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# 上傳功能：修中文檔名亂碼 + 可選 strategy/factor 區

## 目標

1. **修中文亂碼**：透過 file selector 上傳中文檔名 PDF 時，論文標題顯示
   mojibake（如 `ä¸­æ\x96\x87…`）。root cause：`parse_multipart` 用 `latin-1`
   解碼整個 header，但瀏覽器的 `filename="中文.pdf"` 是 UTF-8 bytes。
2. **可選 kind 區**：手動上傳時讓使用者選「策略 Strategy」或「因子 Factor」，
   上傳的論文直接歸到該區（而非只靠 title 自動分類）。

## Root cause（已重現）

`parse_multipart`：`raw_headers.decode("latin-1")` → UTF-8 中文 filename 變
mojibake → `save_upload` 用 `Path(filename).stem` 當 title → DB 存壞字。

修法：把 regex 撈到的 filename（latin-1 字串）`.encode("latin-1").decode("utf-8")`
還原成正確中文；解碼失敗則保留原值（相容純 ASCII）。

## kind 選擇設計

- 前端上傳 panel 加 `<select>`：自動分類（預設）/ 策略 / 因子。
- FormData 多帶一個 `kind` 欄位（`""` / `strategy` / `factor`）。
- `save_upload(..., kind=...)`：非空時寫 `LabelStore.set_kind(source, source_id, kind)`
  → 與既有「手動覆寫 kind」機制共用，論文立即出現在指定 tab。
- 自動分類（空）時不寫 override，沿用 `paper_class` 對 title 的判斷。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 | 本檔 |
| M2 | 修中文檔名解碼 | `parse_multipart` UTF-8 還原 + test |
| M3 | 上傳可選 kind | `save_upload`/`handle_upload` kind 參數 + server 傳遞 + 前端 select + test |
| M4 | docs + 驗證 | README、瀏覽器截圖、本檔總結 |

## Fallback 指引

- 純改 `upload.py` + server upload 分支 + 前端 panel，不動其他。
- 回滾：`git revert <M4>..<M2>`。

## 進度日誌

### M1 — 進度檔 ✅
重現中文檔名 mojibake；設計 `_fix_utf8` 還原 + kind 表單欄位。
Commit: `M1: 上傳中文亂碼 + 可選 strategy/factor 區 — 計畫`

### M2 — 修中文檔名解碼 ✅
- `upload.py` 加 `_fix_utf8(s)`：`s.encode('latin-1').decode('utf-8')` 還原，
  失敗保留原值（相容 ASCII）。`parse_multipart` 對 filename 套用。
- 測試 +2（UTF-8 中文 filename / 中文 title 落 DB 不亂碼）
Commit: `M2: 修上傳中文檔名 mojibake（latin-1→utf-8 還原 filename）`

### M3 — 上傳可選 kind + 修既有亂碼 ✅
- `save_upload(..., kind=)`：非空 kind 寫 `LabelStore.set_kind('manual', sid, kind)`
  → 與手動覆寫共用，論文直接進指定 tab；`handle_upload` 讀 `kind` 表單欄位套整批
- 前端：上傳 panel 加「歸類到」select（自動/策略/因子），app.js FormData 帶 kind
- **`scripts/fix_manual_titles.py`**：一次性修既有 DB 亂碼標題（dry-run 預設，
  `--apply` 才寫）。掃 papers，對「latin-1→utf-8 後會變且有效」的 title 還原。
  已對使用者既有 4 篇 manual 套用：`Carhart四因子` / `Fama and French 三因子` /
  `fama french 五因子`（Sharpe 1964 純 ASCII 不動）
- 測試 +3（kind override / 非法 kind 忽略 / kind 表單欄位套整批）
- **瀏覽器驗證**：上傳 panel 有 kind 下拉；papers 表第一列中文標題正確顯示；
  curl 上傳中文檔名 + factor → title 正確 + 進 factor tab
Commit: `M3: 上傳可選 strategy/factor 區 + fix_manual_titles.py 修既有亂碼`

### M4 — docs + 報告 ✅
README webui 段補 kind 選擇 + 亂碼修復工具；本檔總結。
Commit: `M4: docs — 上傳 kind 選擇 + 中文標題修復說明`

## 結論

兩個需求都完成：
1. **中文亂碼**：新上傳的中文檔名/標題正確（`_fix_utf8`）；既有亂碼用
   `scripts/fix_manual_titles.py --apply` 一次修好。
2. **kind 選擇**：上傳時「歸類到」可選策略/因子/自動，直接歸到對應 tab。

19 個 upload 測試全綠。

## 後續方向
- `_fix_utf8` 同樣可套到 RFC 5987 `filename*=UTF-8''…` 編碼（目前只處理裸 UTF-8）
- fix_manual_titles 可擴成掃全來源（目前 manual 為主，但邏輯已支援 `--source`）
