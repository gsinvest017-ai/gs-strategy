# 策略池切換與回測結果庫（三期計畫・第一期）

> 狀態：第一期已實作（2026-10-02）
> 相關：[`live-strategy-graph.md`](live-strategy-graph.md)、[`compositional-research-workflow.md`](compositional-research-workflow.md)

## 三期範圍

| 期 | 內容 | 狀態 |
|---|---|---|
| 一 | dashboard 策略下拉選單（策略池＝gs-zipline-tej 註冊表）＋ 每次回測自動存入結果庫 | **本文件** |
| 二 | 蒙地卡羅與多次試驗驗證：每次試驗都存，另存彙總績效分布；接入因子池與 MINT trial ledger | 待做 |
| 三 | 量化論文爬蟲排程 → LLM 依論文原文產生策略程式碼 → 通過驗證門檻才放進策略池 | 待做 |

## 介面原則

- **單一真相**：策略池就是 gs-zipline-tej 的 `dashboard.strategies.registry`。它掃描所有含 `manifest.yaml` 的 bundle，格式依 `docs/strategy-import-spec.md` v1.2，來源包括：
  - gs-zipline-tej 內建範例；
  - 本 repo 的 `strategies/`；
  - `DASHBOARD_STRATEGY_DIRS` 指定的其他目錄；
  - 經 FORGE／MINT 匯出器產生的 bundle。
- **只當介面，不改程式**：gs-zipline-tej、GSINVEST/gs-FORGE、GSINVEST/gs-MINT 都不修改。本 repo 只呼叫它們的公開函式（`registry.refresh / list_strategies / list_factors`、`runner.run_backtest`），而且一律在 `.venv-bt` 子程序裡執行。圖伺服器本身不 import zipline，外部策略崩潰也不會拖垮它。
- 子程序的輸出可能含金鑰，所以失敗時只回固定的中文訊息，不轉述原文。

## 切換規則

1. 策略自帶 `strategies/<id>/graph.json` 時，直接開那張圖，例如 `tsmom_tx_mtx`、`llm_view_tx`。
2. 其他策略開**粗圖** `strategies/_pool/<id>/graph.json`（自動產生，不進版控）：

```
data.pool_strategy ──StrategyBundle──► feature.strategy_spec ──StrategySpec──► backtest.pool_zipline ──Returns──► report / facts / resolve
        └──────────────────────────────StrategyBundle──────────────────────────┘                                ledger ─┘
```

   - `bundle_version` 是策略原始碼（`.py/.yaml/.md/.json`，不含產生出來的 graph.json）的內容 hash，由 `prepare_graph` 釘選。改一行策略碼就是新的回測組態，N+1。
   - `feature.strategy_spec` 呈現 manifest 宣告的 universe、參數、驗證產物與來源，讓 02／03 欄在拆成細節點之前也有東西可看。
   - `backtest.pool_zipline` 透過 gs-zipline-tej runner 跑真實 Zipline，報酬讀自 runner 輸出的 equity parquet。
3. fixture（測試資料）模式不可切換，因為切換會觸發真實資料回測，違反 fixture 的隔離承諾。

## 結果庫（`data/backtests.sqlite`）

- 每一次**非預覽**的執行都寫一筆 `runs`，包含被 PIT 守門拒絕或回測失敗的執行。欄位有：狀態、是否新增 selection trial、執行後的 N、模型與引擎、Sharpe／PSR／DSR／MDD／CAGR、各節點狀態、參數快照。
- `returns` 以 `backtest_key` 為鍵，每個組態只存一次。快取重播會多一筆 run，但不會重複寫報酬。
- `details` 存 walk-forward fold 表、runner 資訊與驗證報告。
- ledger（`log/trials.jsonl`）仍是 N 的唯一來源；結果庫只負責回答「每次執行產生了什麼」。
- 選用 stdlib SQLite（WAL），不新增依賴。需要分析時，可以用 DuckDB `ATTACH`。
- API：`GET /api/strategies[?refresh=1]`、`POST /api/strategies/select {id, expected_revision}`、`GET /api/results[?strategy=&limit=]`、`GET /api/results/<run_id>`。
- UI：頂列有策略下拉選單（依來源分組，因子池第二期才開放）；「結果」面板列出執行紀錄，點選可看權益曲線、驗證警告與參數快照。

## 實測（2026-10-02）

- 策略池讀到 19 支策略與 4 個因子，沒有匯入錯誤。
- 在 UI 切換到 `buy_and_hold_tw` 後按執行：真實 Zipline 回測 226 天，Sharpe 0.67；自動寫入結果庫並記為新試驗 +1。
