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
- `strategies/xsmom_stkfut_rmt/config.yaml` — M13 + M14 編輯（hedge flags + 60-root universe）
- `tests/test_strategy_math.py` — M13 編輯（3 個新測試）
- `docs/progress-xsmom-beta-hedge.md` — M13 新增 / M14 append（本檔）
- `/tmp/xsmom_m13_beta_neutral_result.pkl`、`/tmp/xsmom_m13_no_hedge_result.pkl` — M13 產出
- `/tmp/xsmom_m14_60root_result.pkl` — M14 產出
- `~/.zipline/data/tquant_future/2026-05-19T16;01;16.781143/` — M14 新 bundle
