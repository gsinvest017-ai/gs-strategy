# Fix: dashboard PDF links still "-" — stale server process

## 症狀

使用者選「只看本地 PDF」後，PDF 欄仍全部顯示「—」，提示卻說「有本地 PDF
**87** 筆」（87 = 全部論文數，而非已下載的 34）。

## Root cause（已證實）

執行中的 webui server 是**舊的 process**，載入的是尚未含 PDF 篩選的 server.py：

| 證據 | 值 |
|---|---|
| pdf 篩選後端 commit (`10ca620`) | 2026-05-27 **15:44:53** |
| 執行中 server (PID 529955) 啟動 | 2026-05-27 **13:34:00**（早 2 小時） |
| 舊 server `/api/papers?pdf=local` 回應 | `count:87`、**`filter` key 缺失**、`fallback_latest:True`、首列 wiley |

`http.server` 不會在檔案變動時自動 reload Python。靜態檔（index.html/app.js）
是每次 request 即時讀，所以新版下拉選單會出現；但執行中的 `server.py`/`stats.py`
仍是 process 啟動當下的版本 → 不認得 `?pdf=` → 落到 fallback 回最新全部 87 筆
→ 最上面是無 pdf 的 wiley → 顯示「—」。

新版程式碼本身正確：fresh server `?pdf=local` 回 34 筆且帶 `pdf_local`（已驗證）。

## 修正

1. **重啟** port 5057 的 server，載入現行程式碼。
2. **防再犯**：
   - `/api/summary` 加 `server_started` + `code_rev`（啟動時的 git 短 hash），
     前端 footer 顯示 → server 過期時一眼看得出。
   - `run_webui.sh` 啟動前先停掉同 port 的舊 server（restart-safe），
     避免改完碼忘了重啟。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + root cause | 本檔 |
| M2 | 版本戳記 + restart-safe + 重啟 | summary `server_started`/`code_rev`、footer 顯示、run_webui.sh 換舊 server、重啟並驗證 34/本地 + tests |
| M3 | docs + 報告 | README 註記「改碼後需重啟」、進度檔總結 |

## Fallback 指引

- 立即手動修：`pkill -f 'quant_crawler.webui'` 後 `./scripts/run_webui.sh`。
- 回滾本任務改動：`git revert <M2>`（純 server 戳記 + 啟動腳本，無資料變更）。
