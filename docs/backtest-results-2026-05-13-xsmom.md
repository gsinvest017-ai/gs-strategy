# xsmom_stkfut_rmt — 第一次跑通 (2026-05-13)

跟著 M7/M8/M9 把 4 支策略的最後一支接上 `tquant_future` bundle。本檔只記錄
這次新增的執行結果與發現的 calibration 問題；其他三支策略的數字仍在
`backtest-results-2026-05-11.md`。

## 環境

- venv: `.venv-bt/` (與其他三支相同)
- bundle: `tquant_future`，本次 `FUTURES_ROOTS` 擴成 32 roots
  (TX + MTX + 30 個股期，root list 詳見 `data/stock_futures_universe.json` 的 `head` 切片)
- mdate: 2018-01-01 ~ 2026-05-10
- universe: 鎖在 config.yaml 的 30 個 roots（避免 auto-discover 撞 SymbolNotFound）
- start/end: 2020-01-02 ~ 2026-04-30 (6.32 年)
- capital_base: 30,000,000 NTD

## 重現命令

```bash
# 1. (一次性) ingest 含 30 個股期的 bundle
FUTURES_ROOTS="TX MTX CAF CBF CCF QFF CEF CFF CGF CHF CJF CKF CLF CMF CNF CQF \
    CRF CSF CUF CWF CXF CYF CZF DAF DBF DCF DDF DEF DFF DGF DHF DIF" \
MDATE="20180101 20260510" ./scripts/ingest_futures.sh

# 2. 跑策略
./scripts/run_strategy.sh xsmom_stkfut_rmt /tmp/xsmom_stkfut_rmt_result.pkl

# 3. 摘要
.venv-bt/bin/python scripts/summarize_results.py \
    /tmp/xsmom_stkfut_rmt_result.pkl --markdown
```

## 結果

| name             | start      | end        |  years | capital_base |   final | total_return | CAGR    | ann_vol | Sharpe | Max_DD  | n_tx |
|:-----------------|:-----------|:-----------|-------:|-------------:|--------:|:-------------|:--------|:--------|-------:|:--------|-----:|
| xsmom_stkfut_rmt | 2020-01-02 | 2026-04-30 |   6.32 |   30,000,000 | 584,284 | **-98.05%**  | -46.35% | 19.00%  | -3.302 | -98.05% |  565 |

策略**慘賠**。但這是 calibration 問題，不是 integration 問題；M9 的目標
（跑通 pipeline、拿到 metrics）已達成。

## 慘賠原因 — RMT gap 閾值與 universe 規模不匹配

從 result.pkl 解出來：

- `n_universe`: 24-30（30 個 root 都跑得起來，符合 `min_universe: 20`）
- `gap` 統計（1534 個交易日全有值）:
  - mean: **0.050**
  - min:  0.020
  - max:  **0.097**
- `regime_scale` 分佈:
  - `0.0`: 784 天 (51%) — gap < 0.05 直接 de-risk 到零
  - `0.5`: 750 天 (49%) — gap 在 [0.05, 0.20]，半倉
  - `1.0`: **0 天** — gap 從未 ≥ 0.20，永遠進不了全倉

config 給的 `rmt_threshold: 0.20` / `rmt_low_threshold: 0.05` 顯然是論文 G5 全市場
50+ 資產的尺度；換到我們 30 檔藍籌的縮小宇宙，gap 自然壓縮。實際上策略就在
「半倉做 momentum」與「現金為王」之間 toggle，沒享受到趨勢 + 又付足滑價與 commission。

## 後續修正方向（屬於 /review-strategy 範疇，這次先不動）

1. **重新校準 gap 閾值**：用 `regime_scale=1.0` 落在分佈上分位（e.g. 75th percentile）
   反推 `rmt_threshold`，用中位數附近反推 `rmt_low_threshold`。
2. **擴大 universe**：ingest top 60-100 個股期讓 N 更大、gap 更接近論文尺度。
3. **驗證 long_decile / short_decile 在 N=30 是否合理**：n=30、decile=0.1
   → `n_long=n_short=3`，部位太集中。或許改 0.2 decile（6 vs 6）比較合理。
4. **TX hedge 是否反向放大虧損**：`hedge_with_tx: true` 時 net beta 應該歸零，
   但 -98% 的下檔說某些日子根本沒成功 short TX。需要 transaction-level 檢查。

## 已知 caveats

- Universe 鎖死 30 個 root 在 config 是工程妥協；論文的精神是「全宇宙動態取樣」。
  若要忠實重現，需先 ingest 257 個 root（TEJ API 流量很大，夜間預算內跑不完）。
- 跑出 4 種 schedule_function 警告（gap < 0.05 時 `_flatten_all` 反覆下零單），
  不影響正確性但會讓 trade count 略偏高。
