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
- [ ] 核心框架 (config / storage / base / logger)
- [ ] arXiv crawler
- [ ] NBER crawler
- [ ] SSRN crawler
- [ ] 機構研究 crawler (CME / Fed / AQR / Man)
- [ ] CLI orchestrator
- [ ] tests + 一次 live 小量驗證
- [ ] README + 收尾

---
