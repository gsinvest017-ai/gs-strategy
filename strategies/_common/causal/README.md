# `_common/causal/` — 因果因子去過擬合 loop

Survey gap #1 的落地骨架（見 `docs/survey-quant-frontier-2026-06.md`）。把「因子 → 真的有效應，還是共同衝擊造成的偽相關」做成可重用、可 pass/fail 的測試。

## Loop（2026-09 校準版）

```
factor panel（股票 × 期間）
  → dag.select_confounders          一律保留預先登錄的全部控制變數（PC 圖只作診斷，dag_diagnostics）
  → dml.estimate_factor_effect      交叉擬合部分線性 DML；cluster=期間 → 依期間 cluster 的標準誤
  → dml.estimate_effect_by_period   每期一個斜率（Fama–MacBeth），Newey–West t
  → refute.refute_factor            互不重疊的時間區塊內各自估計，方向一致比例 ≥ 0.7
  → pipeline.causal_factor_verdict  PASS / CONDITIONAL / FAIL
```

判定規則：

| 判定 | 條件 |
|---|---|
| PASS | 依期間 cluster 的 DML p < 0.05，**且**逐期斜率 NW \|t\| ≥ t 臨界值、方向相同，**且**時間區塊方向一致 |
| CONDITIONAL | 顯著但區塊方向不一致；或沒有提供 `time_col`（標準誤假設列獨立） |
| FAIL | 上面兩道顯著性檢定任一沒過 |

**面板一定要傳 `time_col`**，否則判定最高只到 CONDITIONAL。

## 為什麼改（舊版會讓雜訊過關）

2026-09-15 兩份獨立審查（gs-ai-capex-cycle `reviews/`）在台股股票×月面板上發現：

1. **iid 標準誤**：同一期間的股票共享市場、產業衝擊。若處置變數與報酬各自帶有期間（或產業×期間）共同成分，真正的變異數是 iid 公式的 design effect 倍：`1 + (m−1)·ρ_d·ρ_u`（m＝每群列數、ρ＝群內相關），t 值被放大 √DE 倍。實測 iid／cluster 標準誤比 1.9–2.3 倍，純雜訊因子 iid 拒絕率 33%–63%。
2. **PC 縮減控制變數**：PC 的條件獨立檢定同樣假設 iid；而且丟掉真正的混淆變數會帶回遺漏變數偏誤，選擇後推論也不成立。現在控制變數只能加、不能被資料刪。
3. **DoWhy 三項反駁沒有檢定力**：placebo 在任何資料生成過程下期望值都是 0；random common cause 與 D、Y 獨立，估計值只動 O(1/√n)；data subset 估同一個機率極限。三者都沿用 iid 列結構，是被審查統計量本身的函數。現在只經 `dowhy_auxiliary` 提供描述性輸出，不作門檻。

校準測試：`tests/test_causal_calibration.py`（產業×期間雜訊因子的 PASS 率必須 ≤ 15%，真效應必須 PASS）。

## 跑 PoC

```bash
cd /home/kevin/gs-strategy
python -m strategies._common.causal.examples.causal_poc
```

合成面板含一個真效應因子與一個經由 `macro` 混淆的偽相關因子；正確的 loop 應 PASS 前者、FAIL 後者。

## 依賴

- 必要：numpy、pandas、scipy。
- 建議：scikit-learn（`learner="rf"`／`"lasso"`；沒有時退回 OLS nuisance，`method` 會標 `linear_fallback`）。
- 選配：causal-learn（`discover=True` 時的 PC 診斷）、DoWhy（`dowhy_auxiliary`）。

## 與 validation 搭配

`causal` 檢查效應是否穩健，`_common/validation/` 檢查過擬合：

- `pbo(..., metric="sharpe")`：預設以 Sharpe 評分。舊版以平均報酬評分，會一直選到波動最大的設定。
- `block_sharpes`：沒有參數的策略，改報不重疊區塊的 Sharpe，不要把 CPCV 測試段 Sharpe 當樣本外證據。
- `dsr_sr_variance`、`effective_n_trials`、`min_track_record_length`：DSR 的變異數規則、有效試驗數與最短樣本長度。
