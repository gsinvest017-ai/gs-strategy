# Test-plans for autogo dashboard import

## 目標

依 autogo "Source repo test plans" import contract，把 gs-strategy 變成可被
autogo dashboard `/plans` import 的 source repo。產出：
1. `test-plans/<id>.md` 至少 2 支符合 schema 的 plan（minimal smoke + webui flow）
2. `test-plans/README.md` 講清楚本 repo 的命名 / 規則
3. `scripts/test_plan_format.py` formatter + validator（mirrors autogo `_is_plan_file()`）
   含 `validate` / `new` / `list` subcommands + pytest

## 必要 schema（從 spec 抽出）

`_is_plan_file()` 兩條：
1. 檔案前 2KB 起始為 `---\n` frontmatter，下一個 `---\n` 收尾
2. frontmatter 內至少有 `id:` AND (`title:` OR `runner:`)

額外規則：
- `README.md`（lowercase 比對）跳過
- dotfile (`.foo.md`) 跳過
- `id_skip:` 取代 `id:` → 被過濾（不 import）
- BOM strip
- 一行一條 `key: value`，不支援多行 nested；陣列只認 inline `[a, b, c]`

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 設計 | 本檔 |
| M2 | test-plans/ + 範例 | `001-smoke.md` + `002-webui-rag.md` + `test-plans/README.md` |
| M3 | formatter / validator | `scripts/test_plan_format.py` + `tests/test_test_plan_format.py` |
| M4 | docs + 最終驗證 | README 連結、本檔總結 |

## Fallback 指引

純新增 `test-plans/` 目錄 + 一支 script，不動 production code。回滾：
`rm -rf test-plans/ scripts/test_plan_format.py tests/test_test_plan_format.py`
或 `git revert <M4>..<M2>`。

## 進度日誌

（每完成一個 milestone 在下方追加 `## Mn — <title>` 段落。）
