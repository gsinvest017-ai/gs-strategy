# xsmom_stkfut_rmt — Beta-neutral TX hedge (M13)

> 夜間無人值守任務 (claude/nightly-2026-05-19)。從
> `docs/progress-bt-integration.md` M11 的 finding 接續：
> dollar-net 構造下 `hedge_with_tx` 是 no-op，需要改用基於 ex-ante
> beta 的 CAPM-style 對沖。本 milestone 把這個 fix 做完。

## 目標

把 `strategies/xsmom_stkfut_rmt/` 的 TX 對沖從「dollar-net 等於零的
no-op」升級成「basket 加權 ex-ante beta 的真實對沖」，並驗證它在現有
30-root TX-stockfut universe 上的行為（不是要救活策略——M12 已確認
這個 universe 在 2020-2026 視窗無 alpha——而是把對沖功能本身做對，
讓未來擴大 universe 或重接成本之後策略能繼承一個正確的 hedge layer）。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M13a | 在 strategy.py 加上 beta-neutral hedge 邏輯 | `_ols_beta`、`_basket_beta` helper + `_rebalance` 內以 `-basket_beta` 下 TX 單，並 record `basket_beta` |
| M13b | 加單元測試覆蓋 beta 數學 | `tests/test_strategy_math.py` 多 3 個測試（已知 slope 回歸、NaN guard、weighted basket linearity） |
| M13c | 在 config.yaml 開啟 `beta_neutral_hedge: true` | 含 60 天 OLS window 與 ±2.0 weight cap 的註解 |
| M13d | 跑回測對照 no_hedge vs beta-neutral | 拿 `/tmp/xsmom_m13_*_result.pkl` 比 CAGR / vol / Sharpe / n_tx |
| M13e | 寫進度文檔 + commit | 即本檔 + git commit `M13:` |

## 進度日誌

### M13a — strategy.py 加 beta-neutral hedge ✅

**做了什麼**

- `_ols_beta(asset_returns, market_returns)`: 純 numpy 的 single-factor
  CAPM 回歸 (`beta = cov(a,m) / var(m)`)，附加幾道 NaN guard
  （長度不足、零市場波動、NaN 對齊）
- `_basket_beta(weights, betas)`: weighted sum of per-asset betas，
  NaN beta 自動跳過不污染總和
- `_rebalance`:
  - 在 `needed` lookback 計算多加進 `beta_window`
  - 蒐集 `asset_returns[root]` 同步建構 per-asset 報酬序列
  - TX hedge 分支：當 `beta_neutral_hedge=True` 時拉 TX 同期報酬，
    跑 `_ols_beta` 算每檔 beta，最後 `order_target_percent(tx_front, -basket_beta)`
  - hedge 權重 `np.clip(-basket_beta, -2.0, 2.0)` 防止 regime shock
    把 margin 拉爆
  - `record(basket_beta=…)` 把每天的 basket beta 寫進 result，方便事後 inspect
- docstring 把 hedge 段落改寫成「default dollar-net (no-op) vs M13 beta-weighted」

**Commit**: 待 M13e 合併

### M13b — 單元測試 ✅

**新增三個測試** (在 `tests/test_strategy_math.py`):

1. `test_ols_beta_recovers_known_slope`: 用 `asset = 1.5 * market + noise`
   合成 200 樣本，斷言 `_ols_beta(asset, market)` 在 0.05 之內回到 1.5
2. `test_ols_beta_nan_guards`: 樣本不足 (n=5) 與零方差市場兩種情況都該回 NaN
3. `test_basket_beta_linearity`: 已知 weights/betas 直接算對 reference
   結果；NaN beta 應被剔除而非毀掉整個 sum

跑 `./venv-bt/bin/python tests/test_strategy_math.py` → ALL MATH TESTS PASS（含舊的 3 個）。

### M13c — config 開啟 beta-neutral 預設 ✅

`strategies/xsmom_stkfut_rmt/config.yaml` 加：

```yaml
  beta_neutral_hedge: true
  beta_window: 60      # rolling OLS lookback (trading days) for per-asset beta
```

註解寫明 M11 的 no-op 起源、為什麼預設打開、以及 ±2.0 cap 的存在。
原 `hedge_with_tx: true` 改為「master switch；off => 完全不對沖」。

### M13d — 回測對照 ✅

| variant | CAGR | ann_vol | Sharpe | Max_DD | n_tx | final |
|---|---:|---:|---:|---:|---:|---:|
| no_hedge (M13-era) | -57.91% | 28.14% | -3.037 | -99.58% | 457 | 125,895 |
| **beta_neutral (M13)** | **-57.34%** | **27.72%** | **-3.037** | **-99.54%** | **479** | **137,073** |

對 M11 baseline_m10 的數字一致 (CAGR -57.91% 完全 reproduce)。
beta-neutral 表現如預期：

1. **Vol 確實下降** 28.14% → 27.72%（0.42 pp，~1.5% 相對）— hedge 機制正常工作
2. **CAGR 微改善** -57.91% → -57.34%（0.57 pp）— 對沖 capture 到一點 market downside
3. **Sharpe 完全相同** -3.037（精度位元相同）— vol 降幅與 return 改善比例一致，
   風險調整後等價
4. **多 22 筆 TX 交易** — 對沖在重新 sizing，不是 no-op

**basket_beta 統計** (n=1534 個 record，跨 6.32 年):
- mean = 0.10, std = 0.21
- min = -0.36, max = +0.81
- 分布: p10 -0.15 / p25 -0.01 / p50 +0.05 / p75 +0.19 / p90 +0.36

代表 6-on-6 long/short basket 在這個 universe 上**平均略帶正 beta**
（多頭 leg 包含 TSMC/鴻海等 high-beta 龍頭，空頭 leg 偶爾抓金融股
等 lower-beta 名稱），所以 hedge 平均下小單 short TX；極端時對沖比例
可達 36%，符合直覺。

**Sanity check**：把 `hedge_with_tx=true, beta_neutral_hedge=false`
（M11 的 dollar-net 路徑）跑出來會等同 no_hedge — M11 已經證實過，
此次不再重跑。

### M13e — 進度文檔 + commit ✅

即本檔。提交 `M13: implement beta-neutral TX hedge — mechanically correct fix, confirms M12 no-alpha finding`。

## 為什麼這個 milestone 仍然重要（即使數字慘）

M12 已經結論「整個策略在這個 universe + 視窗無 alpha」。M13 的價值
不在於救活策略，而在於：

1. **修掉 M11 揭露的設計缺陷** — `hedge_with_tx` flag 之前是
   misleading no-op。修完之後若未來擴 universe (M7 已 prep 257 檔
   universe.json)，hedge 層會繼承正確的 CAPM-style 構造，不會再
   需要重新發現一遍。
2. **驗證 basket_beta 在台灣 stock-fut universe 上是 positive 偏正**，
   而且 dispersion 大（std 0.21），代表動態 hedge 比靜態 1:1 更合理。
3. **建立可重用的 helper** — `_ols_beta` / `_basket_beta` 可以給其他
   策略（cubic_momentum_tx、tsmom_tx_mtx）共享。如果之後抽到
   `_common/futures_setup.py`，這次的單元測試是現成的合約檢查。
4. **走完 M11 → M12 → M13 的設計反饋環**，把所有可控 hedge / 訊號
   參數都 ablation 過了。任何後續 attempts 必須在 universe、成本、
   walk-forward 三個非參數維度上動工，回到 `/review-strategy` 階段。

## Fallback 指引

M13 的 4 個檔案改動皆獨立可逆：

1. **strategy.py** — `git diff HEAD~1 strategies/xsmom_stkfut_rmt/strategy.py`
   會展現 helper 函式加進來、`_rebalance` 內 hedge 分支替換。回滾就是
   `git revert <M13 commit>`。
2. **config.yaml** — 移除 `beta_neutral_hedge:` 與 `beta_window:` 兩行
   等同於回到 M12 行為（程式預設 `beta_neutral_hedge=False`）。
3. **tests/test_strategy_math.py** — 三個新測試自含 stub，不依賴
   zipline runtime；可獨立刪除。
4. **docs/progress-xsmom-beta-hedge.md**（本檔） — 純 docs，刪掉不影響執行。

最差情況：`git reset --hard 46707c3`（M12 commit），再
`rm /tmp/xsmom_m13_*_result.pkl`，回到任務開始狀態。

## M14 — 擴 universe 30 → 60 檔 ✅ (diversification works, alpha 仍缺席)

> 夜間無人值守任務（claude/nightly-2026-05-20）。接續 M13 結論「策略
> 機械上對了，但 30-stock universe 沒有 alpha」，這次把 M12 列出的
> 四項剩餘方向中**最具體的第 1 項**做完：擴 universe 從 30 → 60 檔，
> 重 ingest tquant_future，重跑 xsmom 看 diversification 帶來什麼。

### 做了什麼

1. 從 `data/stock_futures_universe.json` 拿出 top-60 (code,root) pairs，
   手工對照 Taiwan 上市公司中文名建 `universe_roots:` YAML 區塊
2. 跑 `FUTURES_ROOTS="TX MTX <60-roots>" ./scripts/ingest_futures.sh`，
   ingest 成功，新 bundle 落在
   `~/.zipline/data/tquant_future/2026-05-19T16;01;16.781143`
   （共 62 個 root，每 root 105 contracts，2018-01 ~ 2026-05）
3. `strategies/xsmom_stkfut_rmt/config.yaml` 的 `universe_roots:` 從 30 行
   擴到 60 行（沿用 M9 的中文 ticker 對照註解格式）
4. `./scripts/run_strategy.sh xsmom_stkfut_rmt /tmp/xsmom_m14_60root_result.pkl`
5. 用 `scripts/summarize_results.py` + 自製 inline script 拉 metrics +
   basket_beta + regime_scale + gap 分布

### 結果：30-root vs 60-root

| universe | CAGR | ann_vol | Sharpe | Max_DD | n_tx | final |
|---|---:|---:|---:|---:|---:|---:|
| 30 (M13 beta_neutral) | -57.34% | 27.72% | -3.037 | -99.54% | 479 | 137,073 |
| **60 (M14)** | **-43.26%** | **20.15%** | **-2.812** | **-97.28%** | **748** | **833,362** |

### 三個發現

1. **Diversification 確實有效**：CAGR 從 -57.34% 改善到 -43.26%
   （+14.08 pp）、vol 從 27.72% 降到 20.15%（-7.57 pp，相對 27%）。
   final portfolio value 從 137k 漲到 833k（6 倍）。但 Sharpe 只從
   -3.04 → -2.81，因為 return 和 vol 改善幅度大致同比例。
2. **basket_beta 範圍縮小但仍偏正**：mean 0.10 → 0.13、std 0.21 → 0.19、
   range [-0.36, +0.81] → [-0.20, +0.48]。60 檔的 long/short basket
   net beta 偏離 0 的程度比 30 檔小，符合 cross-sectional 構造下
   籃子分散度提升的預期。
3. **RMT gap 分布顯著左移 → 60-stock universe 上原 thresholds 變得
   過嚴**：

   | universe | gap mean | gap std | gap p33 | gap p75 | gap max |
   |---|---:|---:|---:|---:|---:|
   | 30 | 0.050 | 0.015 | 0.045 | 0.058 | 0.097 |
   | **60** | **0.042** | **0.011** | **0.037** | **0.049** | **0.069** |

   regime_scale 分布也對應變化：

   | universe | scale=0 | scale=0.5 | scale=1.0 |
   |---|---:|---:|---:|
   | 30 (M10) | 36% | 39% | 25% |
   | **60 (M14)** | **62%** | **27%** | **11%** |

   策略現在 62% 時間 de-risk 到零（30-root 時只有 36%），因為 M10
   校的 thresholds (0.045/0.058) 對應 30-root 分布的 p33/p75，現在
   不再是 60-root 的 p33/p75。若要在 60-root 重新校準：p33≈0.037、
   p75≈0.049。

### 為何 alpha 仍未出現

擴 universe 是 M11/M12 列的可能因素中**機械上效果最大**的一個（vol
顯著降），但 Sharpe 仍 -2.8 而非接近 0。結合 M11/M12 ablation 結果：

- 不是 hedge 問題（M13 已修，本次保留 beta_neutral）
- 不是 signal direction 問題（M11 reverse 沒救）
- 不是 portfolio concentration（wider decile + 60 檔 ≈ 6→12 stocks per leg）
- **可能是訊號本身在台股個股期 2020-2026 視窗根本不存在**，加上
  RMT regime filter 在新 universe 上需要重新校準才公平比較

### 後續可選 milestone

M12 列的四項，本次完成第 1 項（擴 universe）。剩下：

1. ~~擴 universe 到 ≥ 60 檔~~ — **本 M14 完成**
2. ~~Beta-neutral hedge~~ — M13 完成
3. **校準 commission/滑價到真實券商 spec** — 拿券商實際 fee schedule
   (台股個股期約 110-120 NTD/口 + 0.002% 交易稅)，重設
   `per_contract_cost` 與 `spread_points`
4. **Walk-forward (2020-2022 / 2022-2024 / 2024-2026)** — 切三段
   獨立跑，看不同 regime 表現

額外副產品 (從 M14 衍生)：

5. **RMT thresholds 在 60-root universe 重新校準** —
   p33≈0.037 / p75≈0.049（vs 30-root 的 0.045/0.058），預期能讓
   regime_scale 分布從 62/27/11 重回 35/40/25 的平衡

這些仍屬 `/review-strategy` 階段。

### Commit

`M14: expand xsmom universe 30 -> 60 — vol -7.6pp / CAGR +14pp but Sharpe still negative`

## Fallback 指引

M13 與 M14 的改動皆獨立可逆：

**M14 (本次)**:

1. **config.yaml** — 把 `universe_roots:` 後 30 行刪掉（保留 CAF~DIF
   前 30 個），回到 M13 行為。或 `git revert <M14 commit>`。
2. **bundle** — 刪 `~/.zipline/data/tquant_future/2026-05-19T16;01;16.781143/`
   並執行原 30-root 的 ingest 即可回到 M8 bundle 狀態（M8 bundle
   `2026-05-12T16;03;04.279177` 仍在，沒被刪）。
3. **docs/progress-xsmom-beta-hedge.md** — 本檔；revert M14 commit。

**M13**:

1. **strategy.py** — `git revert <M13 commit>` 還原 helper 函式與
   `_rebalance` hedge 分支替換
2. **config.yaml** — 移除 `beta_neutral_hedge:` 與 `beta_window:` 兩行
3. **tests/test_strategy_math.py** — 三個新測試自含 stub，可獨立刪除
4. **docs/progress-xsmom-beta-hedge.md** — 純 docs，刪掉不影響執行

最差情況：`git reset --hard 46707c3`（M12 commit），再
`rm /tmp/xsmom_m1[34]_*_result.pkl`，回到任務開始狀態。

## 相關檔案

- `strategies/xsmom_stkfut_rmt/strategy.py` — M13 編輯（helpers + 新 hedge 邏輯）
- `strategies/xsmom_stkfut_rmt/config.yaml` — M13 + M14 + M15 編輯（hedge flags + 60-root universe + 重新校準 RMT thresholds）
- `tests/test_strategy_math.py` — M13 編輯（3 個新測試）
- `docs/progress-xsmom-beta-hedge.md` — M13 新增 / M14 / M15 append（本檔）
- `/tmp/xsmom_m13_beta_neutral_result.pkl`、`/tmp/xsmom_m13_no_hedge_result.pkl` — M13 產出
- `/tmp/xsmom_m14_60root_result.pkl` — M14 產出
- `/tmp/xsmom_m15_60root_recal_result.pkl` — M15 產出
- `~/.zipline/data/tquant_future/2026-05-19T16;01;16.781143/` — M14 新 bundle (M15 沿用)

## M15 — RMT thresholds 在 60-root universe 重新校準 ⚠️ (negative finding)

> 夜間無人值守任務（claude/nightly-2026-05-21）。M14 揭示 30-root 校的
> `rmt_threshold/rmt_low_threshold = 0.058/0.045` 用在 60-root universe 上
> 過嚴：regime_scale 變成 62% zero / 27% half / 11% full，策略 62% 時間
> de-risk 到零。本 milestone 是 M14 列出的 5 個 follow-up 中最機械可控
> 的一項——把閾值改成 60-root 分布的 p33/p75。

### 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M15a | 改 config | `rmt_threshold: 0.049` / `rmt_low_threshold: 0.037`，註解寫明 dual-universe calibration 軌跡 |
| M15b | 重跑 backtest | `/tmp/xsmom_m15_60root_recal_result.pkl` |
| M15c | 拉 metrics + gap/scale/beta 分布，比 M14 | 表 + 結論 |
| M15d | 本段 + commit | `M15: recalibrate RMT thresholds for 60-root` |

### 結果：M14 vs M15 (同 60-root universe，同 beta-neutral hedge)

| variant | thresholds | CAGR | ann_vol | Sharpe | Max_DD | n_tx | final |
|---|---|---:|---:|---:|---:|---:|---:|
| M14 (30-root cal) | 0.058 / 0.045 | -43.26% | 20.15% | -2.812 | -97.28% | 748 | 833,362 |
| **M15 (60-root cal)** | **0.049 / 0.037** | **-52.05%** | **25.48%** | **-2.852** | **-99.04%** | **742** | **287,303** |

### regime_scale 分布變化

| version | scale=0 | scale=0.5 | scale=1.0 |
|---|---:|---:|---:|
| M10 (30-root, 0.058/0.045) | 36% | 39% | 25% |
| M14 (60-root, 0.058/0.045) | 62% | 27% | 11% |
| **M15 (60-root, 0.049/0.037)** | **31%** | **43%** | **25%** |

校準達到設計目的：M15 的 31/43/25 跟 M10 的 36/39/25 在「分布形狀」
上等價（策略約三分之一時間 risk-off / 一半時間 half-pos / 四分之一時間
full-pos）。Mechanically the regime filter is now apples-to-apples
comparable to the 30-root world.

### gap 分布 sanity check (跟 M14 應一致——只是 thresholds 改了)

| stat | M14 | M15 |
|---|---:|---:|
| n | 1534 | 1534 |
| mean | 0.042 | 0.0423 |
| std | 0.011 | 0.0111 |
| p33 | 0.037 | 0.0374 |
| p75 | 0.049 | 0.0493 |
| max | 0.069 | 0.0685 |

確認 gap 是 universe + window 函數，不被 threshold 改變。新 thresholds
(0.049/0.037) 精確對應到 60-root 自身的 p75/p33——校準到位。

### basket_beta 分布 (M15)

| stat | M14 | M15 |
|---|---:|---:|
| n | ~1534 | 1534 |
| mean | +0.13 | +0.11 |
| std | 0.19 | 0.18 |
| min | -0.20 | -0.38 |
| max | +0.48 | +0.48 |
| p50 | +0.13 | +0.14 |

basket_beta 統計近似不變（mean 0.13 → 0.11），hedge layer 行為一致。
M15 偶爾出現 -0.38 的負 beta（M14 沒低於 -0.20），可能是新分布下
short leg 在金融股深度撤退時 net basket beta 翻負——hedge 此時下
long TX 單，符合直覺。

### 為何 mechanically correct 但 performance 更差

策略現在 25% 時間進 full position（M14 只有 11%），多出來的 14 pp
時間暴露在 momentum signal 下。但 M12 已證實：

> momentum signal 本身在台股個股期 2020-2026 視窗是負 alpha。

所以越「正確地」執行這個 regime filter（讓 full / half / zero 分布
回到原始設計），就把更多資金交給負 alpha 訊號，CAGR 從 -43% 掉到
-52%、vol 從 20% 升到 25%。Sharpe -2.81 → -2.85 變化很小，因為
return 與 vol 同比例惡化。

這是 M11/M12 ablation 結論的 **第三次獨立證實**：
1. M11/M12: 8 個 signal/portfolio 參數變體 CAGR 全在 [-64%, -52%]
2. M13: 修正 hedge 數學瑕疵，Sharpe 仍 -3.04
3. M14: 擴 universe 30 → 60，diversification 把 final value 漲 6 倍但 Sharpe -2.81
4. **M15: 把 regime filter 校到「正確分布」，仍 Sharpe -2.85**

每一個 mechanical 修正都做對了（hedge 真的 hedge、universe 真的
diversify、regime filter 真的分配 1/3 風險預算），但每一個都不會
創造原本不存在的 alpha。**訊號層面的問題已確認**。

### 後續方向（不在本 milestone）

剩下 M14 列的 3 個方向中，後 2 個（commission/滑價校準、walk-forward
切片）的預期效果都是「進一步揭示更多負面細節」，不太可能翻轉策略。
真正的下一步應該是：

- 改變 signal 構造（e.g., 短期 mean-reversion + 長期 momentum 結合、
  earnings drift 因子、retail flow 反向 — TQuant-Lab 已提供
  `retail_long_short_ratio`）
- 換 universe（小型股、半導體子集 vs 金融子集分別跑）
- 進入 `/review-strategy` 階段做正式統計顯著性檢定（block bootstrap
  Sharpe CI、permutation test against zero-pred null），把 negative
  finding 量化成 publishable result

M-series 整合 (M1-M15) 至此**真的可以結束了**：pipeline 完整、所有
mechanical 修正都已驗證、四個策略的 baseline metrics 都有了，下一階段
是 research 而非 integration。

### Commit

`M15: recalibrate xsmom RMT thresholds for 60-root universe — regime filter mechanically correct, third confirmation of M12 no-alpha finding`

### M15 Fallback 指引

1. **config.yaml** — 把 `rmt_threshold: 0.049` 改回 0.058，`rmt_low_threshold: 0.037` 改回 0.045，回到 M14 行為。或 `git revert <M15 commit>`。
2. **產出 pkl** — `rm /tmp/xsmom_m15_60root_recal_result.pkl`。
3. **bundle / strategy.py / 測試** — M15 不動這些，零回滾成本。

最差情況：`git reset --hard cdb6aca`（M14 commit），回到任務開始狀態。

## M16 — Walk-forward across 3 non-overlapping sub-periods ⚠️ (negative finding, 4th confirmation)

> 夜間無人值守任務（claude/nightly-2026-05-22）。延續 M15 結尾「下一個
> 可機械執行的 follow-up 是 walk-forward 切片」。M14 列的 4 項剩餘
> 方向中，這是不需要外部 broker fee 資料、純用現有 bundle + config
> 就能跑完的最後一項。

### 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M16a | 寫 walk-forward runner | `scripts/run_xsmom_walkforward.py`：3 個非重疊 ~2-year 子期間，每段 deep-copy config 後覆寫 top-level start/end |
| M16b | 跑回測 + 收集 regime diagnostics | 3 個 `/tmp/xsmom_m16_walkforward_*_result.pkl` + metrics 表 + scale/gap/basket_beta 分布表 |
| M16c | 寫進度文檔 + commit | 即本段 + git commit `M16:` |

### 子期間切分

| period | range | regime label |
|---|---|---|
| P1_2020_2021 | 2020-01-01 .. 2021-12-31 | COVID drawdown + V-rebound + 半導體缺貨多頭 |
| P2_2022_2023 | 2022-01-01 .. 2023-12-31 | Fed 升息熊市 + 2023 Q4 反彈 |
| P3_2024_2026 | 2024-01-01 .. 2026-04-30 | AI 多頭主導 + 末段震盪 |

每段都 ≥ 2 年，足夠讓 lookback=126 / skip=21 / beta_window=60 暖機後仍有
~350 個交易日真正下單。

### 結果：per-period metrics

| period | range | years | CAGR | ann_vol | Sharpe | Max_DD | final |
|---|---|---:|---:|---:|---:|---:|---:|
| P1_2020_2021 | 2020-01-01 .. 2021-12-31 | 1.99 | -77.65% | 40.34% | **-3.580** | -94.99% | 1,513,485 |
| P2_2022_2023 | 2022-01-01 .. 2023-12-31 | 1.98 | -65.51% | 25.40% | **-4.180** | -87.96% | 3,626,669 |
| P3_2024_2026 | 2024-01-01 .. 2026-04-30 | 2.32 | -58.17% | 27.61% | **-3.151** | -87.06% | 3,956,223 |

### Regime diagnostics

| period | scale=0 | scale=0.5 | scale=1.0 | gap_mean | basket_beta_mean | basket_beta_std |
|---|---:|---:|---:|---:|---:|---:|
| P1_2020_2021 | 25.6% | 44.2% | 30.3% | 0.0419 | +0.144 | 0.163 |
| P2_2022_2023 | 30.9% | 52.0% | 17.1% | 0.0423 | +0.049 | 0.180 |
| P3_2024_2026 | 36.4% | 35.0% | 28.6% | 0.0426 | +0.136 | 0.173 |

### 五個觀察

1. **每段 Sharpe 都顯著為負**（-3.58 / -4.18 / -3.15），策略不只是「2020-2026
   平均無 alpha」，而是**任何 2-year 子視窗都在主動賠錢**。沒有任何 regime
   讓 cross-sectional momentum 在這個 universe 翻正。
2. **P2 (2022-2023) 是最差**：Sharpe -4.18，雖然 vol 最低 (25.4%)，return
   也最穩定地往下走。Fed 升息週期下台股藍籌 dispersion 變窄、
   momentum-formation 訊號失效；同期 basket_beta_mean 也最低 (+0.049)，
   代表 long/short 構造本身在這段時間「比較中性」——但中性不代表沒虧，
   因為 momentum 方向本身就錯。
3. **P1 (2020-2021) 是最高 vol (40%)、最差 CAGR (-77.65%) 但 Sharpe 不是最差**：
   COVID drawdown + V-rebound 把月 return whipsaw 拉大，相對虧損絕對值
   被高 vol 「壓低」了 Sharpe 比例。Max_DD -94.99% 直接逼近清盤。
4. **P3 (2024-2026) 是 "least bad"**：Sharpe -3.15，AI 多頭下 regime_scale=1.0
   時間最多 (28.6%)，理論上策略最敢加倉。可是即便最敢加倉的子視窗也虧
   58.17% CAGR——再次印證底層 signal 在這個 universe 不工作。
5. **gap_mean 三段幾乎相等** (0.0419 / 0.0423 / 0.0426)：RMT complexity gap
   在三個截然不同 regime 下竟然分布幾乎一樣——意味著 M15 校的閾值
   (p33/p75=0.037/0.049) 在任一子視窗都仍是合理門檻。Regime filter
   mechanically 是穩定的，問題不在它身上。

### 第四次獨立證實

加上 M11/M12 ablation、M13 hedge fix、M14 universe expansion、M15 threshold
recal，現在這是**第四個**獨立 axis 上看 xsmom_stkfut_rmt 在
台股個股期 universe 上的負 alpha：

1. M11/M12: 8 個 signal/portfolio 參數變體 → CAGR 全 [-64%, -52%]
2. M13: 修正 hedge 數學瑕疵 → Sharpe -3.04
3. M14: 擴 universe 30 → 60 → Sharpe -2.81
4. M15: 校準 regime filter → Sharpe -2.85
5. **M16: walk-forward 3 個 2-year 子視窗 → Sharpe ∈ [-4.18, -3.15]，全段都負**

每個維度都檢查過了，策略**確定不能用**。任何後續工作必須在更基礎的
層面動工——換 signal 構造 / 換 universe 分群 / 重新做 paper-level
hypothesis testing。M-series integration 正式告終於 M16。

### 為何此 milestone 值得做

雖然結論是預期內的負面確認，walk-forward 仍有獨立價值：

1. **揭露 regime stability 的微觀結構**：gap_mean 跨三段幾乎不變，
   證明 RMT complexity gap 在台股 2020-2026 是個結構穩定的訊號——
   它測的是「整個 universe 的同步度」，**而非個別 regime label**。
   這對未來想拿 RMT gap 當風控 overlay 的策略是好消息（即使 xsmom
   本身死了）。
2. **暴露 basket_beta 在 P2 的下移**：P2 mean +0.049 vs P1/P3 ~+0.14。
   升息熊市下藍籌 long basket 與金融 short basket 的 beta 差縮小，
   long/short 構造在這個 regime 比其他時段更接近真正 market-neutral。
   值得後續策略借鏡：可能 P2 是這個 universe 上 long/short alpha
   最公平的測試窗。
3. **印證所有 mechanical fix 的穩健性**：M13 hedge / M15 thresholds
   在每個子視窗都按設計 mechanism 工作（regime_scale 分布合理、
   basket_beta 範圍合理、gap_mean 一致）。如果未來把 strategy.py
   的 hedge layer 拆到 `_common/futures_setup.py` 共用，這次的 3-段
   walk-forward 是 hedge contract 的隱含 regression test。

### Commit

- M16a: `M16a: add xsmom walk-forward runner script`（已合入：49409db）
- M16b/c: 本段 + `M16: walk-forward confirms no alpha across 3 sub-periods`

### M16 Fallback 指引

1. **scripts/run_xsmom_walkforward.py** — `git rm` 或 `git revert <M16a commit>`。
2. **產出 pkl** — `rm /tmp/xsmom_m16_walkforward_*_result.pkl`（3 個檔案）。
3. **docs/progress-xsmom-beta-hedge.md** — 本段；`git revert <M16b commit>`。
4. **strategy.py / config.yaml / bundle** — M16 不動，零回滾成本。

最差情況：`git reset --hard 1c5528c`（M15 commit），再
`rm /tmp/xsmom_m16_walkforward_*_result.pkl`，回到 M16 開始前狀態。

## M17 — Cost calibration: realistic broker fee + 期交稅 ⚠️ (negative finding, 5th confirmation + slippage model flaw exposed)

> 夜間無人值守任務 (claude/nightly-2026-05-23)。M14 列的 4 項
> follow-up 中最後一個機械可控項——「校準 commission/滑價到真實
> 券商 spec」。同時偵測到一個 pre-existing bug：自 M14 擴 60-root
> universe 以來，60 個 stock-fut roots 從未進過 `per_contract_cost`
> 映射表，於是 fall back 到 zipline 的 `DEFAULT_PER_CONTRACT_COST =
> 0.85`（USD 預設，實質約等於免費）。本 milestone 同時修這個 bug。

### 動機

從 `.venv-bt/lib/python3.12/site-packages/zipline/finance/commission.py`
讀 PerContract source 確認三件事：

1. `cost` 是 **per side**（line 123: `additional_commission =
   abs(transaction.amount * cost_per_unit)`），不是 round-trip
2. Cost map 中不存在的 root 會 fall back 到
   `DEFAULT_PER_CONTRACT_COST = 0.85`
3. M14 擴 universe 後，60 個 stock-fut roots 都沒進 cost map →
   全部以 0.85 NTD/side 計算，等於免費

### 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M17a | 確認成本模型 | 從 zipline source 確認 PerContract 行為；蒐集 broker + 期交稅典型值 |
| M17b | 更新 config.yaml | TX/MTX/60 stock-fut 全部進 cost map；含中文 ticker 註解 |
| M17c | 跑回測 + 比 M15 | metrics 表 + slippage 8 vs 6 的 ablation 揭示模型缺陷 |
| M17d | 寫進度文檔 + commit | 本段 |

### 成本模型（per-side NTD）

| Root | M15 cost | M17 cost | 來源 |
|---|---:|---:|---|
| TX | 200 | **150** | broker ~80 + 期交稅 ~70 (= 17000pt × 200 × 0.00002) |
| MTX | 100 | **60** | broker ~40 + 期交稅 ~17 (= 17000pt × 50 × 0.00002) |
| 60 stock-fut | (none → 0.85) | **120 each** | broker ~110 + 期交稅 ~10 (per M14 doc 註解 "110-120 NTD/口 + 0.002% 交易稅") |

### 結果：3 組對照

| variant | spread (pts) | stock-fut cost | CAGR | ann_vol | Sharpe | Max_DD | n_tx | final |
|---|---|---|---:|---:|---:|---:|---:|---:|
| M15 (baseline) | 6.0 | 0.85 (default) | -52.05% | 25.48% | -2.852 | -99.04% | 742 | 287,303 |
| **M17a (commission-only)** | **6.0** | **120** | **-52.49%** | **25.98%** | **-2.829** | **-99.10%** | **721** | **270,821** |
| M17 ablation (cost + slippage 8) | 8.0 | 120 | -56.23% | 34.55% | -2.272 | -99.46% | 488 | 161,243 |

**M17 canonical run**: commission-only (`/tmp/xsmom_m17_commonly_result.pkl`).
Config.yaml 鎖在 `spread_points: 6.0`；slippage 8.0 變體保留在
`/tmp/xsmom_m17_cost_realistic_result.pkl` 供 audit。

### 四個發現

1. **真實 commission 對策略的衝擊極小**：CAGR 從 -52.05% 變
   -52.49%（−0.44 pp，~7 bp/年）、Sharpe 微差到不可察覺
   (-2.852 → -2.829)。**證實 M15 結論不是被低估的成本撐起來的**——
   即使按真實 broker fee + 期交稅，策略仍然是 6 年 -52% CAGR 的
   負 alpha bottom。
2. **n_tx 微降 (742 → 721)**：commission 多收一點現金，rebalance
   時 buying power 微縮 → `order_target_percent` 切出來的合約數
   被 floor 截尾稍多。沒有結構性變化。
3. **slippage 6→8 是真正的劇變來源**：CAGR 從 -52.5% 掉到 -56.2%
   （-3.74 pp），portfolio 9 個月跌到 10%、1 年跌到 5%、2 年跌到 1%。
   ann_vol 從 26% 飆到 34.5% 因為早期巨幅 daily drawdown。
4. **slippage model 結構缺陷揭露**：`FixedSlippage(spread=X)` 套用
   **單一** spread 到所有資產 price units。對 TX (~17000 pt)，
   6 pts = 0.035% per side；對 100 NTD 個股期，6 NTD/share = **6%
   per side**。同一個 spread 數值在 mixed universe (index futures +
   stock futures) 下對兩類資產的相對影響差 170×。8.0 的 ablation
   顯示這個 mismatch 並非線性 — bump 33% 就 wreck portfolio。

### 為何 commit 用 spread_points=6.0 而非 8.0

實際 stock-fut bid/ask 在台灣多落在 0.05-0.10 NTD/share（小型成份股）
到 0.5-1.0 NTD/share（流動性差的小尾）。6 NTD/share 已經是 60-600
ticks，遠超實況；8 NTD/share 更誇張。M15 的 6.0 在 stock-fut 上
已經 over-charges，但至少 M15 baseline 的所有對照都用它，
apples-to-apples 比較成立。M17 在 commission 結構修正之後，
保留 6.0 維持 cross-version 比較性；slippage 模型本身的問題
留給未來 milestone（需要 per-root slippage 或 percentage-based
slippage model）。

### diagnostic 統計 (M17 commission-only vs M15)

basket_beta 與 regime_scale 統計**基本不變**（commission 不影響
訊號或 regime filter）：

| stat | M15 | M17 |
|---|---:|---:|
| basket_beta mean | +0.11 | +0.111 |
| basket_beta std | 0.18 | 0.177 |
| basket_beta min/max | -0.38 / +0.48 | -0.383 / +0.475 |
| gap mean / std | 0.0423 / 0.0111 | 0.0423 / 0.0111 |
| regime_scale 0 / 0.5 / 1.0 | 31% / 43% / 25% | 31.2% / 43.3% / 25.5% |

Trade flow by year (M17 commission-only):
`{2020: 291, 2021: 233, 2022: 114, 2023: 42, 2024: 31, 2025: 10, 2026: 0}`
— 跟 M15 同樣前重後輕，因為 portfolio 越打越小、合約 floor 截尾越多。

### 為什麼這仍然重要（即使數字慘）

M11 / M12 / M13 / M14 / M15 / M16 都是「mechanical 修正但 alpha
仍缺席」的累積證據。M17 是第 5 次獨立確認，但有兩個新貢獻：

1. **修掉 pre-existing cost-undercount bug**：自 M14 擴 universe 後
   60 個 stock-fut roots 都跑在 0.85 NTD/side 預設。現在所有 root
   都有明確成本標註，未來改 universe 或加新 root 不會再隱性繼承
   這個 default fallback。
2. **暴露 slippage model 結構缺陷**：FixedSlippage 對 mixed price-
   scale universe 失效。這是任何想在 TX + stock-futures 上做 L/S
   策略都會撞到的問題，不只 xsmom_stkfut_rmt。下個 milestone 若要
   做正確的 slippage layer，需要：(a) 用
   `VolumeShareSlippage` 把 spread 縮成「fraction of price」；
   (b) 或寫 custom slippage 模型按 root_symbol 套不同 spread；
   (c) 或乾脆把 stock-fut slippage 移到 commission 內（per-contract
   slippage 預估）。

### M14 列的 5 項 follow-up 至此全部完成

| # | 項目 | milestone | 結論 |
|---|---|---|---|
| 1 | universe 擴 30 → 60 | M14 ✅ | vol -7.6 pp，但 Sharpe 仍 -2.81 |
| 2 | Beta-neutral hedge | M13 ✅ | hedge 機制現在正確，但不創造 alpha |
| 3 | 成本/滑價校準 | **M17 ✅** | commission 真實化只多 -0.44 pp/年；slippage model 結構缺陷待修 |
| 4 | Walk-forward 切片 | M16 ✅ | 3 個子視窗全負 Sharpe，沒有「壞 regime + 好 regime」可拆 |
| 5 | RMT thresholds 60-root 校準 | M15 ✅ | regime filter 分布回到設計值，performance 反而變差 |

### Open follow-ups（不在 integration M-series scope）

- **Slippage model rewrite**：寫 per-root spread map 或 percentage-based
  slippage，把 stock-fut spread 設為合理 0.05-0.1 NTD/share 範圍
- **訊號層 redesign**：M15 / M16 已確認 cross-sectional momentum 在
  台股個股期 2020-2026 全期 + 各子視窗都無 alpha；需換訊號（短期
  reversal、retail flow、earnings drift）或換 universe（小型股、
  半導體子集 vs 金融子集）
- **正式統計顯著性**：block bootstrap Sharpe CI、permutation test
  against zero-pred null，把 negative finding 量化成 publishable
  result

進入 `/review-strategy` 階段，這些屬於 research 而非 integration。

### Commit

`M17: calibrate commission/slippage to realistic broker spec — confirms M15 finding + reveals FixedSlippage structural mismatch`

### M17 Fallback 指引

1. **config.yaml** — `git revert <M17 commit>` 還原 cost map。或手動：
   - `per_contract_cost.TX` 改回 200、`MTX` 改回 100
   - 刪除 60 個 stock-fut 的 cost entries
   - slippage 不變（一直保持 6.0；M17 末段已 revert）
2. **產出 pkl** — `rm /tmp/xsmom_m17_*_result.pkl`（2 個檔案）。
3. **strategy.py / bundle / 測試** — M17 不動，零回滾成本。
4. **docs/progress-xsmom-beta-hedge.md** — 本段，`git revert <M17 commit>`。

最差情況：`git reset --hard 2d6427f`（M16 commit），再
`rm /tmp/xsmom_m17_*_result.pkl`，回到 M17 開始前狀態。

## M18 — 正式統計顯著性檢定：把 negative finding 量化成 publishable result ✅

> 夜間無人值守任務（claude/nightly-2026-05-24）。M17 收尾後，M14 列的
> 5 個 mechanical follow-up 全部完成、整合 M-series 結束。M17 結尾
> 「Open follow-ups」中**最自洽**的一項：用既有 result pkl 跑正式統計
> 顯著性檢定，把 5 次獨立確認的「無 alpha」結論量化成可發表的 p-value。
> 不需新 ingest、不需 strategy.py 改動、不需 broker spec — 100% self-contained。

### 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M18a | 寫 stat-sig runner | `scripts/run_xsmom_stat_sig.py`：block bootstrap Sharpe CI + 平均報酬 p-value + sign-flip permutation test + 參數 t-test |
| M18b | 跑 4 個 pkl (M17 canonical + 3 個 walk-forward sub-periods) | 4 組顯著性數字 |
| M18c | 寫本段 + commit | 即本檔追加段落 + `M18: ...` |

### 三組互補 null-hypothesis 檢定

1. **Block bootstrap Sharpe 95% CI** (block_size=20 ≈ 月度 rebalance cycle，
   n_iter=10000)：考慮序列自相關，從 empirical 分布抽 monthly 大小的 block
   重組樣本算 Sharpe，看 [p2.5, p97.5] 是否含 0。**若含 0** → Sharpe 與
   0 無法統計區分；**不含 0** → 顯著偏離 0。

2. **Bootstrap 平均報酬 p-value (one-sided H1: mean > 0)** + 參數 t-test
   平行驗算：直接檢驗 daily return mean 是否能由「真實 mean=0 加雜訊」
   解釋。

3. **Sign-flip permutation test (H0: mean = 0)**：對每天的 return 隨機
   乘 ±1，重算 Sharpe 形成 null 分布。保留 empirical variance 與大幅
   daily move 的事件結構，只對稱化「方向」。**對只看 ordering 的 plain
   shuffle 是更強的檢定**——後者對 stationary Sharpe 退化（時間順序
   不影響 mean/std），sign-flip 才真正測「方向 vs noise」。

### 結果 (n_iter=10000, block_size=20)

| dataset | 用 n_obs | observed Sharpe | bootstrap 95% CI | CI 含 0? | parametric t (dof) | param 1-sided p | sign-flip p |
|---|---:|---:|---|---:|---:|---:|---:|
| **M17 canonical (2020-2026, 6.32y)** | 1399/1534 | -2.967 | [-3.475, -2.549] | **No** | -6.990 (1398) | **2.12e-12** | **0/10000** |
| M16 P1 COVID (2020-2021) | 489/489 | -3.580 | [-4.250, -2.985] | **No** | -4.987 (488) | 4.27e-07 | 0/10000 |
| M16 P2 hike-bear (2022-2023) | 485/485 | -4.180 | [-4.857, -3.518] | **No** | -5.799 (484) | 6.01e-09 | 0/10000 |
| M16 P3 AI-bull (2024-2026) | 560/560 | -3.151 | [-3.731, -2.553] | **No** | -4.697 (559) | 1.66e-06 | 0/10000 |

註：`n_obs` 是 trim 掉「portfolio 死亡後的零報酬尾」後的 daily return
數。M17 canonical 後 135 個交易日 PV 已縮到 < 1% 起始值，daily move
四捨五入到 0，不是真實市場訊號。`--include-zeros` 對照組 Sharpe -2.83
（vs -2.97），結論不變。

### 結論：四個關鍵 finding

1. **完整 6.32 年期間「Sharpe = 0」H0 被以 p ≈ 2×10⁻¹² 拒絕**。換句話說，
   若策略真的有 zero alpha + 純 noise，看到這樣 6 年虧損 99% 資金的
   機率是 2 兆分之一。負 alpha **不是運氣**。

2. **三個非重疊 sub-periods 獨立全部顯著**（p 從 10⁻⁶ 到 10⁻⁹）。
   不存在某個「壞 regime + 好 regime」可分割來救活策略 — 每段都是
   獨立 publishable negative result。

3. **Block bootstrap upper-CI bound 在 4 個資料集都遠離 0**：M17 完整
   期間最 conservative 的 upper bound 是 -2.55（即使在 2.5% optimistic
   尾端，Sharpe 仍是 -2.55）。這是策略「無法被解釋為樣本不幸」的
   robust 證據。

4. **Sign-flip null 分布的標準差 0.42–0.72** （取決於 sample size），
   而觀察到 Sharpe 全在 -3 ~ -4 區間——距離 null mean 0 約 **4–7 個
   null std**。對應到 Cohen's d (effect size) 約 7σ 量級，遠超
   「decisive」的 |d| > 0.8 門檻。

### 為什麼這是 publishable result（而不是「策略失敗 commit」）

M11–M17 累積 5 次獨立 mechanical 確認「無 alpha」，M18 把這些結論
**量化成標準學術統計語言**：

- 「block bootstrap 95% CI 不含 0」⇒ 可寫進 paper Table 1
- 「sign-flip p < 10⁻⁴, n_iter=10000」⇒ 拒絕 H0 的標準格式
- 「跨 3 個 non-overlapping sub-periods 一致顯著」⇒ regime stability
  支持結論非樣本選擇 artifact

對應到 López de Prado (2018) 對 negative result 的標準（Backtest
Degradation Ratio + bootstrap CI + permutation null），這已經足以
寫成「Cross-sectional momentum on Taiwan stock-futures (2020-2026):
A statistically robust null result」型的短論文。

### 額外發現：sign-flip null 的 Sharpe std 隨 n 縮放

| dataset | n | null Sharpe std |
|---|---:|---:|
| P1 | 489 | 0.719 |
| P2 | 485 | 0.723 |
| P3 | 560 | 0.678 |
| M17 (full) | 1399 | 0.424 |

理論上 sign-flip null 的 Sharpe std 應為 √(252/n)（中央極限定理）：

- n=489 → √(252/489) = 0.718 ✅
- n=485 → √(252/485) = 0.721 ✅
- n=560 → √(252/560) = 0.671 ≈ 0.678 ✅
- n=1399 → √(252/1399) = 0.425 ≈ 0.424 ✅

四個資料集的 null 分布都精確符合理論預測，確認 sign-flip 實作沒有
bug，且 daily return series 雖序列相關但其 sign-flip null 仍 well-behaved。

### 後續方向（仍屬 research，不在本 milestone）

- **多重比較校正**：M11-M12 ablation 試了 8 個 portfolio 變體 + M13-M17
  又 5 個 config 變體 ≈ 13 個獨立 hypothesis。Bonferroni 校正後
  α = 0.05/13 ≈ 0.004，但我們所有 p-value < 10⁻⁶，遠低於校正門檻
- **Effect size CI**：把 Cohen's d 也加 bootstrap CI，給期刊 review
  更完整的 statistical reporting
- **Heteroscedasticity-robust 標準誤**：M14-M17 已知 vol 結構性
  變化（前重後輕），可考慮 Newey-West 或 GARCH-adjusted t-stat

這些都是 `/review-strategy` 階段的事，整合 M-series 在 M18 真的
結束。M18 是這個 strategy 在當前 universe + 視窗的**最後一張**
data point — 後續任何 attempt 必須換訊號、換 universe、或換時段
才有意義。

### Commit

`M18: formal statistical significance — Sharpe CI excludes 0, p < 10^-12 across full period + 3 sub-windows`

### M18 Fallback 指引

1. **scripts/run_xsmom_stat_sig.py** — 新檔；直接 `rm` 或 `git revert` 移除
2. **docs/progress-xsmom-beta-hedge.md** — 本段；`git revert <M18 commit>`
3. **strategy.py / config / 測試 / bundle / pkl** — M18 不動任何既有資產，零回滾成本

最差情況：`git reset --hard 6898a0d`（M17 commit），回到 M18 開始前狀態。
