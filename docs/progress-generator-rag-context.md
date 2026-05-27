# Generator auto-embeds RAG paper context into generated bundles

> 接 `progress-rag-mcp.md` 的最後一條「後續方向」：
> 「generator 自動帶 context — 未來可讓 generate.py 直接呼叫 retrieve 把 top
> 公式段落寫進 bundle（目前是給提示，由 Claude/人工拉取）」。
> 本任務把它從「給提示」升級成「直接內嵌原文段落」。

## 目標

`quant_crawler/strategy_gen/generate.py` 產生的 bundle README，在來源論文已被
RAG 索引時，**直接呼叫 `rag.retrieve.paper_context` 取回 top 段落並內嵌進
README**，讓 reviewer / Claude 不必再多跑一次 MCP 就能對照原文公式。
未索引論文維持原本的 `rag-ingest` fallback 提示。整段不得讓 generation 失敗
（RAG 出問題就優雅退回 hint）。

## 範圍邊界

- 只動 README 的 RAG section 產生邏輯；manifest / strategy.py / futures_setup.py
  完全不變 → 不影響 dashboard validator、不改變既有 bundle 的可執行性。
- 不新增任何依賴（純用既有 `quant_crawler.rag.retrieve`）。
- 取回段落只做**預覽**（每篇 top 3 chunk、每段截 700 字），README 仍指向 MCP
  做完整 / 進一步查詢。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | generator 內嵌 RAG 段落 + tests + 驗證 | `_rag_context_section` helper、`generate_bundle(rag_db_path=)`、2 個新測試、live 驗證、README 更新 |

## 進度日誌

### M1 — generator 內嵌 RAG 段落 ✅

**做了什麼**

- `generate.py`：
  - 新增 `_RAG_QUERY_BY_TEMPLATE`（momentum / mean_reversion / buy_and_hold
    各自的 targeted query）+ `_RAG_CONTEXT_CHUNKS=3` / `_RAG_CHUNK_PREVIEW_CHARS=700`
  - 新增 `_rag_context_section(paper, classification, rag_db_path)`：呼叫
    `rag.retrieve.paper_context(..., query=<template query + matched_keywords>)`，
    把 top 3 chunk（含 page label + BM25 score）內嵌成 `### Auto-retrieved
    passages` 區段；保留 `get_paper_context(...)` / `get_paper_fulltext(...)`
    MCP 提示。整段包在 try/except，RAG 任一環節出錯就回 fallback hint。
  - `generate_bundle` 新增 `rag_db_path: Optional[Path] = None` 參數（預設用
    `config.DB_PATH`，daily pipeline 呼叫端不需改動），README RAG section 改成
    呼叫 helper（取代原本的 inline is_indexed + hint 字串）。
- `tests/test_strategy_gen.py`：+2 測試
  - `test_generate_bundle_embeds_rag_passages`：seed 一個含公式字串的 temp
    papers.db + rag_chunks，斷言 README 內嵌該公式、頁碼 `p.7`、仍有 MCP 提示。
  - `test_generate_bundle_rag_not_indexed_fallback`：papers 表存在但無 chunks →
    斷言落到「Paper text NOT yet indexed」fallback、無 passages 區段。
  - helper `_seed_papers_table` 建最小 papers 表供 `retrieve._paper_meta` enrich。
- `README.md`：RAG/MCP 段落更新，說明 generated README 現在直接內嵌段落。

**驗證**

- `pytest tests/test_strategy_gen.py tests/test_rag.py` → **51 passed, 1 failed**。
  唯一 failure 是 `test_generate_bundle_passes_validator`，原因是 crawler `.venv`
  沒裝 `numpy`（validator subprocess import strategy.py 時炸）——
  **已 `git stash` 驗證此 failure 在本次改動前的 base commit (`300dc7f`) 完全相同**，
  屬既有環境問題，與本次 README-only 改動無關。
- **Live 驗證**：對真實 `data/papers.db` 的 `arxiv:2605.00854`（cubic momentum
  論文）跑 `generate_bundle`，README 正確內嵌 3 段原文（含 "cubic function of
  market momentum ... critical threshold" 公式描述、p.1 / p.10 page label、
  BM25 score）+ MCP 提示。

**Commit**: 見 `M1: ...` commit

## Fallback 指引

純 README 產生邏輯變更 + 2 個測試 + README 文案，無資料 / schema / manifest /
strategy.py 變動。

- 回滾本任務：`git revert <M1 commit>` — 還原 `generate.py` 的 helper 與
  `rag_db_path` 參數、移除 2 個測試、還原 README 文案。
- 已產生的 `strategies/_generated/*/README.md` 會在下次 `strategy_gen` 跑時
  自動重寫（README 每次都重寫，非 idempotent-merge 欄位），故回滾後重跑即恢復
  舊版 hint-only README。

## 相關檔案

- `quant_crawler/strategy_gen/generate.py` — 編輯（新增 helper + 參數）
- `tests/test_strategy_gen.py` — 編輯（+2 測試 + seeding helper）
- `README.md` — 編輯（RAG 段落文案）

## 後續方向

1. 目前 query 是 template-keyed 固定字串 + matched keywords；可改成從 paper
   abstract 抽關鍵名詞做更精準的 formula query。
2. 內嵌段落是純文字預覽（pypdf 抽出的文字，數式符號可能失真）；若上 `pymupdf`
   / nougat 做數式還原，內嵌品質會更好（與 progress-rag-mcp.md 的「公式專用抽取」
   後續方向共用）。
3. 可選擇把內嵌段落數 / 截斷長度做成 manifest 或 CLI 參數，讓不同論文調整。
