# test-plans/ — autogo dashboard import contract

本目錄是 [autogo](https://github.com/) dashboard 從 gs-strategy import 用的
**source-repo test plans** 區。每支 `.md` 是一份「請 Claude / Playwright
代你跑一次某種 UI flow」的測試計畫；autogo 端按 `↻ refresh` 即可抓回去。

> autogo 用 lowercase 比對忽略 `README.md`，所以本檔不會被當 plan 匯入。

## 規則速查

```
<repo>/test-plans/<id>.md       ← 首選位置
<repo>/<id>.md                  ← fallback（不建議，會混進其他 .md）
```

`autogo._is_plan_file()` 接受的條件：

1. 檔案前 2KB 是 YAML frontmatter（以 `---` 開頭、下一個 `---` 收尾）
2. frontmatter 內**必須**有 `id:` 鍵，並且 **`title:` 或 `runner:` 至少一個**

被略過的：

- `README.md`（lowercase 比對）
- dotfile (`.foo.md`)
- 沒 frontmatter / frontmatter 不合格的 `.md`
- 把 `id:` 改成 `id_skip:` 也會被過濾（保留歷史 demo 用）

## Frontmatter schema

| key | 必填 | 範例 | 說明 |
|---|---|---|---|
| `id` | ✅ | `001-smoke` | 唯一識別。建議跟檔名一致。autogo 端 namespace 顯示為 `<label>:<id>` |
| `title` 或 `runner` (≥1) | ✅ | `title: webui smoke` / `runner: playwright-mcp` | 兩個任一即可，通常都寫 |
| `runner` | 建議 | `playwright-mcp` / `playwright-traced` / `chrome-devtools-mcp` | 預設 `playwright-mcp` |
| `tags` | 選 | `[demo, smoke]` | inline 陣列，給 UI 過濾 |
| `created` | 選 | `2026-05-29` | UI 顯示 |
| `browser` | 選 | `chromium-fresh` / `chrome-persistent` | traced runner 用 |
| `url` | 選 | `https://example.com` | 純資訊 |
| `estimated_seconds` | 選 | `60` | UI hint |

> ⚠️ 一行一條 `key: value`，不支援多行 nested；陣列只認 inline `[a, b, c]`。

## 本目錄現有 plans

| id | runner | 用途 |
|---|---|---|
| `001-smoke` | playwright-mcp | webui 首頁 smoke：summary 卡 / 來源分布 / footer |
| `002-webui-rag-search` | playwright-mcp | RAG 全文檢索 panel：搜「cubic momentum threshold」驗結果 |

## 怎麼新增一支

```bash
# 互動生成（會問你 id / title / runner / tags）
.venv/bin/python scripts/test_plan_format.py new

# 直接指定
.venv/bin/python scripts/test_plan_format.py new 003-my-plan \
    --title "我的 plan" --runner playwright-mcp

# 驗證所有現有 plans 是否符合 autogo schema
.venv/bin/python scripts/test_plan_format.py validate --all
```

## 兩種 plan 風格

- **Fuzzy**（本目錄預設）— body 短，自然語言描述「我想知道什麼」，autogo 端會
  spawn Claude 自己決定每一步。
- **Traced** — body 含 `js traced-script` code fence，逐步寫死 Playwright 動作。
  詳見 spec §3.B。

設計詳記 `docs/progress-test-plans.md`。
