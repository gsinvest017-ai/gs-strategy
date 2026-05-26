# Strategy Import Spec Compliance — gs-strategy → gs-zipline-tej dashboard

> 把本 repo 的 4 支既有策略（`strategies/{vgrsi_tx, cubic_momentum_tx,
> tsmom_tx_mtx, xsmom_stkfut_rmt}/`）改造成符合
> `~/gs-zipline-tej/docs/strategy-import-spec.md` v1 規格的 bundle，
> 同時提供一支轉檔器，給後續 paper-crawler → strategy-gen pipeline 用。

## 目標

讓 dashboard 透過 `DASHBOARD_STRATEGY_DIRS=$HOME/gs-strategy/strategies`
（或預設 `<repo>/strategies/` scan）直接認得這 4 支策略，並把
`~/gs-strategy/quant_crawler` 未來自動產生的策略以同一份 layout 寫出去。

成功條件：
1. 4 個 bundle dir 各有 `manifest.yaml`，passes 規格 §2 全部 validation rules
2. `strategy.py` import 不再依賴 sibling `_common/` package（spec §3.3）
3. `strategy.py` 仍然能被 `strategies/_common/runner.py` 跑（既有工作不破壞）
4. 一支自動化 validator 能 lint 任意 bundle dir 是否合規
5. 一支轉檔器 `scripts/config_to_manifest.py` 可以把舊式 `config.yaml`
   翻成新的 `manifest.yaml`，後續爬蟲產生器直接呼叫即可
6. pytest 覆蓋 (a) validator (b) 4 個 bundle 都能 dashboard-style import

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + plan | 本檔 |
| M2 | 轉檔器 + validator | `scripts/config_to_manifest.py`, `scripts/validate_dashboard_bundle.py` |
| M3 | 移除 sibling import | 把 `_common/futures_setup.py` 複製進每個 bundle、改 strategy.py import |
| M4 | 4 支策略 manifest.yaml | `strategies/<name>/manifest.yaml` × 4，全部 pass validator |
| M5 | smoke test + pytest | dashboard-style driver 驗證 import + `tests/test_dashboard_bundle.py` |
| M6 | README + 最終報告 | 更新 strategies/README、commit summary |

## 設計決策

### 1. In-place 改造 vs 平行 dist/

選 **in-place**。理由：
- spec §6 預設 scan `<repo>/strategies/`，把 manifest.yaml 直接放進現有
  bundle dir 最自然
- 既有 runner.py 與新 dashboard driver 都用 `sys.path.insert(0, bundle_dir)`
  + 讀 `context.params`，schema 同源、不需要兩份
- 避免 dist/ 內容跟原始檔案 drift

### 2. 共用 helper 怎麼處理

spec §3.3 明文「strategies MUST NOT `from other_bundle import`」。
4 支策略目前都 import `_common.futures_setup`（apply_taiwan_futures_costs /
make_continuous_taiwan_futures / make_roll_futures_handler）。

選方案 **(B) 每個 bundle 自帶副本**：
- 把 `_common/futures_setup.py` 複製為各 bundle 的 sibling `futures_setup.py`
- strategy.py 改 `from futures_setup import ...`（刪掉 sys.path hack）
- bundle 變自包 (self-contained)，符合 spec §4「sys.path 只有 bundle dir」
- 既有 runner.py 因為也 insert `bundle_dir`，仍然能 resolve

未來如要更新 helper，寫一支 `scripts/sync_futures_setup.py` 從 canonical
source 同步到每個 bundle。短期暫不寫，待第二份 helper 出現再抽出。

替代方案 (A)「把 helper 全 inline 進 strategy.py」直接 reject — 4 份複製
等於 4 處要同步維護，比方案 B 還糟。

### 3. params 欄位完全保留

spec §3.4 + §2 允許 `params: {}` free-form。直接把舊 config.yaml 的
`params:` 整塊複製進 manifest，dashboard 端 JSON editor 仍可 override。

### 4. 新增的 meta 欄位來源

| Manifest field | 來源 |
|---|---|
| `id` | bundle dir name (`vgrsi_tx` 等) |
| `name` | bundle dir 的 README h1 / 手動填 |
| `description` | strategy.py docstring 第一段或 README 開頭 |
| `asset_class` | bundle 名 = future bundle → `future`，其餘 `equity` |
| `tags` | 從目錄名 + 訊號類型推斷（momentum/futures/taiwan/...） |
| `requires_tej_key` | bundle = `tquant*` → `true` |
| `extra_deps` | 掃 strategy.py import，過濾掉 stdlib/numpy/pandas/scipy/zipline |
| `symbols` | 從 params.roots / root_symbol / universe_roots 抽 |
| `source.kind` | 預設 `manual`（手寫從 paper），轉換器允許 override |
| `source.inputs.paper.arxiv` | 從 strategy.py docstring 抓 `arxiv \d{4}.\d{5}` |

## Fallback 指引

如果中途要回滾或交接：

1. **進度本身**：本檔記錄每個 milestone 的 commit hash 與檔案清單
2. **回滾 strategy.py import 改動**（M3）：
   - `git revert <M3 commit>` 把 strategy.py 拉回 `_common.futures_setup`
   - 刪除各 bundle 內的 `futures_setup.py` 副本
3. **回滾 manifest.yaml**（M4）：直接 `rm strategies/*/manifest.yaml`
4. **回滾 converter/validator scripts**（M2）：`rm scripts/config_to_manifest.py scripts/validate_dashboard_bundle.py`
5. 最差情況：`git reset --hard 2a29b7f`（M19 commit），回到 M-series 結束點

## 進度日誌

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
