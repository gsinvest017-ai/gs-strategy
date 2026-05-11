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

**Commit**: `d9ff51c`

### M3 — 驗證安裝 ✅ (with caveat)

**做了什麼**

1. 跑 `./scripts/setup-bt.sh python3.12` 成功建出 `.venv-bt/`（python3.11/3.10/3.9 在系統上都沒有，3.12 是 zipline-tej 支援上限，可用）
2. 確認 `.venv-bt/bin/{python,pip,zipline}` 三隻 binary 都齊
3. `python -m py_compile` 把 4 支 `strategy.py` + `runner.py` + `futures_setup.py` 全部跑過，語法乾淨
4. 用 `yaml.safe_load` 載入 4 份 `config.yaml`，斷言 `bundle == 'tquant_future'` 且 `calendar` / `benchmark` 都已不存在 → 全部 PASS

**Caveat — `import zipline` 需要 TEJAPI_KEY**

驗證過程中發現 `zipline-tej` 依賴的 `exchange_calendars.exchange_calendar_tejxtai`
**在 import 時就呼叫 TEJ API** 抓最新交易日，沒設 `TEJAPI_KEY` 連
`import zipline` 都會直接丟 `AuthenticationError`：

```
File ".../exchange_calendar_tejxtai.py", line 2179
  dynamic_close_dates = get_dynamic_close_days(...)
  tejapi.errors.tej_error.AuthenticationError: (Status 404) 請輸入您的api_key
```

這是 upstream 套件的行為，不是這次改動造成。已在 `strategies/README.md`
加 `⚠️ TEJAPI_KEY 是 import-time 必要條件` 段落提醒。

**還沒做**（需要 `TEJAPI_KEY` 才能繼續）

- 實際 `zipline ingest -b tquant_future`
- 跑任一支 strategy 拿到 result.pkl
- 比對 metrics 是否合理

這些留給使用者在有金鑰的環境執行 `./scripts/ingest_futures.sh` 後驗證。

**Commit**: `8fd3319`

### M4 — `.env` + run_strategy.sh wrapper ✅

**做了什麼**

- `.gitignore`: `.env` / `.env.*` 加入忽略；`.env.example` 反向 unignore 讓 template 可追蹤
- `.env.example`: 提供 `TEJAPI_KEY` / `TEJAPI_BASE` 樣板
- `.env`: 本地填入真實 key（**不會 commit**，已用 `git check-ignore -q` 驗過）
- `scripts/ingest_futures.sh`: 自動 source `.env`；同步把預設 equity tickers `IR0001 IX0001` 拿掉（與 benchmark opt-in 一致）
- `scripts/run_strategy.sh`: 新 wrapper，照名字跑單支策略，自動 source `.env`
- `strategies/README.md`: 流程從 `export TEJAPI_KEY=...` 改成 `cp .env.example .env` + `./scripts/run_strategy.sh`

**Commit**: `b083fab`

### M5 — Ingest 通過 (含 2 個 upstream gotcha 修復) ✅

**做了什麼**

1. 第一次跑 `ingest_futures.sh` 失敗：`fetch_equity_data` 拿 `IR0001 IX0001` TEJ 回空 → pandas datetime 欄位塞 `[]` 炸
2. 讀 bundle source 確認 ticker 是 optional，改成 futures-only ingest（`EQUITY_TICKERS` 改 opt-in）
3. 第二次跑：fetch 過了，但 bcolz daily-bar 寫入 `KeyError: 0` 在 `first_session_open` → 認出是 pandas 3.0 移除 label→positional fallback
4. `pip install "pandas<3.0" "numpy>=2.0"` 降版 → 第三次跑 ingest 成功
5. 把 pin 固化到 `requirements-bt.txt`，`setup-bt.sh` 改成 `pip install -r requirements-bt.txt`

**Bundle 狀態**
- 路徑: `~/.zipline/data/tquant_future/2026-05-11T09;13;34.738913/`
- 內容: `daily_equities.bcolz` / `future_raw.parquet` / `assets-7.sqlite` 等齊全
- mdate: 20180101 ~ 20260510，futures: TX + MTX

**Commit**: 見 `M5: ...` commit

### M6 — 跑 3/4 支策略並收集 metrics ✅ (with caveat)

**做了什麼**

- 跑通 vgrsi_tx / cubic_momentum_tx / tsmom_tx_mtx，輸出 `/tmp/*_result.pkl`
- 寫 `scripts/summarize_results.py` 把 pickle 轉成 metrics 表（auto-load `.env` 因為 pickle.load 會 import zipline）
- 把結果完整寫進 `docs/backtest-results-2026-05-11.md`

**摘要**

| strategy          | CAGR  | Sharpe | Max_DD  | n_tx |
|:------------------|:------|-------:|:--------|-----:|
| vgrsi_tx          | 9.62% |  0.866 | -18.49% |  489 |
| cubic_momentum_tx | 8.87% |  0.642 | -38.64% |  870 |
| tsmom_tx_mtx      | 9.04% |  0.692 | -27.95% |  419 |

**Caveat: xsmom_stkfut_rmt 未跑**

它在 initialize 階段就需要 `CAF` 等個股期 root，bundle 沒 ingest 個股期 → 直接
`SymbolNotFound`。要跑這支策略需要：

```bash
FUTURES_ROOTS="TX MTX CAF CBF ..." ./scripts/ingest_futures.sh
```

完整個股期 root list 待 TEJ 文件對照後補。記在 `docs/backtest-results-2026-05-11.md` 的「未跑」段。

**Commit**: 見 `M6: ...` commit

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
