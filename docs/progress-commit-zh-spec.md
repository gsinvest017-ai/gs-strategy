# 規範 git commit message 用繁體中文寫（本 repo 落地）

## 目標

把 `~/.claude/CLAUDE.md` global 行為規則 #3「Git commit message 主體用繁體中文」
在本 repo 落地為可機械檢查的 spec + 可選 `commit-msg` git hook。
為 Claude（safe-yolo 等 skill）與人類貢獻者提供統一準則與**例外清單**，
避免之後 commit log 中英文混雜、貼到工作群組時語感斷層。

## 偵測現況（基線）

- repo CLAUDE.md：僅描述 YOLO sandbox，**未提 commit 語言規則**
- 最近 30 commit subject：**0 / 29 含中文**（全英文）→ rule 尚未在本 repo 落地
- 無 `scripts/hooks/` / `install_hooks.*`

## Spec 摘要

1. 主體（subject + body 描述句）**用繁體中文**
2. **保留原文**：
   - Prefix：`Mn:` / `feat:` / `fix:` / `refactor:` / `chore:` / `test:`
   - Git trailers：`Co-Authored-By:` / `Signed-off-by:` / `Refs:`
   - 技術識別符：檔名、函式、CLI flag（`--apply` / `--force`）、產品名（`SKILL.md`、`gs-trading-portal`）、API 路徑、stack trace 原文
3. Subject **≤ 72 字（不含 prefix）**；長細節寫進 body 或進度檔
4. 例外：dependabot / lockfile / auto-merge 等機械訊息保留工具預設

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 偵測 | 本檔 |
| M2 | spec 本體 + repo CLAUDE.md reference | `docs/spec/git-commit-style.md`、`CLAUDE.md` 新增段落 |
| M3 | validator + 測試 | `scripts/check_commit_msg.py`（純 stdlib）+ `tests/test_check_commit_msg.py` |
| M4 | hook 安裝機制（不自動裝） | `scripts/hooks/commit-msg`、`scripts/install_hooks.sh`、`docs` 總結 |

## Fallback 指引

- 純新增 doc / script / hook，不動 production code。
- 回滾：`git revert <M4>..<M2>`；或 `rm -rf docs/spec scripts/hooks scripts/install_hooks.sh scripts/check_commit_msg.py tests/test_check_commit_msg.py`
- hook 預設 **不會** 安裝到 `.git/hooks/`；要啟用須手動 `./scripts/install_hooks.sh`

## 進度日誌

（每完成一個 milestone 在下方追加 `## Mn — <title>` 段落。）
