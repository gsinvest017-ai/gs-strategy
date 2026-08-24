---
type: progress
updated: 2026-05-27
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# RAG dashboard panel + MCP server info

> 在既有 webui 加上：(1) 給不會 SQL 的人瀏覽/檢索 RAG 全文 store 的面板；
> (2) 顯示目前 MCP server 的資訊（設定、暴露的 tools、索引健康、運行偵測）。

## 目標

非技術使用者開 `http://127.0.0.1:5057` 就能：
- 看 RAG 索引概況（幾篇論文、幾個 chunk）、列出已索引論文（依 strategy/factor）
- 用**自然語言關鍵字**搜全文（BM25），看到命中段落 + 來源 + 頁碼 + 分數，
  完全不用寫 SQL
- 點某篇論文看它的 chunks / 全文
- 看 `gs-strategy-rag` MCP server 的設定、提供哪些 tool、索引狀態、是否有
  process 正在跑

## 設計

後端檢索邏輯已存在（`quant_crawler.rag.retrieve` + `RagStore`），webui 只需加
**唯讀 GET endpoints** 包一層；MCP 資訊另寫 `mcp_info.py`。

### 「正在運行的 MCP server」語義（誠實說明）

`gs-strategy-rag` 是 **stdio transport** MCP server：沒有常駐 daemon，由 Claude
Code 在每個 session **按需 spawn**。因此面板顯示：
1. **設定**：從 `.mcp.json` 讀 server 名稱 / command / args / transport
2. **暴露的 tools**：import FastMCP app 後 `list_tools()` 取 name+description
3. **索引健康**：`RagStore.stats()`（server 實際服務的資料）
4. **運行偵測（best-effort）**：`pgrep -f quant_crawler.rag.mcp_server` 看當下
   有沒有 session 起了 server（有 PID 就顯示，沒有就標「stdio：由 client 按需啟動」）

### API

| endpoint | 回傳 |
|---|---|
| `GET /api/rag/stats` | `{papers_indexed, chunks, papers:[{source,source_id,title,kind,n_chunks}]}` |
| `GET /api/rag/search?q=&kind=&limit=` | enriched chunks（title/kind/page/score/text） |
| `GET /api/rag/paper?source=&source_id=&q=` | 指定論文 chunks（有 q 取相關段落，無 q 取全文） |
| `GET /api/mcp/info` | `{config, tools, running:[{pid,started}], rag:{...}}` |

### 前端

- **RAG 全文檢索面板**：搜尋框 + kind 篩選 → 結果表（標題 / kind / 頁 / 分數 /
  段落文字）；側邊「已索引論文」清單，點擊 → 顯示該篇 chunks。
- **MCP server 面板**：server 名稱 + command、transport、tools 清單（name+desc）、
  索引健康、運行狀態 badge。

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 設計 | 本檔 |
| M2 | webui RAG/MCP 後端 | `quant_crawler/webui/mcp_info.py` + server `/api/rag/*`、`/api/mcp/info` + tests |
| M3 | 前端面板 + 驗證 | RAG 檢索/瀏覽面板、MCP 面板、瀏覽器截圖、README、本檔總結 |

## Fallback 指引

- 純新增 webui 唯讀 endpoints + 前端面板 + 一個 `mcp_info.py`，不動 RAG store /
  既有面板。回滾：`git revert <M3>..<M2>`。
- 整段：`git reset --hard c132b8b`（RAG/MCP M5 commit）。

## 進度日誌

### M1 — 設計 ✅
釐清 stdio MCP server「運行」語義（無常駐 daemon，按需 spawn）；面板顯示
config + tools + 索引健康 + best-effort process 偵測。Commit `<M1>`。

### M2 — webui RAG/MCP 後端 ✅
- `quant_crawler/webui/mcp_info.py`：`mcp_config`（讀 .mcp.json）、`mcp_tools`
  （introspect FastMCP `list_tools`）、`running_servers`（pgrep）、`mcp_info`
- server GET：`/api/rag/stats`、`/api/rag/search`、`/api/rag/paper`、`/api/mcp/info`
  （全部唯讀，包既有 `rag.retrieve` + `RagStore`）
- 4 mcp_info 測試 + 5 server endpoint 測試；live 驗證 search/mcp-info
Commit: `M2: webui RAG endpoints (stats/search/paper) + /api/mcp/info`

### M3 — 前端面板 + 驗證 ✅
- **RAG 全文檢索面板**：關鍵字搜尋框（不用 SQL）+ 分類篩選 → 結果表
  （論文/分類/頁/分數/命中段落），右側「已索引論文」清單，點擊看 chunks/全文
- **MCP server 面板**：server 名稱 + stdio badge + 啟動命令、索引健康、
  運行狀態 hint、5 個 tool 清單含說明
- 瀏覽器驗證：搜「cubic momentum threshold」回 25 筆、34 篇索引、MCP 5 tools；
  截圖確認兩面板渲染
- webui+rag 測試 70 綠
Commit: `M3: RAG browse panel + MCP server info panel (frontend)`

## 結論

不會 SQL 的使用者開 dashboard 即可：關鍵字搜 RAG 原文（BM25）、點論文看
chunks/全文、看 MCP server 設定 / tools / 索引狀態 / 運行偵測。全唯讀、複用
既有 `rag.retrieve`。

## 後續方向
- RAG 結果可加「複製 get_paper_context(...) 呼叫」按鈕，方便貼給 Claude。
- MCP 面板可加「測試 ping」按鈕實際 spawn server 跑一次 list_tools 驗證健康。
- 大論文全文目前一次塞進 <pre>；可加分頁/lazy load。
