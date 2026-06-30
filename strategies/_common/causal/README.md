# `_common/causal/` — 因果因子去過擬合 loop

Survey gap #1 的落地骨架（見 `docs/survey-quant-frontier-2026-06.md`）。把「因子 → 真因果還是偽相關」做成一條可重用、可 pass/fail 的測試，對抗 overfitting。

## Loop

```
factor panel
  → dag.select_confounders     (causal-learn PC，選要 control 的混淆變數)
  → dml.estimate_factor_effect (DoubleML 估因果效應 + 信賴區間)
  → refute.refute_factor       (DoWhy placebo / random-cc / subset 反駁)
  → pipeline.causal_factor_verdict → PASS / CONDITIONAL / FAIL
```

## 設計原則

- **adopt 既有庫**：DoubleML（BSD-3）、causal-learn（MIT）、DoWhy（MIT）。
- **每個重套件都 optional import**：沒裝也能跑——退化成 numpy/scipy fallback（FWL 偏相關 + permutation/bootstrap 反駁）。
- **零 zipline 耦合**：只吃 `pandas.DataFrame`（欄＝forward return／factor／confounders）。因此**可直接上移** `gs-quant-common`（gs-common-lift 報告建議：勿稀釋 gs-common 的 infra 定位）。

## 跑 PoC（今天就能跑）

```bash
cd /home/kevin/gs-strategy
python -m strategies._common.causal.examples.causal_poc
```

合成資料含一個真因果因子與一個經由 `macro` 混淆的偽相關因子；正確的 loop 應 PASS 前者、FAIL/CONDITIONAL 後者。

## 啟用完整路徑（adopt 真套件）

```bash
pip install doubleml scikit-learn causal-learn dowhy
```
裝好後 `method` 欄會從 `*_fallback` 變成 `doubleml` / `dowhy`，identification 更嚴謹。

## 接真實因子（下一步）

把 `tsmom_tx_mtx` 的因子值與 forward return 對齊成 panel（用 alphalens-reloaded 產生因子/分位／IC），confounders 放 TWD 匯率、美股隔夜、類股動能等。詳見 survey 報告第六節步驟 1。

## 與 validation 搭配

`causal` 判因果，`_common/validation/` 判過擬合（CPCV／Deflated Sharpe／PBO）。一支因子要進策略，建議兩關都過：因果 PASS + DSR P(skill) 夠高。
