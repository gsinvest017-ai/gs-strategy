# Test plan — gs-strategy

> 生成於 2026-05-29 by `/test-plan`
> Spec sources: `README.md`, `pyproject.toml`, `docs/progress-*.md`, `.mcp.json`, `architecture.drawio`
> Framework: **pytest** (偵測自既有 `tests/test_*.py` + `def test_*` + 大量 `@pytest.fixture` / `parametrize`)
> 模式: **gap analysis**（既有 160 個 test functions 已涵蓋大部分純函數 + webui；本計畫聚焦未覆蓋區）

## Overview

- Stack: Python 3.12; HTTP via `requests`; persistence via stdlib `sqlite3` (FTS5)
- 測試檔位置: `tests/`；命名 `test_<module>.py`
- 既有規模: **15 檔 / 160 test functions**
- 跨 venv 慣例:
  - `.venv` (crawler) — pytest, requests, pypdf, mcp, yaml, jinja2
  - `.venv-bt` (backtest) — numpy/pandas/zipline-tej + pytest（給 strategy_math + dashboard_bundle 用）
- Coverage goal: **80%**（排序依據；P0 = 缺口風險 + 高呼叫流量）

<!-- BEGIN test-plan: auto-generated section -->

## Existing coverage matrix

| Module / Layer | 既有測試 | 既有案例數 | 缺口 |
|---|---|---:|---|
| `quant_crawler/utils/http.py` (**RateLimitedSession**) | — | **0** | ⚠️ **P0**：per-host delay / 429 / 503 / Retry-After / backoff jitter / download stream |
| `quant_crawler/utils/text.py` | `test_text.py` | 5 | ✅ |
| `quant_crawler/utils/logging.py` | — | 0 | low |
| `quant_crawler/crawlers/base.py` | — | 0 | ⚠️ run loop / try-except 隔離 / dedup / disabled skip |
| `quant_crawler/crawlers/arxiv.py` | `test_arxiv_parsing.py` | 1 | atom multi-author / categories / NaT date |
| `crawlers/{nber,repec,fed,wiley,aqr}.py` | — | **0** | RSS / HTML 解析 happy + bad-shape |
| `quant_crawler/orchestrator.py` | — | **0** | crawl_runs accounting / experiment-log append |
| `quant_crawler/storage/db.py` | `test_storage.py` | 4 | papers_with_pdf / ON CONFLICT 路徑 |
| `quant_crawler/storage/labels.py` | `test_labels.py` | 7 | ✅ |
| `quant_crawler/storage/models.py` | (via db) | — | dataclass JSON serialise corner case |
| `quant_crawler/paper_class.py` | `test_paper_class.py` | 9 | ✅ |
| `quant_crawler/pdf_fetch.py` | `test_pdf_fetch.py` | 9 | ✅ |
| `quant_crawler/strategy_gen/{classify,generate,taxonomy}` | `test_strategy_gen.py`, `test_taxonomy.py` | 36 | ✅ |
| `quant_crawler/rag/{store,ingest,retrieve}` | `test_rag.py` | 15 | ✅；可補大文件 chunk + 多語 |
| `quant_crawler/rag/mcp_server.py` | `test_mcp_server.py` | 4 | ✅ in-process；補 subprocess wire |
| `quant_crawler/webui/stats.py` | `test_webui_stats.py` | 23 | ✅ |
| `quant_crawler/webui/server.py` | `test_webui_server.py` | 28 | ✅；補 POST 併發 / 大檔 |
| `quant_crawler/webui/mcp_info.py` | `test_mcp_info.py` | 4 | ✅ |
| `strategies/<bundle>` signal math | `test_strategy_math.py` | 10 | ✅ (.venv-bt) |
| Bundle validator / converter | `test_dashboard_bundle.py` | 5 | ✅ |

## Unit tests（新增 — U-001..U-040）

### Module: `quant_crawler.utils.http` — `RateLimitedSession`

**責任**：per-host 最小延遲 + 429/503 retry + Retry-After + backoff + 串流下載
**純度**：side-effect（網路 IO）
**公開介面**：`get(url, **kwargs)` / `download(url, dest)` / 屬性 `min_delay` / `max_retries`
**策略**：用 `responses` 或 `unittest.mock` mock `requests.Session.request` + `time.sleep` monkeypatch 防真睡

| # | Target | Case | 類型 | 前置 / Mock | 優先 |
|---|---|---|---|---|---|
| U-001 | `get(url)` | 第一次打 host A：不等；同 host 第二次：等 ≥ `min_delay` 才送出 | happy | mock `time.sleep` 計次 + assert delta | P0 |
| U-002 | `get(url)` | 不同 host A vs B：互不阻擋 | happy | mock | P0 |
| U-003 | `get(url)` | 200 first try：無 retry，不 sleep | happy | mock 200 | P0 |
| U-004 | `get(url)` | 429 → 200：1 次 retry，依 `Retry-After: 3` 等 3s | error | mock 429 then 200 | P0 |
| U-005 | `get(url)` | 503 → 503 → 200：2 次 retry，backoff exponential | error | mock | P0 |
| U-006 | `get(url)` | 503 持續超過 `max_retries`：最終回 503 not raise | error | mock 4×503 | P0 |
| U-007 | `get(url)` | `requests.RequestException`：retry，超過 max → raise | error | mock raise | P0 |
| U-008 | `get(url)` | `Retry-After` 是 RFC 1123 日期字串：當下 raise ValueError fallback 到 backoff | error | mock header | P1 |
| U-009 | `_retry_after` | non-numeric header → backoff_base ** (status%10) + jitter | happy | direct call | P1 |
| U-010 | `_sleep_backoff` | attempt N → sleep ≥ backoff_base**N | happy | monkeypatch sleep | P1 |
| U-011 | `download(url, dest)` | 200 stream → 寫入完整 bytes，回傳 total | happy | mock stream chunks | P0 |
| U-012 | `download(url, dest)` | 非 200 → 回 None；不建檔 | error | mock 404 | P0 |
| U-013 | `download(url, dest)` | 寫到一半 chunk 為空：跳過 | edge | mock empty chunk | P1 |
| U-014 | thread-safety | 同 host 多執行緒呼叫 → 序列化、no 同時 burst | concurrency | `threading` 起 5 worker | P1 |

### Module: `quant_crawler.crawlers.base.BaseCrawler`

**責任**：共用 run loop / try-except 隔離 / dedup `(source, source_id)` / relevance filter / disabled skip
**純度**：glue
**策略**：fake subclass + tmp DB；mock orchestrator’s storage

| # | Target | Case | 類型 | 前置 / Mock | 優先 |
|---|---|---|---|---|---|
| U-015 | `run()` | 子類 yield 3 papers → 全進 DB；returns (3 new, 0 updated) | happy | fake crawler | P0 |
| U-016 | `run()` | 子類其中一筆 raise → 其他仍寫入；該錯誤被吞 + log warning | error | partial exception | P0 |
| U-017 | `run()` | 整個 `fetch()` raise → run returns gracefully + crawl_run 標 error | error | exception | P0 |
| U-018 | `run()` | dedup：同 (source, source_id) 第二次跑只 update 不重複 | happy | seed DB | P0 |
| U-019 | `run()` | `bypass_relevance=True` 全部進；False → regex 不中的剔除 | happy | config | P1 |
| U-020 | `enabled=False` | orchestrator 不呼叫此 crawler（除非 include_disabled） | edge | orch test | P1 |
| U-021 | `max_items_per_run` | 子類 yield 100 但 cap=10：只前 10 進 | edge | — | P1 |
| U-022 | `min_delay` 透傳 | crawler 內 session 用 config.min_delay 而非預設 | happy | spy session | P1 |

### Module: 5 個 active crawlers（RSS / HTML 解析）

**責任**：把 source 回應解析成 `PaperRecord`
**純度**：pure（給定 fixture HTML/XML）
**策略**：放 fixture 進 `tests/fixtures/<source>_*.{xml,html}`，呼叫 `parse_one(...)` 直接 assert

| # | Crawler | Fixture | 驗證 | 優先 |
|---|---|---|---|---|
| U-023 | nber | `nber_rss_ok.xml`（3 items） | 3 個 PaperRecord，title/url/published 正確 | P1 |
| U-024 | nber | author 含 multiple dash | authors 正確切 | P1 |
| U-025 | repec | NEP fmk listing HTML | source_id 取對；relative URL 拼 base | P1 |
| U-026 | fed_feds | RSS 含 HTML escapes | abstract unescaped | P1 |
| U-027 | wiley | TOC RSS | abstract 為空 OK（wiley 不給） | P1 |
| U-028 | aqr | publisher-curated HTML | bypass_relevance 生效（全部進） | P1 |
| U-029 | * | 空 feed / bad XML | gracefully skip，不 crash | P2 |
| U-030 | arxiv | 既有 1 案例 + atom multi-author | authors 兩位以上 | P2 |
| U-031 | arxiv | category list（含 q-fin.TR + stat.AP） | categories list 完整 | P2 |
| U-032 | arxiv | `published` ISO + tz | datetime 正確 parse | P2 |
| U-033 | arxiv | summary contains LaTeX `$ \alpha $` | 不會把 `$` 當作什麼 | P2 |
| U-034 | nber | pdf_url 從 wid 推 | constructed URL 對 | P2 |
| U-035 | repec | RePEc id 含 `:` `;` `_` | DB key 不爆 | P2 |

### Module: `quant_crawler.orchestrator`

**責任**：依 REGISTRY 順序跑 crawler；包進 crawl_runs；EXPERIMENT_LOG.md append
**純度**：glue
**策略**：tmp DB + 兩個 fake crawler + tmp EXPERIMENT_LOG

| # | Target | Case | 類型 | 前置 / Mock | 優先 |
|---|---|---|---|---|---|
| U-036 | `run_all` | 兩個 enabled crawler 都成功 → 兩筆 crawl_runs 都 finished_at 有值 / error None | happy | fake | P1 |
| U-037 | `run_all` | 一個 throw → 該 row error 有訊息；其餘照常 | error | fake | P1 |
| U-038 | `run_all(only=['arxiv'])` | 只跑指定 | happy | — | P1 |
| U-039 | `run_all(include_disabled=True)` | enabled=False 也跑 | edge | config patch | P2 |
| U-040 | `append_experiment_log` | 寫進 docs/EXPERIMENT_LOG.md 結尾，含 source 三項計數 | happy | tmp md | P1 |

## Integration tests（新增 — I-001..I-011）

### Boundary: HTTP out (`utils.http.RateLimitedSession`) — `responses` mock

**Strategy**：用 `responses` 套件擬 arxiv Atom endpoint；驗 retry / UA / timeout

| # | Scenario | Setup | Assert | 優先 |
|---|---|---|---|---|
| I-001 | arxiv 200 atom feed | register mock → 1 paper xml | `arxiv` crawler 解析後 DB 多 1 row | P0 |
| I-002 | arxiv 503 then 200 | register 2 responses | 第 2 呼叫成功，DB 寫入；session 觀察到 1 retry | P0 |
| I-003 | arxiv timeout | mock connection error | run 不 crash + crawl_run error=timeout | P0 |
| I-004 | UA header 正確 | mock 200 + capture headers | header User-Agent == config 設定 | P1 |
| I-005 | min_delay 真睡（短一點 0.05s） | 同 host 連 3 次 | 第 2、3 次至少間隔 0.05s | P1 |

### Boundary: subprocess pipeline (`scripts/daily_refresh.sh`)

**Strategy**：tmp working dir + 假 .env + 攔截 venv python 為 echo-stub；驗 4 階段 stdout

| # | Scenario | Setup | Assert | 優先 |
|---|---|---|---|---|
| I-006 | dry-run 4 階段 | stub 全部回 0 | stdout 含 `[step 1/4]`..`[step 4/4]`；exit 0 | P1 |
| I-007 | 缺 .env | unset TEJAPI_KEY | exit 2 + log `no-tejkey` | P1 |
| I-008 | step 2 (fetch-pdfs) 非零 | stub fetch-pdfs exit 1 | 仍繼續到 step 3-4；log WARN 而非 FAIL | P1 |

### Boundary: MCP stdio server（subprocess wire）

**Strategy**：用 `mcp.client.stdio.stdio_client` spawn server，覆蓋 in-process 測試之外的 wire 行為

| # | Scenario | Setup | Assert | 優先 |
|---|---|---|---|---|
| I-009 | initialize + list_tools | spawn server | 收到 5 tools；ListToolsResult 結構正確 | P1 |
| I-010 | call_tool `search_paper_chunks` | spawn + 真實 RAG store | content[0].text JSON-parse 後是 list | P1 |
| I-011 | call_tool unknown name | spawn | error code per MCP spec | P2 |

## E2E tests（新增 — E-001..E-003）

### Flow: 完整 ingest pipeline (CLI 全鏈)
**Entry**：`./run.sh crawl`
**Setup**：tmp `data/` (覆寫 `QC_DATA_DIR`)；mock 1 個 arxiv RSS endpoint (responses)；真實 pypdf 抽 tiny PDF（test fixture 一份 100KB PDF）
**Steps**：
1. `quant-crawl run -s arxiv` → exit 0；`papers.db` 多 1 row
2. `quant-crawl fetch-pdfs -s arxiv -n 1` → `data/pdfs/arxiv_*.pdf` 存在
3. `quant-crawl rag-ingest` → `rag_chunks` 至少 1 row
4. `quant-crawl rag-search "tiny pdf marker"` → 至少 1 hit，包含已知字串

**Assert**：CLI exit 全 0；DB / FS / stdout 三方一致

| # | Flow | 優先 |
|---|---|---|
| E-001 | 上述 4 步 happy chain | **P0** |

### Flow: webui label round-trip
**Entry**：spawn webui (test port) → POST `/api/labels` → GET `/api/papers?kind=...`
**Setup**：tmp DB 預塞 3 papers；no kind_override
**Steps**：
1. POST add_subcat (s='arxiv', sid='1', op='add_subcat', value='ui-test') → 200
2. POST set_kind value='factor' → 200
3. GET /api/papers?kind=factor → 包含 source_id=1
4. POST remove_subcat → manual_subcats=[]
5. POST set_kind value=null → kind_override=null

**Assert**：每步 200 + DB 終態符合；search by subcat 也命中

| # | Flow | 優先 |
|---|---|---|
| E-002 | 上述 label CRUD round-trip | P1 |

### Flow: launcher smoke
**Entry**：`./run.sh setup && ./run.sh test`
**Setup**：tmp HOME / venv（重 setup 一次）；guarded by `RUN_E2E=1`
**Assert**：venv 建好 / pytest 跑得過

| # | Flow | 優先 |
|---|---|---|
| E-003 | run.sh setup → test 成功 | P2 |

## Coverage matrix（計畫後達成）

| Module / Layer | Unit | Integration | E2E |
|---|---|---|---|
| `utils.http` | ✅ U-001..014 | ✅ I-001..005 | ✅ E-001 |
| `crawlers/*` | ✅ U-015..035 | ✅ I-001..005 | ✅ E-001 |
| `orchestrator` | ✅ U-036..040 | ✅ I-006..008 | ✅ E-001 |
| `storage/*` | ✅ (既有) | ✅ (既有) | ✅ E-001 |
| `pdf_fetch` | ✅ (既有) | (real arxiv in E-001) | ✅ E-001 |
| `strategy_gen/*` | ✅ (既有) | ✅ (既有, validator subprocess) | partial |
| `rag/*` | ✅ (既有) | ✅ I-009..011 | ✅ E-001 |
| `webui/*` | ✅ (既有) | ✅ (既有) | ✅ E-002 |
| `paper_class` | ✅ (既有) | (via stats) | ✅ E-002 |
| `strategies/*` math | ✅ (.venv-bt) | (dashboard_bundle) | — |
| `daily_refresh.sh` | — | ✅ I-006..008 | (E-003 indirect) |
| `run.sh / run.ps1` | — | — | ✅ E-003 |

## Implementation order

1. **P0 unit** — `utils.http.RateLimitedSession`（U-001..014, U-011..012）— 是所有 crawler 的 infra，ROI 最高
2. **P0 unit** — `crawlers/base.BaseCrawler` 隔離 / dedup（U-015..018）— 失敗會默默吃掉資料
3. **P0 integration** — HTTP out（I-001..003）+ MCP wire smoke（I-009）
4. **P0 e2e** — CLI 全鏈 (E-001) — 最 robust 的 regression gate
5. **P1 unit** — 5 個 RSS/HTML crawlers fixture-based 解析（U-023..028）
6. **P1 unit** — orchestrator（U-036..040）
7. **P1 integration** — daily_refresh stub (I-006..008) + MCP wire 深層 (I-010)
8. **P1 e2e** — webui label round-trip (E-002)
9. **P2** — 邊界 case / 大量資料 / launcher smoke (E-003)

## Test infrastructure 待辦

- 新增 dev-deps：`responses` (HTTP mock) — 加進 `pyproject.toml [project.optional-dependencies.test]` 或 `requirements-dev.txt`
- 新增 `tests/fixtures/`：5 個 RSS/HTML 抓的小檔（每個 < 5KB），1 個 tiny PDF（100KB）
- pytest marker：`@pytest.mark.e2e`（預設 skip，`RUN_E2E=1` 才跑）；`@pytest.mark.bt`（給 .venv-bt 專用）
- conftest fixture：`tmp_papers_db`、`fake_session`、`vcr_cassettes`
- CI matrix（未來）：ubuntu + windows 都跑 unit + integration；e2e 限 ubuntu

## Open questions（spec ↔ code 不一致）

1. **README 表述 stale**：README §「daily_refresh.sh 四階段」漏了 step 2b `rag-ingest`（script 已加入）。→ 哪邊是 canonical？建議改 README 為 5 階段。
2. **split-venv 慣例未文件化**：`.venv` (crawler + webui + RAG) vs `.venv-bt` (strategies + dashboard_bundle + strategy_math) — 何時哪 venv？應在 README / CONTRIBUTING 明示，且 pytest marker 配合（`@pytest.mark.bt`）。
3. **`include_disabled` 的測試策略**：停用 source (SSRN/CME/Man) 會嘗試但通常失敗。要 `xfail` 還是 `skip`？目前無測試。
4. **`paper_class.classify_kind` tie**：score 平手預設 strategy。code 寫死，spec 未表述。e2e 該不該驗 tie path？建議補進 spec。
5. **`bar-fill` 漸層硬寫 `#2d6fbf`**（webui/static/style.css）：與 GS theme `--accent` 翻金衝突；測試不會抓但視覺會。
6. **webui POST `/api/labels` 無 idempotency-key**：add_subcat 同 tag 兩次目前正確 dedupe，但無欄位記錄 client retry。低風險，列出供 review。

## Out of scope

- 第三方依賴內部：`pypdf` / `mcp` SDK / `jinja2` / `requests` 的內部行為
- `.venv*` / `node_modules` / `vendor`（無）
- `data/papers.db` / `data/pdfs/` 中的真實內容（測試用 tmp）
- `strategies/_generated/` 自動產出物（不入版控、由 strategy_gen tests 覆蓋）
- 已停用 crawlers（SSRN/CME/Man）— Cloudflare blocked，不擬列入測試

<!-- END test-plan -->
