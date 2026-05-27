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

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
