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

> **改碼後要重啟**：`http.server` 不會 hot-reload Python，改了 `server.py`/
> `stats.py` 後必須重啟 server 才生效（靜態檔 index.html/app.js 則即時讀）。
> `run_webui.sh` 啟動前會自動停掉同 port 的舊 server；footer 也會顯示
> 「server 啟動於 … · code <git hash>」讓你一眼看出跑的是不是最新版。

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
  本地 PDF 連結即時反映 `data/pdfs/`（無需重建）。
- **Strategy / Factor 雙 panel**：論文區分「策略」「因子」兩個 tab 切換查詢
  （依 `quant_crawler/paper_class.py` 自動分類 strategy vs factor）。每個 tab
  可依**子類別**篩選（factor: value/size/momentum/quality/… ；strategy:
  trend-following/mean-reversion/pairs-trading/…），子類別自動偵測。
- **手動標籤**：每篇論文可在 dashboard 手動新增/移除子類別標籤、或覆寫 kind
  （修正誤判）。手動標註存 `paper_labels` 表，**re-crawl 不會被洗掉**。
  寫入走 `POST /api/labels`（dashboard 因此具備有限寫入能力）。

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

## RAG + MCP（讓 Claude 取原文公式生成忠實 spec）

把下載的 PDF 全文索引進可檢索 store，透過 MCP 讓 Claude 在生成 strategy/factor
spec 時取回**原始論文 context**（正確數學公式、參數定義），避免憑記憶杜撰。

技術棧（純 Python、不靠 SaaS）：`pypdf` 抽文字 + **SQLite FTS5**（BM25 檢索，
與 `papers.db` 同庫）+ **FastMCP** server。需額外安裝：

```bash
.venv/bin/pip install pypdf mcp        # 或見 requirements-rag.txt
```

用法：

```bash
.venv/bin/quant-crawl rag-ingest               # 抽 data/pdfs/*.pdf → chunk → FTS5
.venv/bin/quant-crawl rag-stats --list          # 索引統計 / 列出已索引論文
.venv/bin/quant-crawl rag-search "cubic momentum critical threshold" --kind strategy
```

MCP server（Claude Code 透過根目錄 `.mcp.json` 自動掛載 `gs-strategy-rag`）暴露：

| MCP tool | 用途 |
|---|---|
| `search_paper_chunks(query, kind?, limit?)` | 跨全 corpus BM25 搜段落 |
| `get_paper_context(source, source_id, query)` | 在**已知論文**內取最相關段落（公式 lookup） |
| `get_paper_fulltext(source, source_id)` | 取某論文全文 |
| `list_indexed_papers(kind?)` / `rag_stats()` | 列出已索引 / 索引統計 |

自動產生的 bundle README 會附上對應的 `get_paper_context(...)` 呼叫提示；
`daily_refresh.sh` 在 fetch-pdfs 後自動 `rag-ingest`，閉環：
crawl → fetch-pdfs → rag-ingest → strategy_gen。

設計記錄見 `docs/progress-rag-mcp.md`。

### Dashboard 內瀏覽 RAG / MCP

webui（`./scripts/run_webui.sh`）多了兩個面板，不會 SQL 也能用：
- **RAG 全文檢索**：關鍵字搜原文（BM25）、依 strategy/factor 篩選、點論文看
  chunks/全文。對應 `/api/rag/{stats,search,paper}`。
- **MCP server**：顯示 `gs-strategy-rag` 設定、transport、暴露的 tool 清單、
  索引健康、運行偵測（stdio 無常駐 process 時標示由 client 按需啟動）。
  對應 `/api/mcp/info`。

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
