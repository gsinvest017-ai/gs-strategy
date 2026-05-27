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

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
