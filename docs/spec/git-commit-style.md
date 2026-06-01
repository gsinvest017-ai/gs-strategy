# Spec — Git commit message 風格（本 repo）

> 對應 `~/.claude/CLAUDE.md` global 行為規則 #3 的 repo-level 落地版。
> Claude (含 safe-yolo / git-tag / daily-summary skills) 與人類貢獻者皆適用。

## 1. 為什麼

- 維護者主要語言為繁體中文，commit log 由本人直接 review，中文閱讀效率高
- `/git-tag` 切 milestone group、`/daily-summary`、`/copy-commits-button` 產的中文摘要要與 commit 標題語感一致
- 貼到工作群組訊息不要有語言斷層

## 2. 規範

**Subject + body 描述句用繁體中文**，但下列 token 一律 **保留原文**：

| 保留原文的 token | 範例 |
|---|---|
| Prefix | `Mn:` / `feat:` / `fix:` / `refactor:` / `chore:` / `test:` / `docs:` |
| Git trailer | `Co-Authored-By:` / `Signed-off-by:` / `Refs:` / `Closes #123` |
| 檔名 / 路徑 | `quant_crawler/cli.py`、`docs/spec/git-commit-style.md` |
| 函式 / 類別 / 屬性 | `RateLimitedSession`、`fetch_pending()`、`paper_class.classify_kind` |
| CLI flag | `--apply`、`--force`、`--push`、`--scope=colors` |
| 環境變數 / 設定鍵 | `QC_DATA_DIR`、`bypassPermissions` |
| 專案 / 套件名 | `SKILL.md`、`gs-trading-portal`、`autogo`、`pypdf`、`mcp` |
| API 路徑 / HTTP code | `/api/labels`、HTTP 401、`POST /api/papers` |
| 引用的英文錯誤訊息 / stack trace 原文 | `ModuleNotFoundError: No module named 'numpy'` |

**格式**：
- Subject **≤ 72 字（不含 prefix）**
- 不要寫小說 — 細節進 body 或進度檔
- Body 可選；若有，與 subject 間以空行分隔，每段每行 ≤ 80 字
- Git trailer 在最末段，與 body 以空行分隔

## 3. 範例（do / don't）

### ✅ 好

```
M2: 把 RateLimitedSession 改成支援 Retry-After 標頭

依 spec U-004 在 `_retry_after()` 內優先讀 `Retry-After`，
非數字才走 backoff。新增 14 個 unit case 覆蓋 429/503 鏈。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

```
fix: 修 webui POST `/api/labels` 在空 body 時 500 的 bug
```

```
docs: 補 README 的 `run.sh` / `run.ps1` 跨平台用法
```

### ❌ 不建議

```
M2: add support for retry-after header in RateLimitedSession
^^^ 純英文 subject — 違反規則
```

```
M2: 修正了一個關於 retry-after header 在某些情況下處理不正確且導致 503 持續累積的問題並補充了相關的測試覆蓋
^^^ 過長（>72 字）且寫小說
```

```
M2: 改 「RateLimitedSession」 的 「_retry_after」
^^^ 給類別/函式加了多餘的中文引號 — 程式識別符應保持原文裸寫
```

## 4. 例外

下列情境**不**強制中文，沿用工具預設訊息即可：

- 機械化工具產生的 commit：`dependabot`、lockfile 重生、`auto-merge`
- 他人撰寫的 commit / merge / cherry-pick 過來的歷史 commit 一律不改
- `Merge pull request #N` / `Revert "..."` 等 git 預設訊息可保留

## 5. 機械檢查

repo 提供 `scripts/check_commit_msg.py` 做 lint：

```bash
# 檢查最後一次 commit 的訊息
.venv/bin/python scripts/check_commit_msg.py HEAD

# 檢查任一 commit message 檔（git hook 用）
.venv/bin/python scripts/check_commit_msg.py --file .git/COMMIT_EDITMSG
```

啟用 `commit-msg` git hook（每次 commit 自動 lint）：

```bash
./scripts/install_hooks.sh           # 安裝（symlink 到 .git/hooks/）
./scripts/install_hooks.sh --uninstall
```

hook 預設**警告不阻擋**（exit 0 + stderr 提示），避免擋住正當的混語 commit；
要轉成強制阻擋，把 hook 內 `STRICT=0` 改 `STRICT=1`。

## 6. 怎麼套到既有 commit

**不要** retroactively 改寫歷史。本 spec 只規範**新** commit，舊 commit 維持原樣。

## 7. 參考

- Global 規則：`~/.claude/CLAUDE.md` Behavior rule #3
- 設計與決策：`docs/progress-commit-zh-spec.md`
