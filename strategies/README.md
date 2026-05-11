# Taiwan Futures Strategies (Zipline-TEJ × TQuant-Lab)

從 `data/papers.db` 87 篇論文/報告中篩出 4 支可在台灣期貨市場執行的策略，
直接寫成 TQuant-Lab `tquant_future` bundle 可跑的回測程式碼。

## 策略一覽

| 目錄 | 對應論文 | 標的 | 訊號類型 | 期望年化 (paper原作) |
|---|---|---|---|---|
| `vgrsi_tx/` | arxiv 2605.01300 (Visibility Graphs RSI) | TX (台指期連續月) | 技術指標：可見圖 RSI | Sharpe 2.55-3.6 (DJI/EUR/XAU) |
| `cubic_momentum_tx/` | arxiv 2605.00854 (Periodic Bubbles) | TX | 三次方動量 + Hawkes 過熱 | 模型示意 |
| `tsmom_tx_mtx/` | wiley fut.70093 (Curve Momentum in China) + 業界共識 | TX/MTX | 12-1 月時序動量 + 波動目標 | Moskowitz et al. 經典 |
| `xsmom_stkfut_rmt/` | arxiv 2604.19107 (RMT Complexity Gap) + 個股期動量 | 個股期 universe | 橫斷面動量 + RMT regime overlay | regime-aware 變體 |

## 執行流程

回測環境與爬蟲共用 repo，但用獨立 venv（`.venv-bt`）避免 zipline-tej 與
crawler 的 numpy/pandas pin 衝突。

```bash
# 1. 建立回測 venv (一次性)
./scripts/setup-bt.sh                # 預設用 python3.11，可傳參覆寫

# 2. 設定 TEJ API key (一次性)
cp .env.example .env                  # 然後編輯 .env 填入真的 key
# 注：scripts/ingest_futures.sh 與 scripts/run_strategy.sh 會自動 source .env

# 3. ingest 期貨資料 (一次性 / 定期更新)
./scripts/ingest_futures.sh           # 預設 future="TX MTX"，可用 FUTURES_ROOTS 覆寫

# 4. 跑單一策略
./scripts/run_strategy.sh vgrsi_tx
# 或指定輸出路徑:
./scripts/run_strategy.sh tsmom_tx_mtx /tmp/tsmom.pkl
```

### ⚠️ TEJAPI_KEY 是 import-time 必要條件

`zipline-tej` 依賴的 `exchange_calendars.exchange_calendar_tejxtai` 模組
在 **import 時**就會打 TEJ API 取得最新交易日。沒設 `TEJAPI_KEY`，連
`import zipline` 都會丟 `AuthenticationError`。

也就是說：**任何呼叫到 runner.py / zipline 的指令，shell 內必須先有
`TEJAPI_KEY`**，不只 `zipline ingest` 而已。

### Calendar / Benchmark 預設

- **Calendar** 由 `runner.py` 預設為 `TEJ_morning_future`（`tquant_future`
  bundle 註冊的 calendar）。各策略的 `config.yaml` 不再設定 `calendar:`，
  除非要對接其他 bundle。
- **Benchmark** 預設不設定（zipline 採 zero-returns）。想對標 IR0001 時，
  必須同時 ingest `tquant` equity bundle 並在 config.yaml 加 `benchmark: IR0001`。

每個子目錄都有獨立 README 解釋假設、變數、限制。
