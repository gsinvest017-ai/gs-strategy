# Daily Paper → Strategy Bundle Auto-Gen Pipeline

> 接上 `progress-strategy-import-spec.md` (M1-M6) 的後續工作。前者把 4 支
> 已存在策略改造成 dashboard-spec v1 相容，本任務寫出**自動產生新 bundle**
> 的 pipeline，並排到每日 cron 跑。

## 目標

每天自動：
1. 跑 `quant-crawl run` 抓最新論文 / 機構報告（已有，6 個來源）
2. **新增**：從 `papers.db` 挑出今天新進、relevance pass 的論文
3. **新增**：依關鍵字分類成 `momentum` / `mean_reversion` / `buy_and_hold` 模板
4. **新增**：用 jinja2 渲染成 dashboard-spec v1 相容 bundle (manifest.yaml + strategy.py + futures_setup.py)
5. **新增**：把 bundle 寫到 `strategies/_generated/<paper_slug>/`，並標
   `requires_review: true`，由人工 review 後升級到正式區
6. 把整條 pipeline 串成 `scripts/daily_refresh.sh`，並寫一支
   `scripts/install_daily_refresh.sh` 把 cron 安裝指令包好（最後**不**自動跑）

## 範圍邊界（誠實的範圍宣告）

把任意論文翻成「真的有 alpha 的策略碼」是 open research problem。本 pipeline
**只產 skeleton**：

- 分類器 rule-based，只認得 ~6 個關鍵字桶（momentum / trend / mean-rev /
  rsi / pairs / buy-and-hold fallback）
- 每個模板 strategy.py 是「能 import、能被 zipline 跑、但 trade size = 0」
  的占位骨架；只把 paper-suggested params（如 lookback, threshold）填進
  `manifest.params`，由人工 review 補完訊號邏輯
- 加 `manifest.requires_review: true` (spec 沒這欄，是擴充)，讓 dashboard
  可以 surface「待 review」徽章

這個範圍：
- ✅ 證明 pipeline 端到端能跑（爬→過濾→分類→產 bundle→validate 通過）
- ✅ 給 dashboard 一個增長中的 strategy pool
- ❌ 但**不會自動產生 production-ready 策略** — 那是 human-in-the-loop

未來如果要把分類器升級為 LLM call，把 classify.py 換成
`generate_with_llm.py` 即可，整個 pipeline shape 不動。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + plan | 本檔 |
| M2 | 分類器 | `quant_crawler/strategy_gen/{__init__,classify}.py` + tests |
| M3 | 模板 + generator | `strategy_gen/templates/*.j2`, `strategy_gen/generate.py` + tests |
| M4 | daily_refresh shell pipeline | `scripts/daily_refresh.sh` + 一輪 dry-run smoke |
| M5 | install script + 報告 | `scripts/install_daily_refresh.sh`（不真的裝） + 本檔總結 |

## Bundle dir 規劃

| 路徑 | 用途 | dashboard scan? |
|---|---|---|
| `strategies/<id>/` | 人工維護的 4 支主策略（M-series） | ✅ |
| `strategies/_generated/<paper_slug>/` | 每日自動產生的 skeleton | ✅（dashboard 看到 `requires_review: true` 會顯示徽章） |

`_generated/` 用 `_` 開頭，避免被 `config_to_manifest.py --all` 當成人工 bundle
重新生 manifest（converter 已經 skip `_` 開頭目錄）。

## 命名規則

`paper_slug = f"{source}_{source_id_safe}"` — 例如 `arxiv_2605_01300`。
規則：取出 source + source_id，把任何 `/`、`.`、`:` 改 `_`，全部小寫，截 ≤ 64。

衝突處理：若 slug 已存在但 paper hash 不同（論文更新），覆寫 manifest 但保留
`source.generated_at` 原值，加 `source.updated_at`。

## Fallback 指引

回滾路徑（從重到輕）：

1. **取消每日排程**：`crontab -e` 移除 `gs-strategy-daily-refresh` block，
   或跑 `scripts/install_daily_refresh.sh --uninstall`（M5 會實作）
2. **回滾 generator 但保留 4 支主策略**：
   ```
   git revert <M5-commit>..<M2-commit>
   rm -rf strategies/_generated/
   ```
   主 bundle (`vgrsi_tx` 等) 完全不受影響。
3. **回滾整個 pipeline + spec compliance**：`git reset --hard 2a29b7f`
   （M19 commit，daily-strategy-gen 與 strategy-import-spec 全部 unwind）

## 進度日誌

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
