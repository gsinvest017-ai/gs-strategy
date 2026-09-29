# Live Strategy Graph — Phase B 驗收

日期：2026-09-29。分支：`dev/live-strategy-graph-spec`。範圍為規格任務 7 與必要的新增 API；未改策略訊號、成交、成本或統計判準，未 push。

## 任務狀態

- [x] M5：先固定附錄 B 的 session／run-estimate／layout 介面契約。
- [x] M6：新增後端端點、同源靜態服務及隔離 fixture，補 pytest。
- [x] M7：React／React Flow／Vite 編輯器、離線字型、型別接點與節點卡片。
- [x] R3／R4：300ms preview 防抖及取代舊工作，明確執行、進度、取消、舊結果過期。
- [x] R5／R6：常駐 N 儀表與預判，Report／Facts／五槽處方及錯誤原文。
- [x] R7：dirty、存檔、獨立 layout、sidecar 還原與指紋警告。
- [x] 啟動器：來源指紋判斷 build 是否過期，Windows／Git Bash 指令、README、忽略產物。
- [x] M8：完整後端回歸、前端單元測試、真 server e2e、雙啟動指令與截圖驗收。

## 實測

所有 fixture 使用真 Phase A 合成期貨 bundle、真 Zipline 訂單／成本／損益事件迴圈。每次 UI 啟動使用不同系統暫存工作區，正式 ledger 不變；測試不 mock API。

| 項目 | 指令 | 結果 |
|---|---|---|
| 完整後端回歸 | `$env:PYTHONUTF8='1'; .venv-bt/Scripts/python.exe -m pytest tests/ -q -rs` | 444 passed、7 skipped；88.83 秒。原 432 項保留，新增 12 項全過 |
| 前端單元測試 | UI 目錄執行 `npm test` | 7 passed |
| 正式 build | UI 目錄執行 `npm run build -- --logLevel warn` | 成功 |
| 真 server e2e | UI 目錄執行 `npm run test:e2e` | 8 passed；約 1.3 分鐘，全部無外部請求 |
| Git Bash fixture 啟動 | `bash run.sh graph-ui --fixture --port 19104` | 過期 build 指紋觸發 npm ci＋build；印出 `http://127.0.0.1:19104` |
| PowerShell fixture 啟動 | `./run.ps1 graph-ui --fixture --port 19105` | 跳過最新 build；印出 `http://127.0.0.1:19105` |
| 首頁 | `curl.exe -s -o NUL -w 'HTTP %{http_code}' http://127.0.0.1:19104/` | HTTP 200；19105 同樣 HTTP 200。測試服務已停止 |

e2e 覆蓋：

1. 真拖曳 Sigma → Score，顯示型別錯誤，接線與 graph hash 不變。
2. 真拖動 lookback 滑桿，上游更新、沒有 POST run、N 不變。
3. 新組態 N+1，Report／Facts／Prescription 有實際內容；第二次回放 N 不變。
4. 真回測執行中取消，狀態過期、N 不變。
5. 真拖動節點，layout 有改變，dirty／hash／預判均不變。
6. 改參數但不執行，Backtest 及下游保留舊結果並標過期。
7. sidecar 還原精確參數與快照 hash；抽屜圖表超過單頁資料、有 tooltip、原始表 offset 分頁。
8. 事實不足時處方卡顯示原文補救訊息，不顯示舊處方；Report 不受影響、N 不增加。

所有情境逐一檢查瀏覽器請求只指向 `http://127.0.0.1:19102`，並檢查 CSP／未捕捉錯誤。完成狀態另斷言 13 張卡片皆完整位於 1280×800 視窗、無重疊，N 邊界標籤可見。

驗收截圖：系統暫存目錄 `live-strategy-graph-fixture-1280x800.png`，不入版控。

## 風險與複核

Pre-mortem 的三項風險及證據：

- N 預判與實際資料版本不一致：新增 pytest 比對預判鍵與真回測鍵，測下游參數不影響鍵、缺輸入與不可快取上游拒絕預判。
- preview／載入／執行競態：單元測試覆蓋防抖、取消順序與取代；UI 同步提交鎖防止載入／執行期間參數混入；preview 尚未回 job ID 時等待 ID 再取消。
- fixture 污染正式資料：graph、layout、bundle、cache、sidecar、ledger 全放不同暫存 root，禁止 root／ledger／cache 覆寫，並測取消不記帳與啟動失敗清理。

獨立唯讀複核與主 agent 的共識：Backtest 鍵公式和既有引擎一致，layout 與圖身份分離。複核指出的啟動失敗遮罩／清理、執行與 sidecar 提交窗口、舊取消覆寫新 job、preview 啟動窗口均已修正；沒有未解決的審查分歧。

初始圖非法接線另以真 HTTP 測試確認：UI 仍啟動，graph/load 回覆 400 與原文接線索引。第三方例外仍遮罩。機密變更掃描僅輸出布林判準，結果 PASS；正式 ledger 沒有版控差異。

量化檢查界線：本次是既有策略的工程介面，不是新 alpha／filter，不宣稱 fixture 的績效有交易意義。訊號時序、PnL、成本及資料對齊沿用 Phase A，以原有前視、真 Zipline 等價、overnight／intraday 損益一致性測試防回歸。

## 檔案清單

- 規格與紀錄：`docs/spec/live-strategy-graph.md`、本檔。
- 後端：`strategies/_common/graph/{__main__.py,api.py,ledger.py,service.py,fixture.py}`。
- 前端：`strategies/_common/graph/ui/{package.json,package-lock.json,index.html,vite.config.js,src/main.jsx,src/model.js,src/model.test.js,src/style.css}`。
- 版面：`strategies/tsmom_tx_mtx/graph.layout.json`；初始空座標啟用動態排版，拖曳後存入具體座標。
- 測試：`tests/test_live_graph_phase_b.py`、`tests/e2e/{playwright.config.cjs,graph.spec.cjs}`。
- 整合：`scripts/build_graph_ui.py`、`run.sh`、`run.ps1`、`.gitignore`、`README.md`。

## 限制

既有依賴外部套件／授權 bundle 的測試依原條件跳過，沒有刪減或弱化測試。Phase A 對「成功回測但統計不足」的 pending 稽核邊界不變，詳見附錄 B。

Phase B 範圍內沒有未完成項目。本機是 Windows，已實測 Git Bash 與 PowerShell；沒有原生 Linux 執行環境可供實測。

首次 npm 安裝與瀏覽器安裝需要套件來源；完成 build 後的 UI 執行不需外網。schema 未給 maximum 的數字參數，其滑桿視窗由 minimum／default 推導並可擴張，數字輸入不另加人為上限。完整來源事實、warnings 與 forbids 可在卡片捲動區／檢視抽屜閱讀。
