---
type: progress
updated: 2026-05-27
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# Strategy Category Taxonomy + Tag Enrichment

> 接續 `progress-strategy-import-spec.md`（4 支 bundle 改 spec v1）與
> `progress-daily-strategy-gen.md`（每日自動產生 skeleton bundle）。本任務
> 把「策略分類標籤」做成系統化 taxonomy，套到自動產生 + 手寫 bundle，讓這些
> tag 流進 gs-zipline-tej dashboard 的 search panel 做模糊搜尋。

## 關鍵前置調查結論

**dashboard 端已經完整支援 tag → search，不需要改 gs-zipline-tej。**

| 能力 | 狀態 | 證據 |
|---|---|---|
| 讀 manifest `tags` | ✅ | `dashboard/strategies/importer.py:126-128`、`registry.py:103` (StrategyMeta.tags) |
| API 回傳 tags | ✅ | `dashboard/app.py:62` `/api/strategies` 回傳完整 StrategyMeta |
| search panel 模糊搜尋 tags | ✅ | `dashboard/static/main.js:168` searchHaystack 把 `s.tags` 併入；fuzzyMatch 多 token AND substring |
| card 顯示 tags | ✅ | `main.js:136-142` 渲染 `.card-tags` |

→ 換句話說：**只要我們在 producer 端輸出好的 tags，dashboard 零改動就能搜。**

## 問題：producer 端 tagging 太淺

目前（`classify.py`）每個 template 只給 1-2 個 tag：
- momentum → `("momentum",)`
- mean_reversion → `("mean-reversion", "technical")`
- buy_and_hold → `("baseline", "buy-and-hold")`

4 支手寫 bundle 的 tags 也是手填、彼此不一致（technical / nonlinear / regime…
散落）。沒有共同詞彙表，模糊搜尋的命中率與一致性都差。

## 目標

建立一套**多維度 tag taxonomy**（family / signal / direction / instrument），
用 keyword→tag 規則從論文文字多標籤抽取，套用到：
1. 自動產生的 skeleton bundle（透過 generator）
2. 4 支手寫 bundle 的 manifest
並確認 dashboard importer 吃得到、search 搜得到。

### Tag 維度設計

| 維度 | 範例 tag | 說明 |
|---|---|---|
| `family` | momentum, trend-following, mean-reversion, breakout, pairs-trading, statistical-arbitrage, carry, value, factor, volatility, event-driven, market-making, arbitrage | 策略大類（多標籤） |
| `signal` | technical, fundamental, cross-sectional, time-series, regime-aware, machine-learning, sentiment, microstructure, graph-based | 訊號型態 |
| `direction` | long-only, long-short, market-neutral | 多空結構 |
| `instrument` | index-future, stock-future, single-stock | 交易標的型態 |

固定執行情境 tag（永遠加在自動產生 bundle）：`taiwan`, `futures`,
`paper`, `auto-generated`, `needs-review`。

論文本身的 region / asset-class（可能是 US equity）**不**放進 searchable tags
（bundle 實際上跑 Taiwan futures，放 `us` 會誤導搜尋），改放
`source.paper.categories` 供 audit。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + plan | 本檔 |
| M2 | taxonomy 模組 | `quant_crawler/strategy_gen/taxonomy.py` + tests |
| M3 | 接進 classifier/generator | generated manifest 帶 rich tags + tests |
| M4 | 套用到 4 支手寫 bundle + 端到端驗證 | 更新 manifest tags、確認 dashboard importer 解析得到 |
| M5 | docs + 報告 | README 更新、進度檔總結 |

## Fallback 指引

1. 回滾 taxonomy 但保留既有功能：`git revert <M3-commit>` 讓 generator 回到
   只用 template 的單薄 tags；`rm quant_crawler/strategy_gen/taxonomy.py`
2. 回滾手寫 bundle 的 tag 變更：`git checkout HEAD~ strategies/*/manifest.yaml`
3. 整段回滾：`git reset --hard 541099d`（daily-strategy-gen M5 commit）

## 進度日誌

### M1 — 計畫 + 進度檔 ✅

Commit `e15c142`：含 dashboard 端「已完整支援 tag→search」的前置調查結論
（不需改 gs-zipline-tej）、tag 維度設計、milestone 表、fallback。

### M2 — 多維度 taxonomy 模組 ✅

- `quant_crawler/strategy_gen/taxonomy.py`：
  - 6 個維度（family / signal / direction / instrument / region / asset_class），
    每個維度多標籤 keyword→tag，pattern 全部預編譯
  - `extract_tags(paper, dimensions)` 回每維度命中 tags；
    `flat_tags(paper, dimensions)` 攤平去重（預設只 family/signal/direction）
  - `TAG_VOCABULARY` frozenset 供驗證/列舉
  - 保守 pattern 防 false positive：bare "value"/"graph"/"us" 不命中，
    需 qualified phrase（"value premium" / "visibility graph"）
  - region/asset_class 預設**不**進 bundle tags（bundle 跑 Taiwan futures，
    放論文本身的 "us" 會誤導搜尋）
- `tests/test_taxonomy.py` 11 個測試全綠（多標籤、優先序、false-positive guard、
  region 不外洩、vocabulary 完整性）

Commit: `M2: multi-dimensional strategy-category tag taxonomy`

### M3 — 接進 generator ✅

- `generate.py` 新增 `assemble_tags(paper, classification)`：
  fixed 執行 tag + instrument(由 root 推 index/stock-future) + taxonomy
  flat_tags + template 原 tags，去重保序
- manifest_ctx 的 tags 改用 `assemble_tags`
- CLI 加 `--list-tags` 印完整 42-tag 詞彙表
- 實測 xsmom-like 論文產出 tags：
  `[paper, auto-generated, needs-review, taiwan, futures, index-future,
    momentum, cross-sectional, regime-aware, long-short, market-neutral]`
- 新增 2 個 generator tag 測試；validator 對生成 bundle 仍 OK

Commit: `M3: wire taxonomy into generator — rich searchable tags + --list-tags`

### M4 — 套用到 4 支手寫 bundle + 端到端驗證 ✅

- 4 支 manifest 的 tags 改用統一詞彙：
  - `vgrsi_tx`: mean-reversion / technical / graph-based / time-series / long-only / index-future
  - `cubic_momentum_tx`: momentum / trend-following / volatility / regime-aware / long-short / nonlinear
  - `tsmom_tx_mtx`: momentum / trend-following / time-series / volatility / long-short
  - `xsmom_stkfut_rmt`: momentum / cross-sectional / regime-aware / market-neutral / long-short / stock-future
- **端到端驗證**：用 gs-zipline-tej **自己的** importer
  (`dashboard.strategies.importer._scan_one_dir`) 掃我們的 `strategies/`：
  4 bundles 0 failures，`StrategyMeta.tags` 帶完整 tags；`to_dict()`（API payload）
  也含 tags；模擬 main.js haystack 搜 `market-neutral` / `regime` /
  `cross-sectional momentum` 全部 HIT
- 4 支 validator 仍全 OK

Commit: `M4: apply taxonomy tags to 4 hand-authored bundles (verified via dashboard importer)`

### M5 — docs + 報告 ✅

- `strategies/README.md` 新增「策略分類標籤 (taxonomy)」段落（維度表 +
  `--list-tags` + 搜尋範例）
- 本檔進度日誌補完

Commit: `M5: docs — taxonomy section in strategies/README`

## 結論

- **不需改 gs-zipline-tej**：dashboard importer/registry/app/main.js 早就
  ingest + 模糊搜尋 manifest.tags。缺口純在 producer 端 tag 品質。
- 本任務把 producer 端 tag 升級成系統化多維 taxonomy，自動產生與手寫 bundle
  共用同一詞彙，並用 dashboard 自身 importer 證明 tag 端到端流通、可搜尋。

## 後續方向

1. 若日後 dashboard 想做 **tag facet 過濾**（點 tag chip 篩選而非打字），
   可在 `main.js` 加 chip click handler；tags 資料已就緒。
2. taxonomy 可擴充更多 family（如 `seasonality`、`liquidity`、`low-vol`）—
   在 `_RAW_DIMENSIONS` 加一列 + 補 `test_vocabulary_covers_all_emitted_tags`
   的 sample 即可。
3. 若把 rule-based classifier 換 LLM，taxonomy 仍可當「allowed tag 白名單」
   約束 LLM 只能從 `TAG_VOCABULARY` 選 tag，確保 search 一致性。
