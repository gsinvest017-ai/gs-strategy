# 即時策略圖（Live Strategy Graph）規格

> 狀態：草案，待確認後派工
> 相關：[`statistical-decision-tree.md`](statistical-decision-tree.md)、[`auto-research-funnel.md`](auto-research-funnel.md)
> 首個落地對象：`strategies/tsmom_tx_mtx`

---

## 0. 提案

### 為什麼要做

harness 的 trials 搜尋樹（`:9101/trials`）以「一次試驗」為節點，只能事後 replay。
研究者看不到一支策略**此刻**的參數、每一步的中間值、統計判決是怎麼推出來的。
統計決策樹（`decision.py`）本身就是一張 DAG（事實 → 五槽位 → 處方），但埋在程式裡。

本規格把節點單位從「試驗」換成「策略的一個運算步驟」，借用 ComfyUI 的四個機制：

1. **型別化接點**：接錯型別接不上；缺輸入的節點會亮紅燈並說明原因。
2. **增量重算**：以內容 hash 快取，只重算參數被改動之後的下游節點。
3. **workflow 即資料**：圖（接線＋參數）是一份 JSON，嵌進每一份回測產出，拖回來就能重現。
4. **節點是程式碼、接線是資料**：節點實作是 repo 內經 review 的 Python 函式；接線與參數在圖檔裡。

### 最重要的約束：即時介面不得成為 p-hacking 機器

`auto-research-funnel.md` §1 已算過：N 從 33 增加到 382，E[max SR] 會上升 40.6%，而且這個門檻是全域的。
能即時拉滑桿的介面若不記帳，N 會在沒人察覺的情況下暴增。所以本規格把
`stat-ruleset-1.1.yaml` 的 `purpose` N 記帳規則做成 UI 的**機械行為**，不靠研究者自律。

### 範圍

**MVP（本規格）要做：**
- 圖的定義格式、型別系統、執行引擎（含 hash 快取）
- 本機 Web 編輯器：看圖、改參數、看每個節點的即時輸出
- `tsmom_tx_mtx` 改寫成第一張圖，回測結果須與現行 `strategy.py` 等價
- Backtest 執行自動寫入 trial ledger（`log/trials.jsonl`），N 與 deflation 門檻常駐顯示
- 統計決策樹做成可視節點（Facts → Resolver 五槽位 → Prescription）
- 產出（validation sidecar、manifest）嵌入圖 hash 與圖快照

**MVP 不做（第二階段）：**
- production 模式：即時報價 Data 節點、下單節點、drift 監控節點
- diagnostic 模式（反應面掃描），規則見 §5；它會改變 N 記帳，須連同規則集 1.2 一起修訂
- PBO / CPCV 節點（需要多組試驗矩陣）
- 其他三支策略（`vgrsi_tx`、`cubic_momentum_tx`、`xsmom_stkfut_rmt`）的遷移
- 任意新增節點類型的 UI（MVP 只能在已註冊的節點之間接線）

**不改：**
- `runner.py` 的既有 `--strategy/--config` 路徑照常可用，現有策略不受影響
- `decision.py` 與規則集 1.1 的判準與輸出

---

## 1. 名詞

| 名詞 | 定義 |
|---|---|
| 節點類型（node type） | 一個已註冊的 Python 函式，宣告輸入／輸出接點型別與參數 schema |
| 圖（graph） | 節點實例、參數值、接線的集合，存成 `strategies/<id>/graph.json` |
| 圖 hash | 對「節點類型 id ＋節點實作程式碼指紋 ＋參數 ＋接線 ＋資料區間」正規化後取的 hash |
| 節點 hash | 該節點自身（類型、實作指紋、參數）加上所有上游節點 hash 的組合，作為快取鍵 |
| 上游預覽區 | Backtest 節點上游的所有節點（Data / Feature / Signal / Sizing / Cost） |
| 試驗區 | Backtest 節點及其下游（Validation / Facts / Resolver） |

---

## 2. 節點與型別（MVP：tsmom_tx_mtx）

| 節點類型 | 參數 | 輸入 | 輸出 |
|---|---|---|---|
| `data.futures_bars` | bundle, roots, start, end | — | `Bars` |
| `data.continuous` | — | `Bars` | `ContinuousBars` |
| `feature.signed_momentum` | lookback, skip | `ContinuousBars` | `Score` |
| `feature.ewma_vol` | vol_com | `ContinuousBars` | `Sigma` |
| `signal.direction` | allow_short | `Score` | `Direction` |
| `sizing.vol_target` | target_vol | `Direction`, `Sigma` | `RawWeights` |
| `sizing.gross_cap` | max_gross_leverage | `RawWeights` | `Weights` |
| `cost.futures` | per_contract_cost, spread_points | — | `CostModel` |
| `backtest.zipline` | capital_base, calendar, days_before_close | `Weights`, `CostModel` | `Returns`, `Positions` |
| `ledger.selection_n` | — | — | `LedgerN` |
| `validation.report` | — | `Returns`, `LedgerN` | `Report` |
| `stat.facts` | estimand, design, overlap, family, purpose, holding_periods | `Returns` | `Facts` |
| `stat.resolve` | ruleset_version | `Facts`, `LedgerN` | `Prescription` |

參數預設值一律取自現行 `strategies/tsmom_tx_mtx/config.yaml`。
節點怎麼拆、函式放哪裡由實作決定；上表規定的是**使用者在畫面上看到的節點與接點**。

---

## 3. 需求

### R1 型別化接線

- **需求**：系統 MUST 拒絕型別不相容的接線，並在 UI 上即時標示。
  - **情境**：GIVEN 編輯器開著 tsmom 圖 → WHEN 把 `feature.ewma_vol` 的 `Sigma` 輸出拖到 `signal.direction` 的 `Score` 輸入 → THEN 接線不成立，游標／接點顯示不相容提示，圖檔內容不變。
  - **判準**：型別檢查單元測試全綠；載入含非法接線的 `graph.json` 時回報錯誤並指出哪條線，不得靜默丟棄。

- **需求**：型別 `Returns` MUST 只能由 `backtest.*` 節點產生。
  - **理由**：確保上游預覽區不可能算出任何績效數字（N 記帳的前提，見 R5）。
  - **情境**：GIVEN 一個 Feature 節點類型宣告輸出 `Returns` → WHEN 註冊該節點類型 → THEN 註冊失敗並說明原因。
  - **判準**：對應測試全綠。

- **需求**：必要輸入未接的節點 MUST 顯示為「未就緒」並列出缺哪個接點，不得以預設值補上執行。
  - **情境**：GIVEN 把 `sizing.vol_target` 的 `Sigma` 輸入線刪掉 → WHEN 執行 → THEN 該節點與其下游標示未就緒，訊息寫明缺 `Sigma`，其餘上游節點照常顯示結果。

### R2 增量重算與快取

- **需求**：改動某節點參數後，系統 MUST 只重算該節點及其下游；上游節點 MUST 命中快取。
  - **情境**：GIVEN tsmom 圖已完整跑過一次 → WHEN 把 `sizing.vol_target.target_vol` 由 0.15 改為 0.10 並執行 → THEN `data.*`、`feature.*`、`signal.direction` 顯示「快取」，`sizing.*`、`backtest.zipline` 及下游顯示「已重算」。
  - **判準**：執行引擎測試斷言各節點的實際執行次數；UI 上每個節點都有狀態標記（快取／執行中／已重算／錯誤／未就緒）。

- **需求**：節點實作的程式碼改變時，快取 MUST 失效。
  - **情境**：GIVEN `feature.signed_momentum` 已有快取 → WHEN 修改其實作函式本體（不含 docstring／註解）→ THEN 下次執行時該節點與下游重算。
  - **判準**：對應測試全綠。程式碼指紋的正規化方式須與 `scripts/triage_generated.py` 的 AST 指紋一致（去 docstring）。

- **需求**：快取 MUST 存在磁碟上，重開伺服器後仍然有效；快取目錄 MUST 在 `.gitignore` 內。

### R3 即時預覽

- **需求**：上游預覽區的節點在參數改動後 SHOULD 自動重算並更新預覽，不需按「執行」。
  - **情境**：GIVEN 編輯器開著 → WHEN 拖動 `feature.signed_momentum.lookback` 滑桿 → THEN 該節點與下游的上游預覽區節點更新預覽（防抖處理，拖動中不得堆積重算），`backtest.zipline` 不會被觸發。

- **需求**：每個節點 MUST 在節點卡片上顯示其輸出的精簡預覽：
  - 時間序列型別（`Bars`、`Score`、`Sigma`、`Weights` 等）：最近區間的 sparkline 加上最新值
  - `Returns`：權益曲線
  - `Report`：Sharpe、PSR、DSR、MDD、CAGR，以及 `warnings`
  - `Prescription`：五個槽位（base / se / primary / threshold / gates）各自的結果與 `rule_id`
  - 點開節點 SHOULD 看到完整圖表與原始數值表

### R4 明確執行（ComfyUI 的 Queue）

- **需求**：`backtest.zipline` MUST 只在使用者按下「執行」時才跑，參數變動不得自動觸發。
  - **理由**：每次回測都可能讓 N 加 1（R5），自動觸發等於拖一次滑桿就燒掉一堆 N。
  - **情境**：GIVEN 改了 `sizing.gross_cap.max_gross_leverage` → WHEN 尚未按執行 → THEN Backtest 以下的節點標示「過期」，顯示的是上一次的結果並清楚標註它對應的是舊參數。

- **需求**：回測執行中 MUST 顯示進度與可取消；取消的執行 MUST 不寫入 ledger。

### R5 N 記帳（核心約束）

- **需求**：每一個**新的**圖 hash 第一次成功跑完 `backtest.zipline`，系統 MUST 自動在 `log/trials.jsonl` 追加一筆 `purpose: selection` 的 trial 記錄，`stat_decision.delta_n = 1`。使用者 MUST NOT 能關閉這個行為。
  - **情境**：GIVEN ledger 上 selection N = 33 → WHEN 以一組從未跑過的參數執行回測 → THEN ledger 多一筆記錄，畫面上的 N 變為 34，deflation 門檻（E[max SR]）同步更新。
  - **判準**：整合測試以暫存 ledger 驗證；`decision.audit_ledger` 對新記錄稽核無問題；`scripts/triage_generated.py` 的 `count_existing_selection_trials` 讀出的 N 與畫面一致。

- **需求**：同一個圖 hash 重跑 MUST 命中快取、MUST NOT 追加記錄（與 funnel L0「同組態重跑不產生新資訊」一致）。
  - **情境**：GIVEN target_vol 從 0.15 改成 0.10 並執行（N+1）→ WHEN 改回 0.15 並執行 → THEN 直接取快取結果，N 不變。

- **需求**：上游預覽區的所有運算 MUST NOT 寫入 ledger（相當於 funnel 的 L0–L2，ΔN = 0）。

- **需求**：畫面 MUST 常駐顯示：目前 selection N、對應的 E[max SR]、本次 session 已新增的 N。
  E[max SR] 的計算 MUST 與 `scripts/triage_generated.py` 的 `expected_max_sharpe` 相同。

- **需求**：ledger 為 append-only，系統 MUST NOT 修改或刪除既有行。

- **需求**：trial 記錄 MUST 含 `config_ref`（指向圖 hash 與圖快照）、`ruleset_version`、`decision_path`、`rule_id`，格式與 `decision.py` 的 `Prescription.to_record()` 相容，且能被 harness 的搜尋前沿以 `config_ref` 比對為「已嘗試」。

### R6 統計決策樹可視化

- **需求**：`stat.facts` MUST 由 `Returns` **自動算出**可重算的事實（Jarque-Bera → `normal`、Ljung-Box → `autocorr`、有效樣本數 → `n_eff`），宣告型事實（estimand、design、overlap、family、purpose、holding_periods）由節點參數提供；`n_trials` MUST 來自 `LedgerN`，不得手填。
  - **情境**：GIVEN tsmom 回測完成 → WHEN 看 `stat.facts` 節點 → THEN 每個自動事實旁邊顯示其來源檢定與 p 值。

- **需求**：`stat.resolve` MUST 呼叫既有的 `decision.resolve`，不得另寫一套判準；`UnderdeterminedError` MUST 讓節點亮紅燈並原文顯示補救訊息（例如「請先跑 Ljung-Box」）。
  - **情境**：GIVEN `stat.facts` 無法判定 `autocorr` → WHEN 解析 → THEN `stat.resolve` 顯示紅燈、訊息，不產生處方；`validation.report` 不受影響照常顯示。

- **需求**：`stat.resolve` 卡片 MUST 將五個槽位分開呈現，每個槽位標示「由哪個事實決定」，`forbids` 清單必須顯示出來（例如成對設計禁用獨立雙樣本 t）。

### R7 圖檔與可重現性

- **需求**：圖 MUST 存成 `strategies/<id>/graph.json`，內容為人類可讀、可 diff 的 JSON（固定鍵序、固定縮排），進 git 版控。UI 的「存檔」寫回此檔；未存檔的修改 MUST 有明顯標示。

- **需求**：每次回測產出的 validation sidecar MUST 內嵌圖 hash 與完整圖快照；`manifest.yaml` 的 validation 區塊 MUST 記錄圖 hash。
  - **情境**：GIVEN 一份三週前的 sidecar → WHEN 在編輯器「從產出載入」→ THEN 還原出當時的圖（參數與接線），且圖 hash 與 sidecar 記錄相同；若當時的節點實作指紋與現行程式碼不同，MUST 明確警告「節點實作已變更，無法保證重現」。

- **需求**：圖 MUST 能在無 UI 的情況下以 CLI 執行（例如 `runner` 新增 `--graph` 參數，或獨立指令），行為與 UI 執行相同，包括 R5 的 ledger 記帳。

### R8 與現行策略等價（遷移正確性）

- **需求**：tsmom 的圖版本在相同資料、相同參數下 MUST 與現行 `strategies/tsmom_tx_mtx/strategy.py` 產出相同的回測結果。
  - **情境**：GIVEN 同一份 `tquant_future` bundle、`config.yaml` 預設參數 → WHEN 分別以舊路徑（`runner --strategy --config`）與圖路徑執行 → THEN 每日 `returns` 序列逐點差異的絕對值 < 1e-10，每日持倉口數完全一致。
  - **判準**：等價測試全綠；若因 bundle 需要 TEJ 金鑰而無法在 CI 執行，MUST 在本機跑過並將比對摘要（僅統計量，不含金鑰與帳務資訊）附在交付回報裡，CI 端以 fixture 資料跑同一條比對。

- **需求**：權重 MUST 只使用當根 K 棒收盤前可得的資料，並在下一根執行（與現行 `handle_data` 的時序相同）。
  - **判準**：一個前視偵測測試：把第 t 天之後的價格竄改掉，第 t 天（含）以前的 `Weights` 必須完全不變。

### R9 執行環境

- **需求**：伺服器 MUST 預設只綁 `127.0.0.1`；MUST 能用 `run.sh` / `run.ps1` 的一個子指令啟動，Windows 與 Linux 皆可運作。
- **需求**：回測以 CPU 執行（zipline 事件迴圈是強序列相依，不適用 GPU）。
- **需求**：任何 log、錯誤訊息、sidecar、UI 顯示 MUST NOT 包含金鑰或個資（例如 TEJ 金鑰）；在回報與程式註解中發現個資時，只寫到類別層級，不寫出種類、樣本、格式、次數、行號。

---

## 4. 任務清單（派工用）

- [ ] 0. `/survey-first`：評估現成的 Python DAG／快取框架（如 Apache Hamilton）與前端節點編輯器（如 React Flow），決定採用或自建，結論寫進本檔附錄
- [ ] 1. 節點類型註冊、型別系統、參數 schema（R1）
- [ ] 2. 執行引擎：hash 快取、程式碼指紋、增量重算、節點狀態（R2）
- [ ] 3. tsmom 拆成節點，`graph.json` 與等價測試、前視測試（R8）
- [ ] 4. ledger 記帳與 N／E[max SR] 計算（R5）
- [ ] 5. `stat.facts` / `stat.resolve` / `validation.report` 節點（R6）
- [ ] 6. sidecar／manifest 嵌入圖 hash 與快照，CLI 執行路徑（R7）
- [ ] 7. Web 編輯器：畫布、接線、預覽、執行／取消、存檔、從產出載入（R1–R4、R7）
- [ ] 8. `run.sh` / `run.ps1` 啟動子指令、`.gitignore` 快取目錄（R9）

檔案切分與哪些項目可平行，派工時由 Claude 依實際檔案範圍宣告。

---

## 5. 第二階段預告（本 MVP 不實作，但介面必須留路）

- **production 模式**：只替換 `data.futures_bars` 為即時報價節點、`backtest.zipline` 為下單節點，中間節點不變。
  MVP 的 Data 節點輸出型別 MUST 設計成可被即時來源替換（同一型別）。
- **drift 節點**：比對即時的 `Score` / `Sigma` / `Weights` 與回測期間的分佈，偏離時亮燈。
- **diagnostic 模式**：必須在執行前宣告一組參數網格，結果只以反應面呈現；日後若有 selection trial 採用了該網格內的值，
  N 須追加整個網格的大小（看過 k 個選項再挑一個，等同 best-of-k）。這會改變 N 記帳規則，
  所以 MUST 與 `stat-ruleset-1.2` 一起修訂，不得單獨在程式裡實作。

## 附錄 A：技術選型（Phase A，2026-09-29）

GitHub API 當日快照；stars 不是品質保證，維護狀態以最後 push 及 archived 為依據。

| 候選 | Stars | 最近 push | License | R1 / R2 / R5 | 判定 |
|---|---:|---|---|---|---|
| [Apache Hamilton](https://github.com/apache/hamilton) | 2,601 | 2026-09-29 | Apache-2.0 | Python 型別 DAG / 支援快取 / 需自訂不可繞過記帳 | build |
| [React Flow / xyflow](https://github.com/xyflow/xyflow) | 38,537 | 2026-09-24 | MIT | 可自訂接點驗證 / 狀態顯示需後端 / 記帳需後端 | partial：Phase B 採用畫布 |
| [LiteGraph](https://github.com/jagenjo/litegraph.js) | 8,158 | 2024-08-01 | MIT | 接點與 JSON 完整 / JavaScript 執行非 Python / 記帳需後端 | 不採用 |

三者皆未 archived。Hamilton 適合由 Python 函式宣告資料依賴，但本案需要由固定節點白名單載入使用者 JSON 接線、隔離預覽與明確回測、將取消與 ledger 提交序列化。採用它仍須包覆上述生命週期。MVP 僅十三種節點，選擇 stdlib 小型執行核心，避免雙重 DAG 狀態；代價是自行維護快取與排程測試。實作使用與 triage 相同的 AST 去 docstring 正規化，並把明示 helper 依賴納入指紋。

React Flow 僅採用 Phase B 畫布、互動接點與自訂卡片；所有型別驗證、回測授權邊界與 R5 仍以 Python 為唯一真相。LiteGraph 最後更新較早，且內建 JavaScript 執行器與本案 CPU Zipline 事件迴圈重複，無採用優勢。

### 核心契約

`strategies._common.graph`：`NodeType(id, inputs, outputs, params, function, dependencies=(), cacheable=True)`；函式接受 `(inputs, params, context)` 並回傳依輸出接點命名的 dict。參數 schema 使用 JSON Schema 的 type/default/minimum/maximum/enum 子集。helper 函式或 Python 模組 Path 必須列入 dependencies。

圖格式為 `schema: live-strategy-graph/1`、`nodes: [{id,type,params}]`、`edges: [{from:[node,port],to:[node,port]}]`。固定鍵排序與兩格縮排。接點名稱使用規格型別名稱（例如 `Returns`）。節點 hash 含實作、參數及上游 hash；圖 hash 含正規化圖與所有實作指紋。資料來源必須將資料版本納入參數以避免 bundle 更新後重用舊快取。

`Context` 提供 token、ledger、services、progress。成功 Backtest（含快取重播）必經 `ledger.record_success(graph_hash,snapshot,outputs,context)`；取消與提交共用鎖。ledger 節點為非快取外部來源，完整執行時在回測提交後取樣，讓報告使用最新 N。統計失敗不阻擋已成功回測記帳。HTTP 不接收任意 Python 或 pickle。
