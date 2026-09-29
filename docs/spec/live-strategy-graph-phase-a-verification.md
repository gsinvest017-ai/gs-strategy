# Live Strategy Graph — Phase A 驗收紀錄

日期：2026-09-29。範圍：任務 0–6、8、9 與本機 HTTP JSON API；不含 Phase B 編輯器。三個 agent 在核心里程碑後分別完成 TSMOM、ledger、統計節點，主 agent 整合 CLI/API/產出與回歸測試。

## 任務狀態

- [x] 0 技術選型：Hamilton、React Flow、LiteGraph 的 stars／維護／授權與 R1/R2/R5 比較，見主規格附錄 A。
- [x] 1 註冊、型別接線與參數 schema；禁止非 Backtest 產生 Returns。
- [x] 2 AST 指紋、依賴指紋、磁碟快取、增量重算與狀態。
- [x] 3 TSMOM 圖與真 Zipline futures fixture 等價／前視測試。
- [x] 4 append-only ledger、去重、取消、N 與 E[max SR]；統計不足稽核例外見下。
- [x] 5 ledger/report/facts/resolve 四節點，沿用既有判準。
- [x] 6 sidecar／manifest 圖 hash、快照還原、無 UI CLI。
- [ ] 7 Web 編輯器：依派工排除，留 Phase B。
- [x] 8 Bash／PowerShell API 啟動、loopback 綁定、忽略快取與 console log。
- [x] 9 README 使用方式；主規格附錄 B 為 API 契約。

## 實測

Windows Git Bash 建置：

```bash
bash scripts/setup-bt.sh python
.venv-bt/Scripts/python.exe -m pip install -r requirements-test.txt
PYTHONUTF8=1 .venv-bt/Scripts/python.exe -m pytest tests/ -q -rs
```

結果：**422 passed、7 skipped，47.23 秒**。七項 warnings 為 Zipline 的 Python co_lnotab 棄用警告。第一次 setup 實測因腳本假設 `.venv-bt/bin/pip` 失敗；修正 Windows Scripts 路徑後，原 requirements-bt 成功安裝 zipline-tej 2.2.2。Windows 子程序需 PYTHONUTF8=1，避免既有繁體中文 CLI 測試的編碼不一致。

| 驗收 | 實測位置／命令 | 結果 |
|---|---|---|
| R1 型別／Returns 保護／缺輸入 | `pytest tests/test_live_graph_core.py -q` | 非法接線拒絕、缺輸入及下游未就緒，上游照常執行 |
| R2 快取／增量／實作變更／重啟 | 同上；真 fixture 測試亦斷言上游 cached | 實際呼叫次數與節點狀態符合預期 |
| R3/R4 後端預覽／過期／取消 | core、api、tsmom_equivalence 測試 | preview 不跑回測；過期保留舊輸出；真 Zipline bar 內取消不記帳 |
| R5 selection 記帳 | `pytest tests/test_live_graph_ledger.py -q` | 12 passed；33→34→改回原 hash 仍 34；取消不變；triage N 一致；有效事實 audit 無問題 |
| R5 併發／append-only | 同上 | 12 threads 與 3 spawn processes 同 hash 只追加一次；舊 bytes 保留 |
| R6 事實與處方 | `pytest tests/test_live_graph_stats.py -q` | 4 passed；JB/LB p 值可重算、ESS、ledger N、原文拒答與獨立 report 分支 |
| R7 快照／manifest／CLI | api 與真 fixture 測試 | 還原 hash 相同；實作變更警告；manifest.validation.graph_hash；CLI main 實際執行同 fixture/cache 路徑 |
| R8 真 futures fixture 等價 | `pytest tests/test_live_graph_tsmom_equivalence.py -q` | fixture 非 skip，原策略預設交易參數；每日 returns 絕對差 <1e-10，逐日非零持倉完全相同 |
| PnL 獨立對帳 | 真 fixture 的原始合約 OHLC、成交、乘數、費用與 FIFO lot ledger | 隔夜＋日內－費用逐日符合 pnl；已平倉＋期末 MTM－費用符合最終權益增減，絕對容差 1e-7 |
| R8 前視／接線 | 同上 | 修改 t 後價格不改 t 以前 Weights；target_vol=0 真事件迴圈 returns/positions 歸零 |
| R9 HTTP 啟動 | 下列 Bash 與 PowerShell 指令 | 兩者均 HTTP 200，13 種節點；預設 127.0.0.1 |
| R9 錯誤／console | `pytest tests/test_live_graph_api.py -q` | 外部 console 與例外內容不外傳；拒絕跨 Origin、路徑越界、未知圖 metadata |

API 實測指令：

```bash
bash run.sh graph-api --port 19102
curl http://127.0.0.1:19102/api/node-types
# HTTP 200；node_types 數量 13
bash run.sh graph-run --help
# 正常顯示 run/serve/types 與 CLI 選項
```

```powershell
pwsh -NoProfile -File run.ps1 graph-api --port 19103
curl.exe http://127.0.0.1:19103/api/node-types
# HTTP 200；node_types 數量 13
```

新 API 測試使用暫存服務／ledger。正式 `log/trials.jsonl` 未由本次測試寫入。`.cache/live-strategy-graph/`、`.graph-runs/`、`log/codex-*` 均經 git check-ignore 確認排除。未 push；CI 工作流已加入 requirements-bt，但尚未執行遠端 CI。

## 未覆蓋與限制

- **R5 並非所有邊界情境完全達標**：零波動、觀測不足等情況已看到回測績效，必須計入 N；但 ruleset 1.1 無法對未知 autocorr/n_eff 產生可稽核處方。此時保留 purpose=selection、delta_n=1、status=pending，audit 如實回報不可稽核。正常資料的 audit 通過。不可把 pending 當作合格處方；未修改規則或捏造事實。
- `config_ref` 為既有 harness 相容 manifest 路徑；`graph_ref` 保存圖 hash 與完整快照，`config_sha256` 為圖 hash。這是規格欄位要求的相容調整。
- 真實 tquant_future 測試未執行：本機 TEJ 憑證可用性=false、production bundle 目錄可用性=false。測試需 GS_TEST_REAL_BUNDLE=1，並以獨立子程序避免 fixture 日曆污染。
- 另六個既有 skip：外部 gs_rag 套件一項，TEJ 資料依賴五項。既有測試與 skip 條件未弱化。
- fixture 使用 2016–2020 廠商靜態日曆範圍，回測區間 2018–2020；動態日曆輸入由離線 fixture 提供，orders、fills、costs、accounting 均真實 Zipline。未宣稱已驗證真實資料的 alpha 品質或策略獲利。
- Sigma 的基準預覽與 Sizing 的有效歷史視窗關係見主規格附錄 B；保留舊策略有限視窗語意，未改動 alpha 定義。

## 風險檢查

事前失敗假設為：快取遺漏依賴、取消與記帳競態、連續期貨換月／歷史調整不等價。對應證據為指紋變更與 restart 測試、取消提交共用鎖與跨程序去重、as-of DataPortal 及真事件迴圈每日比對。

反例測試涵蓋：不同資料源混接、負／非有限成本、缺輸入、未知 metadata、多 Backtest 隱藏試驗、統計未知、零權重、sidecar hash 竄改、不可用 ingestion、執行中改圖及跨 Origin 請求。主 agent 審查後限制一圖一 Backtest、鎖定 ingestion timestamp、禁止 MVP diagnostic。

此次遷移保留原 runner、strategy.py、decision.py、ruleset 1.1；經 git diff 確認均未變更。新圖不另寫績效／成交公式。fixture 另以原始合約與成交獨立核對隔夜、日內及 FIFO 損益；通過範圍僅為該合成情境，不能推論成真實市場的可交易性認證。

## 新增／修改檔案

新增：

- `strategies/_common/graph/__init__.py`
- `strategies/_common/graph/__main__.py`
- `strategies/_common/graph/core.py`
- `strategies/_common/graph/ledger.py`
- `strategies/_common/graph/stat_nodes.py`
- `strategies/_common/graph/service.py`
- `strategies/_common/graph/api.py`
- `strategies/tsmom_tx_mtx/graph_nodes.py`
- `strategies/tsmom_tx_mtx/graph.json`
- `strategies/tsmom_tx_mtx/fixture_bundle.py`
- `tests/test_live_graph_core.py`
- `tests/test_live_graph_ledger.py`
- `tests/test_live_graph_stats.py`
- `tests/test_live_graph_tsmom_equivalence.py`
- `tests/test_live_graph_api.py`
- `docs/spec/live-strategy-graph-phase-a-verification.md`

修改：

- `strategies/_common/validation/report.py`
- `scripts/setup-bt.sh`
- `run.sh`
- `run.ps1`
- `.gitignore`
- `.github/workflows/ci.yml`
- `requirements-test.txt`
- `README.md`
- `docs/spec/live-strategy-graph.md`
