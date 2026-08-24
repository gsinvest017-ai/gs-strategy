# Strategy Form Templates（Phase 0）

對應 `~/gs-zipline-tej/docs/strategy-import-spec.md` **v1.2 §13** 的
`strategy_form` 分類。每個子目錄是可複製的骨架（`config.yaml` +
`strategy.py`），沿用 `_common/runner.py` 執行慣例。

`trend` 形式不另設模板——直接複製現行四支期貨策略之一即可。

## 使用方式

```bash
cp -r strategies/_templates/xs_multifactor strategies/my_xs_strat
# 編輯 config.yaml 的 start/end/bundle/params，補完 strategy.py 的 TODO
./scripts/run_strategy.sh my_xs_strat
```

注意：

- 模板目錄用 `config.yaml`（runner 慣例），**不含** `manifest.yaml`，
  dashboard 掃描時不會誤認為可載入 bundle。
- `strategy.py` 保持 import 無副作用；所有參數從 `context.params` 讀
  （dashboard 匯入後可被 UI 覆寫）。
- 各形式的上游來源與契約細節見 spec v1.2 §13 對照表。
- `assets/*.csv` 是 spec §3.3 允許的 bundle-local sidecar（事件表、
  regime 權重），換成真實匯出物時保持檔名或改 `config.yaml` 路徑。

## 形式一覽

| 目錄 | strategy_form | 上游來源 | 適用場景 |
|---|---|---|---|
| `xs_multifactor/` | `xs_multifactor` | Factor--FORGE 因子 + gs-MINT 存活者權重 | 股票橫斷面 topN / 多空 |
| `timing_legs/` | `timing_legs` | gs--Market-Timing（合成 gate → 准入 legs） | 分批進場擇時 |
| `event_driven/` | `event_driven` | GS-insider-ownership（MOPS 申報事件） | 事件日 ± N 日窗口 |
| `tail_hedge_short/` | `tail_hedge_short` | gs-bulltrap-short（假突破放空） | 個股期尾部避險 |
| `regime_overlay/` | `regime_overlay` | gs-E-risk（risk_ew 狀態機權重） | 宏觀風控縮放基礎訊號 |

factor-filter 形狀不需模板——走 gs-zipline-tej Factor Pool 的
qualified 流程（spec §12.4）。多頻率變體以 `rebalance:` 參數表達。
