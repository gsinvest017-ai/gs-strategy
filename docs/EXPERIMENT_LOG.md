# Experiment Log — Quant Futures Paper Crawler

> 一份持續更新的實驗日誌。每個重大里程碑、卡關、決策、回滾都會寫進來。
> 時間戳採台北時間（UTC+8），日期 = `currentDate` 提供的 `2026-05-10`。

---

## 2026-05-10 — Day 0：專案啟動

### 目標
在 `~/yolo-claude` 沙盒下建立一個爬蟲系統，蒐集「最新且具公信力」的期貨量化交易策略研究論文與報告。

### 來源候選（依公信力 + 可機器讀取性排序）
| Tier | 來源 | 介面 | 備註 |
|------|------|------|------|
| S | arXiv `q-fin` (TR/PM/ST/CP) | Atom API | 開放、穩定，最新 preprint 集散地 |
| S | NBER Working Papers | RSS + HTML | 頂級學術機構，每週新論文 |
| A | SSRN FEN / Derivatives eJournal | HTML | 量大但需要繞 anti-bot；只抓 metadata |
| A | Federal Reserve FEDS Notes / IFDP | HTML index | 央行研究，commodity & futures 主題常見 |
| A | CME Group Research / Education | HTML | 期貨原生機構，含 white paper |
| B | AQR Insights | HTML | factor / managed futures 金字招牌 |
| B | Man Group AHL Academic Advisory Board | HTML | trend following 經典論文 |

### 架構決定
- **語言**：Python 3。stdlib + `requests` + `feedparser` + `beautifulsoup4`，避免重型框架。
- **儲存**：SQLite (papers.db) 存 metadata，PDF 落到 `data/pdfs/<source>/<id>.pdf`，原始 response 落到 `data/raw/`（debug 用）。
- **抽象**：`BaseCrawler.fetch() -> Iterable[PaperRecord]`，由 orchestrator 呼叫並寫入 storage。
- **去重**：以 `(source, source_id)` 為 primary key，再以 DOI / URL hash 做跨來源去重。
- **過濾**：keyword regex（`futures|commodity|managed.futures|trend.follow|CTA|term.structure|carry|momentum|basis`）+ category whitelist。
- **禮貌爬蟲**：每個 source 預設 ≥ 2s delay、`User-Agent` 表明意圖、respect `robots.txt`（人工檢查 + 程式跳過 disallowed path）。
- **失敗回滾**：每完成一個 source crawler 就 commit；卡關時 `git stash` + 切到上個 commit。本實驗用 `feat/quant-paper-crawler` branch 推進。

### 進度
- [x] 規劃 + git branch 建立 (`feat/quant-paper-crawler`)
- [x] 目錄骨架建立
- [x] 核心框架 (config / storage / base / logger)
- [x] arXiv crawler — live test：10 取 → 2 keep（filter 正確）
- [x] NBER crawler — live test：40 取 → 4 keep
- [~] SSRN crawler — **卡關**，見下方 incident
- [x] RePEc/NEP crawler（替代 SSRN）— live test：37 取 → 9 keep
- [x] Fed FEDS crawler — live test：15 取 → 2 keep
- [x] AQR crawler（bypass_relevance）— 10 全收（publisher curates）
- [x] Wiley *Journal of Futures Markets* crawler — 28/28 全部相關（最高命中率！）
- [~] CME — 同樣 Cloudflare 擋；停用
- [~] Man AHL — JS-rendered；停用
- [x] CLI orchestrator (`quant-crawl run|list|search|stats|sources`)
- [x] tests — 10/10 通過（offline fixture + storage + text utils）
- [x] README + 初版完成
- [ ] tests + 一次 live 小量驗證
- [ ] README + 收尾

### Incident: SSRN 被 Cloudflare anti-bot 擋
- 兩個 endpoint（feed / html）都回 403，回應 body 是 `Just a moment...` Cloudflare 挑戰頁
- 代表純 `requests` 無法繞過，必須 headless browser（Playwright）才行
- **決定**：不在此版本啟用 SSRN（成本 vs. 效益不划算）。`config.SOURCES['ssrn'].enabled=False`
- **替代**：用 RePEc/NEP 的 `nep-fmk` (Financial Markets) / `nep-rmg` (Risk Management) / `nep-mst` (Microstructure) / `nep-inv` (Investment) 週報，覆蓋同樣的學術論文範圍
- **回滾點**：`feat/quant-paper-crawler` branch 上 commit `Add core framework + arXiv q-fin crawler`

### 收尾總結（Day 0 結束）
- **6 個 enabled source 全綠**：arxiv / nber / repec / fed_feds / aqr / wiley
- **首次 cold-start full run**：seen=230, kept=87
- **每個來源命中率**：
  - wiley: 28/28 (100%) — 最高 signal/noise，因為是專門 futures 期刊
  - aqr: 10/10 (100%) — bypass relevance（publisher-curated）
  - arxiv: 34/100 (34%) — 寬廣 q-fin 池
  - repec: 9/37 (24%)
  - nber: 4/40 (10%) — 一般經濟學論文居多
  - fed_feds: 2/15 (13%) — 央行論文偏宏觀
- **關鍵設計決策**：
  1. SQLite 而非 JSONL — 即用 即查 即過濾
  2. `BaseCrawler.bypass_relevance` — 為 publisher-curated 來源開後門
  3. 每個來源 ≥ 2 秒 host-level delay — 不打擾人
  4. 失敗隔離 — 單一 source 炸不會殺整個 run
- **未解決**：
  - SSRN / CME / Man → 需 Playwright（開頭就決定不在此版本做）
  - NBER 的 `published` 欄位是 HTTP date 字串，沒做日期 normalize
  - AQR / Wiley 沒抓 abstract（要 follow-up 個別抓）

---

## Run @ 2026-05-10T13:53:02Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 34 | — |
| nber | 40 | 4 | — |
| repec | 37 | 9 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 28 | 28 | — |

## Run @ 2026-05-27T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 23 | — |
| nber | 35 | 5 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 22 | 22 | — |

## Run @ 2026-05-28T22:47:51Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 0 | 0 | — |
| nber | 35 | 5 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 22 | 22 | — |

## Run @ 2026-05-29T22:39:24Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 26 | — |
| nber | 35 | 5 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 23 | 23 | — |

## Run @ 2026-05-30T22:30:11Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 26 | — |
| nber | 35 | 5 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 23 | 23 | — |

## Run @ 2026-05-31T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 26 | — |
| nber | 35 | 5 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 23 | 23 | — |

## Run @ 2026-06-01T22:30:14Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 28 | — |
| nber | 35 | 4 | — |
| repec | 58 | 13 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 24 | 24 | — |

## Run @ 2026-06-02T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 35 | 4 | — |
| repec | 48 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 24 | 24 | — |

## Run @ 2026-06-03T22:30:25Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 35 | 4 | — |
| repec | 48 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 24 | 24 | — |

## Run @ 2026-06-04T22:54:24Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 0 | 0 | — |
| nber | 35 | 4 | — |
| repec | 48 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 24 | 24 | — |

## Run @ 2026-06-05T22:30:14Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 35 | 4 | — |
| repec | 48 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 25 | 25 | — |

## Run @ 2026-06-06T22:47:07Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 0 | 0 | ReadTimeout: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed  |
| nber | 35 | 4 | — |
| repec | 48 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 25 | 25 | — |

## Run @ 2026-06-07T22:30:15Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 35 | 4 | — |
| repec | 49 | 6 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 16 | 16 | — |

## Run @ 2026-06-08T22:30:11Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 27 | 3 | — |
| repec | 50 | 7 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 17 | 17 | — |

## Run @ 2026-06-15T22:30:14Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 30 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-06-16T22:30:15Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 30 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-06-17T22:30:13Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 30 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-06-18T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 28 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 19 | 19 | — |

## Run @ 2026-06-19T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-20T22:30:13Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 28 | 6 | — |
| repec | 47 | 9 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-21T22:30:13Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 28 | 6 | — |
| repec | 47 | 10 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-22T22:30:14Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 29 | 4 | — |
| repec | 52 | 9 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-23T22:30:16Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 22 | — |
| nber | 29 | 4 | — |
| repec | 61 | 17 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-25T22:30:35Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 22 | — |
| nber | 29 | 4 | — |
| repec | 61 | 17 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 21 | 21 | — |

## Run @ 2026-06-30T22:30:25Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 22 | 4 | — |
| repec | 53 | 17 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 22 | 22 | — |

## Run @ 2026-07-23T22:30:18Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 26 | — |
| nber | 39 | 5 | — |
| repec | 68 | 17 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 20 | 20 | — |

## Run @ 2026-07-24T22:30:17Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 39 | 5 | — |
| repec | 65 | 14 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 20 | 20 | — |

## Run @ 2026-07-25T22:55:18Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 0 | 0 | ReadTimeout: HTTPSConnectionPool(host='export.arxiv.org', port=443): Read timed  |
| nber | 39 | 5 | — |
| repec | 65 | 14 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 20 | 20 | — |

## Run @ 2026-07-26T22:30:13Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 39 | 5 | — |
| repec | 65 | 14 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 20 | 20 | — |

## Run @ 2026-08-15T22:30:20Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 33 | — |
| nber | 22 | 5 | — |
| repec | 37 | 6 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 17 | 17 | — |

## Run @ 2026-08-16T22:30:16Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 33 | — |
| nber | 22 | 5 | — |
| repec | 37 | 6 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 17 | 17 | — |

## Run @ 2026-08-17T22:30:12Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 32 | — |
| nber | 42 | 5 | — |
| repec | 62 | 16 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-08-18T22:30:15Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 29 | — |
| nber | 42 | 5 | — |
| repec | 62 | 16 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-08-19T22:30:14Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 25 | — |
| nber | 42 | 5 | — |
| repec | 62 | 16 | — |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-08-20T22:32:04Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 25 | — |
| nber | 42 | 5 | — |
| repec | 0 | 0 | ReadTimeout: HTTPSConnectionPool(host='nep.repec.org', port=443): Read timed out |
| fed_feds | 15 | 3 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-08-24T22:30:19Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 25 | — |
| nber | 26 | 1 | — |
| repec | 57 | 8 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |

## Run @ 2026-08-25T22:30:22Z

| source | seen | kept | error |
|--------|-----:|-----:|-------|
| arxiv | 100 | 27 | — |
| nber | 26 | 1 | — |
| repec | 57 | 8 | — |
| fed_feds | 15 | 2 | — |
| aqr | 10 | 10 | — |
| wiley | 18 | 18 | — |
