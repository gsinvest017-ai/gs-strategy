# Backtest Results — 2026-05-11

第一次跑通 `strategies/` 接到 `tquant_future` bundle 後的 metrics 紀錄。

## 環境

- venv: `.venv-bt/` (python 3.12, pandas 2.3.3, numpy 2.4.4, zipline-tej 2.2.2)
- bundle: `tquant_future`，僅 ingest `FUTURES_ROOTS="TX MTX"`，mdate 2018-01-01 ~ 2026-05-10
- calendar: `TEJ_morning_future` (5500 sessions, 2005-2027)
- benchmark: 無（zero-returns）
- commission: `PerContract(TX=200 NTD, MTX=100 NTD)`；slippage: `FixedSlippage(6.0 points)`

## 結果（3 / 4 支策略）

| name              | start      | end        |   years |   capital_base |    final | total_return | CAGR  | ann_vol | Sharpe | Max_DD  | n_tx |
|:------------------|:-----------|:-----------|--------:|---------------:|---------:|:-------------|:------|:--------|-------:|:--------|-----:|
| vgrsi_tx          | 2020-01-02 | 2026-04-30 |    6.32 |      5,000,000 |  8,935,800 | 78.72%       | 9.62% | 11.83%  |  0.866 | -18.49% |  489 |
| cubic_momentum_tx | 2018-01-02 | 2026-04-30 |    8.32 |      5,000,000 | 10,141,400 | 102.83%      | 8.87% | 15.60%  |  0.642 | -38.64% |  870 |
| tsmom_tx_mtx      | 2018-01-02 | 2026-04-30 |    8.32 |     10,000,000 | 20,544,000 | 105.44%      | 9.04% | 14.48%  |  0.692 | -27.95% |  419 |

重現命令：

```bash
./scripts/run_strategy.sh vgrsi_tx          /tmp/vgrsi_tx_result.pkl
./scripts/run_strategy.sh cubic_momentum_tx /tmp/cubic_momentum_tx_result.pkl
./scripts/run_strategy.sh tsmom_tx_mtx      /tmp/tsmom_tx_mtx_result.pkl

.venv-bt/bin/python scripts/summarize_results.py /tmp/*_result.pkl --markdown
```

## 觀察

- **vgrsi_tx**：最高 risk-adjusted (Sharpe 0.866)，最低 MDD (-18.49%)，paper 提的 RSI thresholds (30/70) 在 TX 上看起來工作正常
- **cubic_momentum_tx**：最高 absolute return (CAGR 8.87%, total 102.83%) 但 MDD 最大 (-38.64%)；trade count 870 是三支中最高，cubic flip 訊號比想像中頻繁
- **tsmom_tx_mtx**：CAGR 9.04% / Sharpe 0.692，TX + MTX 雙腳結構讓 trade 數中等 (419)，符合 12-1 TSMOM 月頻換倉特性

三支都正報酬、Sharpe > 0.6，但都還沒做 OOS 切割 / Walk-Forward / 多重檢定校正 — 這些屬於 `/review-strategy` 階段該做的事，不在此次 integration scope。

## 未跑：xsmom_stkfut_rmt → 2026-05-13 已跑

見 `docs/backtest-results-2026-05-13-xsmom.md`。

## 重大發現

1. **`exchange_calendars` 在 import time 打 TEJ API** — 沒 `TEJAPI_KEY` 連 `import zipline` 都炸。已用 `.env` 機制處理。
2. **pandas 3.0 不相容 zipline-tej 2.2.2** — `series[0]` 上 DatetimeIndex 在 pandas 3.0 不再 fallback 到 positional，ingest 時 `KeyError: 0`。已在 `requirements-bt.txt` pin `pandas<3.0`。
3. **`tquant_future` bundle 的 equity ingest 可選** — 預設拿 `IR0001 IX0001` 會失敗（key 可能無此 entitlement 或 TEJ 端空回），改成 futures-only ingest 就過。
