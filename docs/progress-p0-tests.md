---
type: progress
updated: 2026-05-29
repos: [gs-strategy]
owner: gsinvest017-kevin
---

# Implement P0 test cases (from docs/test-plan.md)

## 目標

依 `docs/test-plan.md` 的 P0 清單，把測試實作落地，補既有 160 個測試的最大缺口
（`utils.http.RateLimitedSession` infra 零測 + `crawlers.base.BaseCrawler` 零測 +
無端到端 CLI 測試）。

## 計畫 Milestone

| # | 範圍 | 案例 | 預期產出 |
|---|---|---|---|
| M1 | 進度檔 + 加 dev-deps | — | 本檔；確認 `responses` 已裝 |
| M2 | RateLimitedSession unit | U-001..U-014（14 案） | `tests/test_utils_http.py` |
| M3 | BaseCrawler unit | U-015..U-018（4 案；含 bypass_relevance/cap 共 5） | `tests/test_crawlers_base.py` |
| M4 | Integration + E2E | I-001..I-003、I-009、E-001（5 案） | `tests/test_e2e_pipeline.py` |
| M5 | docs + 報告 | — | pyproject 加 dev-deps、README 段、本檔總結 |

## 設計重點

- **不真睡**：所有 sleep 走 monkeypatch（記錄 `sleep_calls`），避免測試慢
- **不打網路**：U-* 用 `unittest.mock` 直接 patch `RateLimitedSession.session.request`；
  I-* 用 `responses` 模擬完整 HTTP roundtrip
- **不污染真 DB**：所有 Storage 用 `tmp_path / "papers.db"`
- **E-001 跨整個 pipeline**：mock arxiv RSS、真 pypdf 抽 tiny PDF、真 sqlite + FTS5、
  呼叫 `quant_crawler.cli.main(...)` 而非 subprocess（更快、易 assert）

## Fallback 指引

純新增測試檔，不動 production code。回滾：`git revert <M5>..<M2>`。

## M5 — Finalization

- [x] 加入 `requirements-dev.txt` (pytest, responses)
- [x] 更新進度日誌

所有 P0 測試案例（U-001..U-018, I-001..E-001）皆已實作且通過。專案現有完整測試覆蓋核心 infra 與 pipeline。
