---
type: progress
updated: 2026-05-29
repos: [gs-strategy]
owner: gsinvest017-kevin
---

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

### M1 — 計畫 + 設計 ✅
釐清 spec、列必要 schema、規劃 4 milestones。Commit `<M1>`。

### M2 — test-plans/ + 2 個範例 ✅
- `test-plans/001-smoke.md` — webui 首頁 smoke (summary 卡 / 來源分布 / footer)
- `test-plans/002-webui-rag-search.md` — RAG 全文檢索 panel 流程
- `test-plans/README.md` — 本目錄規則、現有 plans、`new`/`validate` 用法
Commit: `M2: test-plans/ with 2 fuzzy plans (smoke + RAG search) + local README`

### M3 — formatter / validator ✅
- `scripts/test_plan_format.py`：
  - `parse_plan(path)` 鏡像 autogo `_is_plan_file()`：2KB 視窗、`---` 框架、
    手刻 `key: value` parser、BOM 容忍、inline 陣列、quoted value 去引號
  - `validate <path>...` / `validate --all` / `list` / `new` subcommands
  - 內建 `_FUZZY_TEMPLATE` 為 fuzzy 風格起手檔
- `tests/test_test_plan_format.py` — 23 案例：
  - skip filename 規則（README.md / dotfile / 一般檔）
  - 必填 id / (title|runner) 路徑
  - frontmatter 邊界 case（無 fm / 沒收尾 / BOM / inline array / quoted）
  - body 抽取、2KB 視窗
  - `new` 生成有效 stub + 拒絕覆寫
  - CLI exit code（validate --all OK / 失敗 file = exit 1）
Commit (amended): `M3: test_plan_format.py validator + new + list (23 pytest cases)`

### M4 — docs + 最終驗證 ✅
- 頂層 README 加 `## autogo dashboard test-plans` 段落
- 本檔總結

Commit: `M4: docs — link autogo test-plans + formatter in top README`

## 結論

`test-plans/001-smoke.md` 與 `002-webui-rag-search.md` 已通過自帶 validator，
autogo 端 `↻ refresh` 即可看到 `<label>:001-smoke` / `<label>:002-webui-rag-search`。

驗證命令：
```bash
.venv/bin/python scripts/test_plan_format.py validate --all   # OK / FAIL
.venv/bin/python -m pytest tests/test_test_plan_format.py     # 23 passed
```

## 後續方向
- 加一支 traced 範例（`js traced-script` fence）驗證 autogo traced runner 也吃得到
- formatter 加 `--format=json` 給 CI 用
- 若 autogo 端報 `cached 0 plans`，先跑 `validate --all` 對照 reasons

