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
- 本輪已修正 `config_ref`：每個 Backtest 快取鍵對應 `.graph-runs/<backtest_key>.config.json`，保存首次完成組態的完整圖快照；精確 repo 相對路徑比對測試通過。
- 真實 tquant_future 測試未執行：本機 TEJ 憑證可用性=false、production bundle 目錄可用性=false。測試需 GS_TEST_REAL_BUNDLE=1，並以獨立子程序避免 fixture 日曆污染。
- 另六個既有 skip：外部 gs_rag 套件一項，TEJ 資料依賴五項。既有測試與 skip 條件未弱化。
- fixture 使用 2016–2020 廠商靜態日曆範圍，回測區間 2018–2020；動態日曆輸入由離線 fixture 提供，orders、fills、costs、accounting 均真實 Zipline。未宣稱已驗證真實資料的 alpha 品質或策略獲利。
- 本輪已修正 Sigma 預覽：節點新增 Score 輸入並使用相同有限視窗，只計算一次，Sizing 直接使用 Sigma.values；未改動 alpha 定義。

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

## Code review 單輪修正（2026-09-29）

依新版 R5，由單一 agent 依序處理；不修改 decision.py、規則集、原 strategy.py 或正式 ledger。此輪是遷移與記帳修正，不是新 alpha 或 filter，不以回測績效選參數。

| 項目 | 修正 | 對應測試 |
|---|---|---|
| 1 N 灌水 | Context.backtest_key 取 Backtest 節點實際快取鍵；ledger 以此去重，完整圖 hash 與快照仍保留 | `test_downstream_family_cached_without_new_selection_and_config_ref`；`test_r8_fixture_real_zipline_equivalence` 實際測 family 改動 cached／N 不變，target_vol=0 後 N+1 |
| 2 Sigma 預覽 | feature.ewma_vol 接收 Score.window，顯示 sizing 使用的 Sigma.values | `test_sigma_preview_is_sizing_sigma_lookback_50_skip_5`：以權重反推 sigma，並獨立對照 legacy 有限視窗 |
| 3 重複計算 | vol_target 直接使用 Sigma.values，不再呼叫 _sigma | 同上：_sigma 呼叫數為一次，視窗為 60 |
| 4 全域靜音 | 執行緒區域的 console／logging 隔離；不更動 logging.disable，worker 輸出不落地 | `test_worker_output_isolation_preserves_other_thread_errors`；`test_external_console_output_and_errors_are_not_exposed` |
| 5 domain 錯誤 | prepare_graph、節點執行及 CLI 啟動保留 GraphError／UnderdeterminedError；第三方例外遮蔽 | `test_prepare_errors_reach_job_and_cli_only_when_controlled` 的三組情境；上列 worker 測試另驗節點訊息 |
| 6 config_ref | `.graph-runs/<backtest_key>.config.json` 先原子寫入，再追加 trial；不同組態可區分，cached 不覆寫首次快照 | `test_downstream_family_cached_without_new_selection_and_config_ref`：以 triage_generated.Candidate.config_ref 精確比對 |
| 7 manifest 寫入時機 | run 只寫 sidecar；save 僅套用目前圖已完成的回測，支援重啟後讀取相符 sidecar | `test_manifest_changes_only_on_save_of_completed_graph`；`test_save_after_restart_uses_matching_completed_sidecar` |
| 8 執行期資料版本 | prepare_graph 僅操作副本；版本入快取鍵、trial 與 sidecar，不回寫文件 | `test_run_pins_runtime_version_without_dirtying_document`；`test_r8_fixture_real_zipline_equivalence` 另驗真 fixture 執行與存檔前後 graph.json bytes 相同 |
| 9 CI 說明 | 補回 Actions secret 設定、bundle 準備及 GS_TEST_REAL_BUNDLE 開關，保留離線 fixture 說明 | `test_ci_documents_optional_secret_and_fixture_coverage` |

API 附錄 B 與 README 已同步：分清文件 graph_hash 與執行 graph_hash，列出 job.message／backtest_key、sidecar.document_graph_hash、config_ref 與 manifest 存檔語意。

### 最終驗收

命令：`PYTHONUTF8=1 .venv-bt/Scripts/python.exe -m pytest tests/ -q -rs`。

最終結果：**432 passed、7 skipped、7 warnings，49.44 秒**。既有 422 個測試全部保留，新增 10 個測試案例；skip 條件未變（外部 gs_rag 一項、TEJ 依賴五項、真實 bundle 一項）。warnings 均為既有 Zipline co_lnotab 棄用警告。R8 fixture、前視檢查、獨立損益對帳及本輪所有回歸測試通過；真實 bundle 限制與 pending 統計稽核邊界仍如前述。`git diff --check` 通過；正式 ledger、decision.py、規則集及原策略未變；未 push。

### 量化自查

Pre-mortem 的三個風險為：快取／去重漏上游或資料版本、Sigma 有限視窗改變 legacy sizing、輸出隔離吞掉其他執行緒的錯誤。獨立方案以實際 Backtest 快取鍵及 Score 視窗為準，反例覆蓋下游 family 改動、資料版本更新、未執行即存檔與第三方例外。

20 條清單的本輪相關檢查通過：訊號可得時點／前視（1–5、10–11）、Sigma 定義與缺資料語意（12、15）、測試本身（19）；R8 既有獨立損益對帳覆蓋 6–9。年化、MDD、filter、branch、exit、alpha 評選（13–14、16–18、20）未修改，不把此輪 fixture 結果解讀成策略可交易性認證。
- `docs/spec/live-strategy-graph.md`

## 對抗式審查 Phase A 修正（2026-09-30）

本輪起點 `5c9a995`，以失敗反例先行修正 A1–A4，並整合 Phase B 的工作接手與共用快取鍵。完整逐條修法、測試名稱與紅綠證據見 `docs/acceptance/live-strategy-graph-phase-b.md` 的「對抗式審查與 Phase B 單輪修正」。

- A1：strategy 與其唯一的本地 import futures_setup 在私有命名空間直接編譯，避免 sys.modules 與 pyc 重用。暫存副本的同程序成本改動實測 spread 6.0→12.0；執行中依賴改動則拒絕提交與該節點快取。
- A2：配對 ingestion 後 pin 到 ingestion.isoformat()；三種等價字串實測同一backtest_key且selection_n=1。
- A3：Ljung-Box檢查10、21及依樣本數推導的最大階，ACF使用同一最大階。n=1000重現實測tested_lags=[10,21,30]，p分別約0.3667、2.8265e-46、3.1405e-44；autocorr=yes、n_eff=372、se_correction=newey_west。provenance記錄所有p值與decision_p_value；原短期p_value以p_value_lag明示，既有統計數值測試保留。
- A4：invalidate保留過期Returns對應的graph_hash，已補pytest。

量化自查：這是基礎設施修正，不是新alpha／filter。Pre-mortem涵蓋指紋與程式不一致、鎖外解析快照混用、重新整理接手競態；反例另覆蓋執行途中改檔與409工作已結束。策略時序、成本公式、PnL與規則判準未改，既有R8 fixture等價及損益對帳通過。獨立複核與主agent未留下未解決分歧。

實際執行 `$env:PYTHONUTF8='1'; .venv-bt/Scripts/python.exe -m pytest tests/ -q -rs`：**453 passed、7 skipped、147 warnings，92.94秒**。原444項通過，新增9項通過；7項外部依賴／授權資料skip條件未變。警告包含依賴套件棄用、fixture bundle重註冊與零波動統計運算，不隱藏警告或改動skip條件。R8 `test_r8_fixture_real_zipline_equivalence` 實際通過。

本輪沒有回滾；decision.py、規則集、strategy.py及正式ledger均無版控差異。差異檢查與機密模式掃描通過（僅記錄布林判準）。未push。
