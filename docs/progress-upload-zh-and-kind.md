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

（每完成一個 milestone 在下方追加 `## Mn — <title>` 段落。）
