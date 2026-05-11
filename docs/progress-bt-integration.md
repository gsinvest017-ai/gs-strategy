# Backtest Integration Progress

> 把 `strategies/` 接到 `gs-zipline-tej` 期貨回測框架，最小改動把 4 支策略跑起來。

## 目標

不重寫策略碼，透過 4 個小改動讓 `strategies/{vgrsi_tx,cubic_momentum_tx,tsmom_tx_mtx,xsmom_stkfut_rmt}/` 能直接在 `tquant_future` bundle 上跑 backtest。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 修正預設值 | `runner.py` calendar 預設改 `TEJ_morning_future`；`futures_setup.py` benchmark 改 opt-in；4 份 `config.yaml` 移除錯誤的 calendar / benchmark 行 |
| M2 | 工具腳本 | `scripts/setup-bt.sh`（建立 `.venv-bt`）+ `scripts/ingest_futures.sh`（包 TEJAPI 設定） + `strategies/README.md` 流程說明 |
| M3 | 驗證安裝 | 實際建立 `.venv-bt/`，確認 `import zipline` 成功，runner.py 在沒有 TEJAPI_KEY 時能 import 不炸（不需要實際跑回測） |

## 進度日誌

### M1 — 修正預設值 ✅

**做了什麼**

- `strategies/_common/runner.py`: 預設 calendar 從 `TEJ_XTAI` → `TEJ_morning_future`（`tquant_future` bundle 的 calendar alias）
- `strategies/_common/futures_setup.py`: `apply_taiwan_futures_costs()` 把 `set_benchmark()` 改成 opt-in（`benchmark` 為 None / 空字串時不呼叫），避免 `tquant_future` bundle 找不到 IR0001 而炸
- 4 份 `config.yaml`: 移除 `calendar: TEJ_XTAI`（讓 runner 用 default）+ 移除 `benchmark: IR0001`（防止 SymbolNotFound）；留下註解說明為何拿掉

**為何這樣改**

預設值改完後，跑 backtest 不再需要每次手動覆寫；想要對標 IR0001 的場景仍可在 config.yaml 加回 `benchmark: IR0001`（同時也要 ingest `tquant` bundle）。

**Commit**: `0fcda98`

### M2 — 工具腳本與 README ✅

**做了什麼**

- `scripts/setup-bt.sh`: 建立 `.venv-bt/` (預設 python3.11)，裝 `zipline-tej` + `pyyaml`；可重入（已存在的 venv 直接 reuse）
- `scripts/ingest_futures.sh`: 包好 TEJAPI_KEY 檢查 + 期貨/股票/日期 env 預設，呼叫 `.venv-bt/bin/zipline ingest -b tquant_future`
- `strategies/README.md`: 改寫「執行流程」段，從手動 `pip install` 一長串改成 3 步 (`setup-bt.sh` → `ingest_futures.sh` → 直接呼叫 `runner.py`)；新增「Calendar / Benchmark 預設」說明區塊

**為何用獨立 venv**

避開 zipline-tej 對 numpy/pandas 嚴格 pin 與 crawler 既有 `.venv/` 衝突；兩個 venv 各自重建都很快。

**Commit**: 見 `M2: ...` commit

## Fallback 指引

任務拆成 3 個 commit，每個都獨立可回滾：

- 想退回 M1 之前：`git revert <M1 commit>` — 還原 4 個檔案的預設值
- 想退回 M2 之前：刪除 `scripts/setup-bt.sh`、`scripts/ingest_futures.sh`，revert `strategies/README.md`
- 想退回 M3 之前：`rm -rf .venv-bt/`（這個 milestone 不會動 repo 內檔案，只建 venv）

最差情況：`git reset --hard <task 開始前的 commit>`，再 `rm -rf .venv-bt/`，回到完全乾淨狀態。

## 相關檔案

- `strategies/_common/runner.py` — 編輯
- `strategies/_common/futures_setup.py` — 編輯
- `strategies/{vgrsi_tx,cubic_momentum_tx,tsmom_tx_mtx,xsmom_stkfut_rmt}/config.yaml` — 編輯
- `scripts/setup-bt.sh` — 新增
- `scripts/ingest_futures.sh` — 新增
- `strategies/README.md` — 編輯
