# quant_crawler — 期貨量化研究論文爬蟲

實驗用 sandbox 內的小型爬蟲系統，蒐集**最新且具公信力**的期貨/量化交易研究論文與報告。
不靠任何 SaaS / API key，純 Python + stdlib + `requests` + `feedparser` + `bs4`。

## 涵蓋的來源

| Tier | source key | 介面 | 內容 |
|------|------------|------|------|
| ✅ S | `arxiv`     | Atom API   | q-fin.TR / PM / ST / CP / RM 最新 preprint |
| ✅ S | `nber`      | RSS        | NBER Working Papers（每週新論文） |
| ✅ S | `repec`     | NEP HTML   | nep-fmk (Financial Markets) / nep-rmg (Risk Mgmt) / nep-mst (Microstructure) / nep-inv |
| ✅ A | `fed_feds`  | RSS        | Federal Reserve FEDS Notes / Working Papers |
| ✅ A | `wiley`     | RSS        | *Journal of Futures Markets* TOC（核心期刊） |
| ✅ B | `aqr`       | HTML       | AQR Capital Insights/Research（publisher-curated，全部收） |
| ❌ — | `ssrn`      | (停用)     | Cloudflare anti-bot；需 Playwright 才能繞過 |
| ❌ — | `cme`       | (停用)     | 同上 |
| ❌ — | `man_ahl`   | (停用)     | JS-rendered |

關於停用來源的決策過程，見 `docs/EXPERIMENT_LOG.md`。

## 安裝

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## 用法

```bash
# 跑所有 enabled 來源並把摘要追加到 EXPERIMENT_LOG.md
.venv/bin/quant-crawl run --log-run

# 只跑特定來源
.venv/bin/quant-crawl run -s arxiv -s wiley

# 包含已停用的來源（會嘗試但通常失敗）
.venv/bin/quant-crawl run --include-disabled

# 列出最新 20 篇
.venv/bin/quant-crawl list -n 20

# 只看 wiley 來源
.venv/bin/quant-crawl list -s wiley -n 10

# JSON 輸出（給下游程式吃）
.venv/bin/quant-crawl list -n 50 --json

# 標題/摘要全文搜尋
.venv/bin/quant-crawl search "trend following"

# 統計
.venv/bin/quant-crawl stats

# 看 source 設定
.venv/bin/quant-crawl sources
```

## 管理介面 (web UI)

本地網頁管理面板，彙整爬蟲 + 策略產生 pipeline 狀態。零外部依賴（stdlib
`http.server`），唯讀（不寫 DB、不改策略檔）。

```bash
./scripts/run_webui.sh                 # http://127.0.0.1:5057
./scripts/run_webui.sh --port 6060     # 或自訂 port
PORT=6060 ./scripts/run_webui.sh
```

面板顯示：

- **論文/報告總量** + 各來源分布（arxiv / wiley / aqr / repec / nber / fed_feds）
- **爬蟲 routine 執行紀錄**（可選日期，來自 `crawl_runs` 表：起訖、抓取/保留數、錯誤）
- **新增資料**（指定日 fetched 的論文；無則 fallback 顯示最近 N 筆）
- **策略清單**：`strategies/`（手寫）+ `strategies/_generated/`（自動產生）的
  id / 來源 / 模板 / 標籤 / 待審
- **匯出狀態**：每支策略是否已匯出到 `~/gs-zipline-tej/strategies/<id>/`
  （可用 `ZIPLINE_TEJ_STRATEGIES_DIR` 覆寫目標路徑）
- **檔案超連結**：論文列連到 PDF（優先本地 `data/pdfs/<slug>.pdf`，否則遠端
  `pdf_url`）；策略列連到 spec markdown（`README.md`）與 `manifest.yaml`，
  皆由 webui 經 `/files/*` 路由 serve（path-traversal + 副檔名白名單防護）。

JSON API（同一 server）：`/api/summary`、`/api/runs?date=`、`/api/papers?date=`、
`/api/strategies`、`/api/dates`；檔案：`/files/pdf/<name>`、
`/files/strategy/<id>/<file>`。設計記錄見 `docs/progress-webui.md`、
`docs/progress-pdf-and-schedule.md`。

### 每日排程 + PDF 下載

```bash
# 手動下載尚未抓的 PDF 到 data/pdfs/
.venv/bin/quant-crawl fetch-pdfs            # 全部；或 -s arxiv -n 5 限量

# 安裝每日排程（crawl → fetch-pdfs → strategy_gen → validate）
./scripts/install_daily_refresh.sh                       # 預覽 cron 行
./scripts/install_daily_refresh.sh --apply --schedule "30 6 * * *"
./scripts/install_daily_refresh.sh --uninstall           # 移除
```

`daily_refresh.sh` 四階段：(1) `quant-crawl run` 更新 papers.db →
(2) `fetch-pdfs` 下載新 PDF → (3) `strategy_gen` 產生 skeleton bundle →
(4) validator。log 在 `data/logs/daily_refresh_<date>.log`。

## 架構

```
quant_crawler/
├── config.py                # SourceConfig + 關鍵字清單 + 路徑
├── cli.py                   # argparse subcommands
├── orchestrator.py          # 註冊 + 順序執行 + EXPERIMENT_LOG 追加
├── crawlers/
│   ├── base.py              # BaseCrawler（共用 run loop + relevance filter）
│   ├── arxiv.py / nber.py / repec.py / fed.py / wiley.py / aqr.py / ssrn.py
├── storage/
│   ├── models.py            # PaperRecord dataclass
│   └── db.py                # SQLite (papers.db) — primary key (source, source_id)
└── utils/
    ├── http.py              # RateLimitedSession：per-host delay + retry/backoff
    ├── logging.py           # console + rotating file handler
    └── text.py              # relevance regex / hash / normalize
```

### 設計重點

- **禮貌爬蟲**：每個 source 有 `min_delay`，HTTP wrapper 以 host 為粒度執行最小延遲；429/503 退避重試
- **去重**：`(source, source_id)` 是 SQLite 主鍵，重跑只更新不重複
- **相關性過濾**：`config.RELEVANCE_REGEX` 涵蓋 futures/momentum/carry/term-structure/managed futures/CTA/stat arb 等
- **publisher-curated 旁路**：AQR 的研究本來就是篩過的，`bypass_relevance=True` 不再過濾
- **失敗隔離**：`BaseCrawler.run` 整個 wrap 在 try/except，單一 source 出錯不會中斷其他

## 開發

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/ -v
```

## 已知限制

1. **SSRN/CME/Man Group**：Cloudflare 或 JS-render 阻擋，需要 Playwright 才能繞過
2. **PDF 下載**：預設關閉（`SourceConfig.download_pdfs=False`），只抓 metadata
3. **NBER 作者解析**：用簡單字串切分；偶爾會被多 dash 干擾
4. **AQR / Wiley 不抓 abstract**：listing/RSS 只給標題；要 follow-up 個別抓

## 下一步

- 接 Playwright 重新啟用 SSRN
- arXiv 加 incremental fetch（last-published 後才抓）
- 加 BIS / IMF / ECB working papers（需找對 RSS）
- export to JSON Lines / Parquet 給下游 backtest 用
