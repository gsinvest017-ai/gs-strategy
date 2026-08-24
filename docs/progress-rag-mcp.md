---
type: progress
updated: 2026-05-27
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# RAG store + MCP server for faithful strategy/factor spec generation

> 把爬下來的 paper/report 全文存進可檢索的 store，透過 MCP 讓 Claude 取回
> **原始論文 context**（例如某策略/因子的正確數學公式），以正確生成忠於原文的
> strategy/factor spec markdown。

## 目標

1. 從已下載的 PDF（`data/pdfs/`）抽全文 → 切 chunk → 存進可檢索 store。
2. 提供 RAG 檢索 API（關鍵字/BM25 + 指定論文全文取回）。
3. 以 MCP server 暴露檢索工具，Claude 可在生成 spec 時呼叫，取回原文 context
   （正確公式、參數、定義），避免「憑記憶杜撰公式」。

## 技術選擇（依 repo「純 Python、不靠 SaaS / API key」原則）

| 元件 | 選擇 | 理由 |
|---|---|---|
| PDF 抽文字 | `pypdf`（純 Python） | 無系統依賴；已驗證可抽 `data/pdfs/*.pdf` |
| RAG store | **SQLite FTS5**（內建，零額外依賴） | BM25 全文檢索；公式/關鍵字檢索足夠；同一顆 `papers.db` |
| 檢索粒度 | per-paper chunk（~1000 字 + overlap，記 page） | 「我知道在替哪篇 paper 生 spec → 取回該 paper chunk 搜公式」 |
| MCP | `mcp` / FastMCP（stdio） | 標準 MCP；Claude Code 可直接掛 |
| 向量/embedding | **暫不做**（記為後續） | 本地 embedding 需 torch/sentence-transformers（重）；目標是 targeted-within-paper 檢索，FTS5 BM25 已足夠 |

> 「vector database and/or 一般 database」→ 選 FTS5（一般 DB + 全文檢索），
> 語意向量層列為後續可選增強。

## 資料模型（同 `data/papers.db` 內新增）

```sql
CREATE TABLE rag_chunks (
    source     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    chunk_idx  INTEGER NOT NULL,
    page       INTEGER,
    text       TEXT NOT NULL,
    PRIMARY KEY (source, source_id, chunk_idx)
);
CREATE VIRTUAL TABLE rag_fts USING fts5(
    text, source UNINDEXED, source_id UNINDEXED, chunk_idx UNINDEXED,
    content='rag_chunks', content_rowid='rowid'
);
```

chunk 與 `papers`、`paper_labels` 以 `(source, source_id)` 對齊，可帶出 title /
kind / 子類別。

## API / CLI / MCP

| 介面 | 功能 |
|---|---|
| `RagStore.search(query, limit, kind?, source?)` | BM25 ranked chunks + paper meta |
| `RagStore.get_chunks(source, source_id)` / `fulltext(...)` | 指定論文全文/chunk |
| `quant-crawl rag-ingest [-n N] [-s src]` | 抽 PDF → chunk → 存 |
| `quant-crawl rag-search "<q>"` / `rag-stats` | CLI 檢索 / 統計 |
| MCP tools：`search_paper_chunks` / `get_paper_fulltext` / `list_indexed_papers` | 給 Claude 取 context |

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 設計 + 裝 deps | 本檔（pypdf + mcp 已裝） |
| M2 | RAG store + PDF ingest | `quant_crawler/rag/{store,ingest}.py`、`quant-crawl rag-ingest` + tests |
| M3 | 檢索 API + CLI | `RagStore.search/get`、`rag-search`/`rag-stats` + tests |
| M4 | MCP server | `quant_crawler/rag/mcp_server.py`（FastMCP）+ 設定範例 + smoke |
| M5 | strategy_gen 整合 + docs | 生成器附 RAG 來源/取回 helper、README、報告 |

## Fallback 指引

- RAG 是新增 table + 新 package，不動既有 papers/labels/webui。
- 移除：`DROP TABLE rag_chunks; DROP TABLE rag_fts;` + `rm -rf quant_crawler/rag`。
- 依賴回滾：`.venv/bin/pip uninstall pypdf mcp`。
- 整段：`git revert <M5>..<M2>` 或 `git reset --hard 178f66e`（strategy/factor M5）。

## 進度日誌

### M1 — 設計 + deps ✅
裝 pypdf + mcp（FastMCP），確認 FTS5 可用、34 PDF 已下載。技術棧定案
（pypdf + SQLite FTS5 + FastMCP，向量層列後續）。Commit `<M1>`。

### M2 — RAG store + ingest ✅
- `quant_crawler/rag/store.py`：`RagStore`（FTS5 `rag_chunks`+`rag_fts`，
  replace_paper/search(BM25)/get_chunks/fulltext/indexed_papers/stats，
  FTS query sanitise 防 operator 炸）
- `rag/ingest.py`：pypdf 抽文字 + page-aware 重疊 chunk（~1000字/150 overlap）
- `quant-crawl rag-ingest`
- **實跑 34 PDF → 3432 chunks**；檢索驗證精準命中 cubic-momentum 公式段落
- 9 store/chunk 測試
Commit: `M2: RAG FTS5 store + pypdf ingest + quant-crawl rag-ingest`

### M3 — 檢索 API + CLI ✅
- `rag/retrieve.py`：`search_chunks`（join title+kind，kind 過濾）、
  `paper_context`（已知論文內 targeted query 或全文）、`list_indexed`
- `quant-crawl rag-search`（含 --kind/--source-id/--json）、`rag-stats --list`
- 6 retrieve 測試（enrich/kind filter/targeted/fulltext/not-indexed）；
  live 驗證 RMT 論文檢索（正確歸 factor kind）
Commit: `M3: enriched RAG retrieval API (kind-aware) + rag-search/rag-stats CLI`

### M4 — MCP server ✅
- `rag/mcp_server.py`（FastMCP）5 tools：search_paper_chunks /
  get_paper_context / get_paper_fulltext / list_indexed_papers / rag_stats
- 根目錄 `.mcp.json` 讓 Claude Code 自動掛 `gs-strategy-rag`
- **完整 stdio client handshake smoke**：initialize→list_tools(5)→call_tool；
  get_paper_context 取回 cubic-momentum 公式段落成功
- 4 MCP 測試（tool 註冊/schema/dispatch）
Commit: `M4: FastMCP server (search/context/fulltext tools) + .mcp.json + tests`

### M5 — strategy_gen 整合 + docs ✅
- `daily_refresh.sh` 加 step 2b `rag-ingest`（閉環 crawl→fetch-pdfs→rag-ingest→gen）
- `generate.py`：bundle README 依 RAG 索引狀態附 `get_paper_context(...)` 提示
  （已索引）或 ingest 指引（未索引）；review checklist 改成「先從 RAG 取公式」
- README 加 RAG+MCP 段落、新增 `requirements-rag.txt`、本檔總結
- 全 RAG/MCP/strategy_gen 測試綠
Commit: `M5: wire RAG into pipeline + generated README hint + docs`

## 結論

閉環達成：爬 → 下載 PDF → **抽全文索引進 FTS5** → MCP server 暴露檢索 →
Claude 生成 spec 時可呼叫 `get_paper_context(source, source_id, query)` 取回
原文公式段落，忠實還原論文。34 篇 / 3432 chunks 已索引可用。

## 後續方向
- **語意向量層**：若要 fuzzy semantic（非關鍵字）檢索，可加本地 embedding
  （sentence-transformers）或外部 embedding，建第二張向量表與 FTS 並用 hybrid。
- **公式專用抽取**：pypdf 對含 LaTeX/數學式 PDF 抽出的是純文字，公式符號可能
  失真；可考慮 `pymupdf` 或 GROBID/nougat 做數式還原。
- **dashboard 整合**：webui 可加一個「RAG 檢索」面板直接查 chunk。
- **generator 自動帶 context**：未來可讓 generate.py 直接呼叫 retrieve 把 top
  公式段落寫進 bundle（目前是給提示，由 Claude/人工拉取）。
