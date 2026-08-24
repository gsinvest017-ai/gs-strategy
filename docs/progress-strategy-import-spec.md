---
type: progress
updated: 2026-05-26
repos: [gs-strategy]
owner: gsinvest017-kevin
---

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

### M1 — 計畫 + 進度檔 ✅

建立本檔，commit `8f6bb71`。

### M2 — 轉檔器 + validator ✅

- `scripts/config_to_manifest.py` — config.yaml → manifest.yaml
  - 從 strategy.py docstring 抓 `arxiv NNNN.NNNNN` 自動填 paper 資訊
  - `--all` 一次掃整個 `strategies/`、`--force` 覆寫人工編輯、
    `--dry-run` 預覽、`--generated` 標 source.kind=generated
  - 預設 idempotent：保留手動編輯的欄位
- `scripts/validate_dashboard_bundle.py` — bundle 合規檢查
  - 涵蓋 spec §2 全部 validation rules + §3.3 forbidden imports
  - AST-scan strategy.py 確保沒有 `from _common.*` 或 relative imports
  - 用 subprocess 隔離 import 測試，繞過 zipline C-ext 不能重複載入的問題

Commit: `M2: add manifest converter + dashboard bundle validator scripts`

### M3 — 移除 sibling imports ✅

- 把 `strategies/_common/futures_setup.py` 複製成每個 bundle 的
  sibling `futures_setup.py`（4 份）
- 改 4 個 strategy.py 的 import：
  - 刪掉 `_HERE/_PARENT/sys.path.insert` hack（spec §3.3 禁止 module-load
    side effect）
  - 改 `from _common.futures_setup import` → `from futures_setup import`
- 驗證：(a) dashboard-style import (`sys.path=[bundle_dir]`) 4 個都過；
  (b) 舊 runner.py 因為也 insert bundle_dir，繼續能跑

Commit: `M3: each bundle owns futures_setup.py, drop sibling _common import`

### M4 — 4 個 manifest.yaml 全部 pass validator ✅

- 跑 `scripts/config_to_manifest.py --all` 產生 4 個 manifest.yaml
- 修 converter bug：sibling `futures_setup` 不該被列為 pip extra_dep；
  改成過濾 bundle-local `*.py` 檔
- 人工打磨 4 個 manifest 的 `name` / `description` / `source.inputs.paper`：
  - `vgrsi_tx` → VGRSI on TX Futures (Rak 2026, arxiv 2605.01300)
  - `cubic_momentum_tx` → Cubic Momentum on TX Futures (Yoshida 2026, arxiv 2605.00854)
  - `tsmom_tx_mtx` → TSMOM on TX & MTX Futures (Moskowitz+ 2012, JFM 2026)
  - `xsmom_stkfut_rmt` → XSMOM on TW Stock Futures (Mukhia+ 2026, arxiv 2604.19107)
- validator 全綠

Commit: `M4: add manifest.yaml for 4 bundles + fix validator subprocess isolation`

### M5 — pytest 覆蓋 ✅

- `tests/test_dashboard_bundle.py` 11 個測試：
  - 每個 shipped bundle 跑一次 validator (parametrize over 4 bundles)
  - manifest schema 抽樣檢查（id, asset_class, params, source）
  - converter idempotency：手動編輯後再跑一次，使用者編輯被保留
  - converter `--force`：覆寫所有欄位
  - forbidden sibling import：validator 必須擋下 `from _common import`
- 修 `tests/test_strategy_math.py`：M3 import 改完後，test 也要 mirror
  dashboard driver 的 `sys.path=[bundle_dir]` 行為
- 把 pytest pip-install 進 `.venv-bt`（之前只有 `.venv` 有）
- 全 suite (`pytest tests/ -v`) 26 個測試全綠（不含需要 feedparser 的
  crawler tests，那組原本就要跑在 `.venv`）

Commit: `M5: pytest coverage for dashboard bundles + converter idempotency`

### M6 — README + 最終整理 ✅

- 更新 `strategies/README.md`：新增「Dashboard import 規格相容」段落，
  說明每個 bundle 結構、如何指向 dashboard、validator/converter 用法
- 補本檔的進度日誌

Commit: `M6: docs — strategies/README explains dashboard-spec compliance`

## 後續方向

1. **gs-scraper 整合**：在 `quant_crawler/` 加 `strategy_gen/` 子套件，
   讀 `data/papers.db` row → 呼叫 `scripts/config_to_manifest.py`
   生成 bundle dir。需要的模板已在 spec §8。
2. **沒做的部分**：
   - `provenance.json` sidecar（spec §7）— 等真的需要 audit trail 再加
   - 多 bundle 同時做 hyperparameter sweep — spec 明示 v1 不支援
   - 共用 helper 的 sync script (`scripts/sync_futures_setup.py`)：
     目前 4 個 bundle 各自 copy，未來如果改 helper 要手動同步。短期可接受。

## Fallback 指引 (final)

最常見的回滾路徑：

1. 若 dashboard import 路徑壞掉但 backtest 仍要跑：strategy.py 仍能被
   `strategies/_common/runner.py` 載入。直接：
   ```
   TEJAPI_KEY=... ./scripts/run_strategy.sh vgrsi_tx
   ```
2. 若手動編輯過的 manifest 被 converter 覆蓋：
   ```
   git diff HEAD strategies/<bundle>/manifest.yaml   # 確認受影響欄位
   git checkout HEAD strategies/<bundle>/manifest.yaml
   ```
3. 整段功能回滾：`git revert <M6-commit>..<M2-commit>` 或
   `git reset --hard 2a29b7f`（M19 commit）。
