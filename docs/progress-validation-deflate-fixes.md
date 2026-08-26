# progress-validation-deflate-fixes

驗證層誠實化——年化係數改為量測、DSR 修掉退化、報告寫回 manifest。
Branch: `dev/validation-deflate-fixes`（stacked 於 `dev/restore-validation-sidecar`）

## 目標

讓 `validation-report-v1` 的每個數字都是「量出來的」或「明確標記為假設」，
不再有看起來像統計量、實際上是常數或用錯係數的欄位。並把報告接進
strategy manifest 的 `validation:` 區塊（spec v1.2 §2），讓 gs-zipline-tej
dashboard 能顯示。

## Milestone

- [x] **M1** — `report.py` 誠實化骨架：頻率推導函式、`resolve_n_trials`
  來源追溯（config > env > default）、`apply_to_manifest`、報告新增
  `n_trials_source` / `dsr_deflated` / `periods_per_year_source` /
  `warnings` 欄位。
- [x] **M2** — `runner.py` 串接：回測寫出 perf 後自動產 sidecar。
- [x] **M3** — 補 32 個測試。
- [x] **M4** — 修掉 M1~M3 引入與既有的兩個「數字是錯的」bug（見下）。

## 進度日誌

### M4 — 兩個會產生錯誤數字的 bug

**bug 1：DSR 在 `n_trials=1` 是常數 1.0，不是統計量**（既有，PR #17 就在 main）

`sharpe.py` 的 Bailey & LdP 極值近似：

```
e  = 1 / n_trials
z1 = norm.ppf(1 - e)
```

`n_trials=1` → `e=1` → `z1 = norm.ppf(0) = -inf` → `expected_max_sr = -inf`
→ `PSR(benchmark=-inf) = norm.cdf(+inf) = 1.0`。

實測（三組 seed，同一支函式）：

| seed | PSR | DSR(N=1) | DSR(N=2) | DSR(N=50) |
|---|---|---|---|---|
| 1 | 0.1212 | **1.0000** | 0.0459 | 0.0003 |
| 7 | 0.0417 | **1.0000** | 0.0121 | 0.0000 |
| 42 | 0.4920 | **1.0000** | 0.2947 | 0.0108 |

報告裡會出現一個滿分 DSR，而它跟報酬序列無關。這比「DSR 等於 PSR」更會騙人。

**修法**：`n_trials == 1` 特判 `expected_max_sr = 0.0`。這不是 hack——虛無假設
下單次抽樣的期望最大 SR 就是 `E[SR] = 0`，那個閉式解本來就只在 `n_trials >= 2`
有效。修後 `DSR(N=1) == PSR`。

**連帶**：`dsr_deflated` 原本寫成 `not (n_trials_source == "default" and n_trials <= 1)`，
只看來源字串、不看數學。任何人在 `config.yaml` 寫 `validation: {n_trials: 1}`
就能替一個未經 deflate 的數字換到「已 deflate」標籤——同一個謊換了個入口。
且 `test_declared_single_trial_is_honest_not_deflated_looking` 把該行為當斷言
鎖住。改成 `dsr_deflated = n_trials >= 2`，並改寫該測試為反向的 regression guard。

**bug 2：年化係數不該由 `rebalance` 推導**（M1 引入）

M1 的設計是 `rebalance`（v1.2 manifest 語義）優先於 `data_frequency`，理由是
「`rebalance` 是唯一能表達週頻/月頻的宣告」。這個理由對「策略決策頻率」成立，
但**年化係數取決於報酬序列的觀測頻率，不是調倉頻率**。zipline perf 的列永遠
是日頻（runner 硬寫 `data_frequency="daily"`），月頻調倉的策略照樣一天一列。

實測同一份 1 年期日頻 perf（總報酬 17.66%）：

| periods_per_year | 年化 Sharpe | CAGR |
|---|---|---|
| 252（正確） | 1.008 | **17.66%** |
| 12（`rebalance: monthly` 推出的） | 0.220 | **0.78%** |

`cagr()` 用 `years = len(r) / periods_per_year`，252 列 ÷ 12 = 21 年。

**修法**：新增 `infer_periods_per_year(perf)`——從 `dt` 欄或 DatetimeIndex 取
相鄰列間隔中位數，在 log 空間 snap 到 252/52/12/(minute→252)。量不到（無時間戳
或列數 < 3）才退回 252，並在 `warnings` 標明是假設而非推導。優先序：
`validation.periods_per_year`（明確宣告）> 量測 > 252。**`rebalance` 不再參與**。

`build_report()` 也改成手上有 frame 就自己量。原本要求呼叫端傳 `periods_per_year`
本身就是陷阱——寫端到端驗證腳本時我自己忘了傳，月頻序列以 252 年化，manifest
寫進 `cagr: "2.9628"`（296%）。改後同一條路徑寫出 `cagr: "0.0678"`、
`periods_per_year: "12"`。

**連帶**：`runner.py` 接上 `apply_to_manifest`（原本只有 CLI `--manifest` 會走到，
自動化路徑是死碼），並把 `warnings` 逐條印出。

### 不採納的一項審查意見

審查建議替 `xsmom_stkfut_rmt` 補 `rebalance: monthly`（其 description 寫
"monthly rebalanced"，被判定為「這次改動要救卻沒救的案例」）。**不採納**：
如上，該策略的 perf 仍是日頻列，補了反而會讓年化係數錯成 12。真正的修法是
量測，已在 M4 完成。

## 驗證

```
pytest tests/test_validation_report.py -q     # 45 passed
pytest tests/ -q                              # 328 passed / 12 failed
```

12 筆失敗與 baseline（`dev/restore-validation-sidecar`）**逐一相同**：
`test_webui_server.py` 10 筆（HTTP fixture 起不來）、`test_mcp_server.py` 1 筆、
`test_e2e_pipeline.py` 1 筆。皆為既有失敗，非本次造成。

端到端實測（非只讀程式碼）涵蓋：DSR 隨 N 單調下降且 N=1 時等於 PSR；四種
`n_trials_source` 在 N=1 時都拿不到 deflated 標籤；日頻/月頻各自量到正確係數；
`apply_to_manifest` 對真實 `vgrsi_tx/manifest.yaml` 副本 round-trip（值全為字串、
既有鍵零遺失、中文未跳脫、壞檔回 False）。

## 已知限制

- 目前四支策略的 `config.yaml` / `manifest.yaml` 都沒有 `validation.n_trials`，
  所以跑起來仍是 `n_trials=1` / `dsr_deflated=false` 並帶警告。這是**刻意的**：
  真實試驗數只有做研究的人知道，系統不該替他編一個。等 MINT 給出權威 N
  （gs-MINT#3 Q4）或研究者自行填入。
- `runner.py` 的 `run_algorithm` 仍硬寫 `data_frequency="daily"`，未讀 cfg。
  改它會變動回測本身的行為，超出本次範圍。
- PBO / CPCV 仍無 caller（`pbo.py` 需要 month × trial 矩陣，來源是 MINT 的
  `trial_returns/*.parquet`，已在 gs-MINT#3 提出請求）。

## Fallback 指引

- Rollback：`git revert` 本分支即可，`sharpe.py` 的特判與 `report.py` 的量測
  彼此獨立，可分別回退。
- 接手者需知：`FREQUENCY_PERIODS_PER_YEAR` 的 `minute -> 252` 是刻意的
  （perf 列是日頻，不是分鐘 bar 數），改它會錯兩個數量級。
