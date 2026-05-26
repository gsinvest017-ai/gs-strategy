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

### M1 — 計畫 + 進度檔 ✅

Commit `13b69bc`：建立本檔，含目標、範圍邊界（誠實宣告：只產 skeleton）、
milestone 表、bundle dir 規劃、命名規則、fallback 指引。

### M2 — paper→template 分類器 ✅

- `quant_crawler/strategy_gen/__init__.py`、`classify.py`
- 3 個 template bucket（優先級由高到低）：
  - `momentum` — 8 個 keyword pattern (momentum/tsmom/xsmom/trend/cta/breakout)
  - `mean_reversion` — 11 個 (rsi/oscillator/pairs/cointegration/stat-arb 等)
  - `buy_and_hold` — fallback，empty pattern 一律 match
- `classify_paper(paper)` 回傳 `ClassificationResult`（template, default_params,
  matched_keywords, tags）
- `tests/test_strategy_gen.py` 18 個分類測試全綠

Commit: `M2: paper->template classifier (momentum/mean_rev/buy_and_hold)`

### M3 — 模板 + 產生器 ✅

- `templates/manifest.yaml.j2`：含 spec 必填欄位 + `requires_review: true`
  擴充 + `source.{template, matched_keywords, paper}` provenance + 一個
  `review_checklist` 區段
- `templates/strategy_{momentum,mean_reversion,buy_and_hold}.py.j2`：
  3 份 skeleton，**每份的訊號函數都回 no-op**（momentum 回 0、
  mean-rev 回 50 中性值、buy_and_hold holdable 1 contract），逼使用者
  review 並補完訊號邏輯才能上線
- `generate.py`：
  - `paper_slug(source, source_id)` — filesystem-safe slug + truncate 64
  - `generate_bundle(paper, out_root, dry_run)` — render manifest +
    strategy.py + 複製 futures_setup.py + 產生 README.md
  - idempotent merge：手動編輯過的 manifest 欄位會保留；
    `source.generated_at` 不會 churn，加 `updated_at` 表達 re-run
  - `select_recent_papers(db_path, since, limit)` — DB query helper
  - CLI: `python -m quant_crawler.strategy_gen --since YYYY-MM-DD --limit N --dry-run`
- 新增 `__main__.py` 讓 `python -m quant_crawler.strategy_gen` 乾淨 invoke
- pytest 33 個（含 M2 的 18 個 + 15 個新測試覆蓋 slug、3 個 template、
  validator pass-through、idempotency、dry-run、DB selector）

Commit: `M3: jinja templates + paper->bundle generator (idempotent)`

### M4 — daily_refresh.sh 端到端 pipeline ✅

- `scripts/daily_refresh.sh`：
  - Step 1: `.venv/bin/python -m quant_crawler.cli run --log-run`
  - Step 2: `python -m quant_crawler.strategy_gen --since yesterday`
  - Step 3: 對所有 `strategies/_generated/*` 跑 validator
  - logging：`data/logs/daily_refresh_<DATE>.log` + summary 一行寫到
    `data/logs/daily_refresh.log`
  - exit code：0 ok / 1 unexpected / 2 missing .env / 3 validator fail
- 對真實 `papers.db` 跑 controlled smoke (10 papers, limit, fresh outdir)：
  10 bundles 全部產出 + 全部 pass validator
- `bash -n` 語法檢查通過

Commit: `M4: daily_refresh.sh end-to-end pipeline (crawl + gen + validate)`

### M5 — install 腳本 + 最終報告 ✅

`scripts/install_daily_refresh.sh`：
- 預設 dry-run，**不**動 crontab，列出 cron line 給人 review
- `--apply` 才實際寫到 crontab，使用 markers (`# >>> gs-strategy daily_refresh <<<`)
  圍住，重複 apply 自動取代不重複堆疊
- `--uninstall` 移除 block
- `--schedule "<cron expr>"` 自訂時間（預設 `0 6 * * *`）
- **本任務不自動 apply** — crontab 是跨 working dir 系統變動，per /safe-yolo
  強制停下條件，使用者必須自己跑 `./scripts/install_daily_refresh.sh --apply`

Commit: `M5: install_daily_refresh.sh (dry-run by default; requires --apply)`

## 後續方向

1. **真的上 cron**：使用者執行
   ```
   ./scripts/install_daily_refresh.sh --apply
   ```
   建議搭配 `--schedule "30 6 * * *"` 錯開 17:30 `quantdata-daily-refresh` 與
   00:00 `gs-claude-config night-shift`。

2. **第一輪手動執行**：
   ```
   ./scripts/daily_refresh.sh
   tail -50 data/logs/daily_refresh_$(date -u +%Y-%m-%d).log
   ```
   檢查 step 1-3 都成功，再交給 cron。

3. **review workflow**：dashboard 顯示 `requires_review: true` 的 bundle 後，
   人工編輯 `_generated/<slug>/strategy.py` 補完訊號邏輯 → 把 manifest
   的 `requires_review` 改 `false` → 視情況把 bundle 升級到 `strategies/<id>/`
   （非 `_generated`），讓它脫離自動覆寫範圍。

4. **未做的**（spec §8 提到但暫時不需要）：
   - `provenance.json` sidecar — generator 已經把 hash-able 資訊放
     `manifest.source` 內，足夠 dashboard audit
   - 老化掉的 `_generated/` bundle 自動清理：目前永遠保留；如果累積過多
     再加 `--prune-older-than N` flag

5. **進階**（換掉 rule-based classifier）：把 `classify.py` 替成
   LLM call（Claude API + cache prompt），同樣 input/output shape，
   pipeline 其他部分不動。`docs/progress-strategy-import-spec.md` 已把
   spec hooks 都接好。
