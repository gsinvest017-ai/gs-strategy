# progress-form-templates

Phase 0（定約）— 策略形式模板骨架。
Branch: `dev/strategy-form-templates`

## 目標

依 gs-zipline-tej `strategy-import-spec.md` v1.2 §13 的形式分類，在
`strategies/_templates/` 提供五種新策略形式的可複製骨架
（config.yaml + strategy.py），讓協作 repo（FORGE / MINT /
Market-Timing / Insider-ownership / bulltrap-short / E-risk）的策略
能以統一模板流入本 repo 與 dashboard。

## 計畫 milestone

- [x] **M2** — 新增 `strategies/_templates/{README.md,
  xs_multifactor,timing_legs,event_driven,tail_hedge_short,regime_overlay}/`
  骨架 + assets 範例 CSV；全數 strategy.py 通過 `py_compile`、
  config.yaml 通過 yaml.safe_load。對應 spec v1.2 由
  gs-zipline-tej `dev/spec-v12-strategy-forms` 分支承載（M1）。
- [x] **M3** — 交叉驗證通過（2026-08-24）：spec §13 表格路徑 ↔
  `_templates/` 實際目錄 5/5 對應；config `strategy_form` 值域 5/5 合規；
  py_compile 與 yaml parse 全綠。spec 端 commit：
  gs-zipline-tej `0748d9b`（dev/spec-v12-strategy-forms）。

## 進度日誌

### M2 — 五形式模板落地

- 形式與上游對應：
  - `xs_multifactor` ← Factor--FORGE 因子 + gs-MINT 存活者權重；
    內建 12-1 momentum placeholder signal、topN / 多空 / equal weighting。
  - `timing_legs` ← gs--Market-Timing 分批進場；gate score 佔位為
    20 日趨勢，cooldown / exit_score / n_legs 參數化。
  - `event_driven` ← GS-insider-ownership 事件窗口；
    `assets/events.csv` sidecar（date,symbol,direction,strength）。
  - `tail_hedge_short` ← gs-bulltrap-short 假突破放空；
    IDLE→SHORTED→分批減碼狀態機，前高停損。
  - `regime_overlay` ← gs-E-risk risk_ew 權重縮放基礎訊號；
    `assets/regime_weights.csv` sidecar。
- 決策：模板用 `config.yaml`（runner 慣例）、不含 manifest.yaml，
  避免 dashboard 掃描誤認；import-safe（無 module-level side effect）；
  所有參數走 `context.params`。
- 已知 TODO（Phase 1+）：signals 因子接線、liquidity floor 接 volume、
  tz 對齊 TEJ 行事曆、Monte Carlo 資金控管參數化。

## Fallback 指引

- Rollback：`git checkout HEAD~1 -- strategies/_templates docs/progress-form-templates.md`
  （或刪除 `_templates/` 目錄即可——全新檔案，不影響既有四支策略）。
- 接手者需知：spec v1.2 文件在另一個 repo
  （gs-zipline-tej `dev/spec-v12-strategy-forms` @ `0748d9b`），
  兩邊需一起 review 才構成完整 Phase 0。
