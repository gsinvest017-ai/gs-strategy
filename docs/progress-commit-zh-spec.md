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

### M1 — 進度檔 + 偵測 ✅
確認 repo CLAUDE.md 未含 commit 規則；最近 30 commit 全英文；無既有 hook。
Commit: `M1: 規範 git commit message 用中文寫（本 repo 落地）— 計畫`

### M2 — spec 本體 + repo CLAUDE.md ✅
- 新增 `docs/spec/git-commit-style.md`（7 章：為什麼、規範、do/don't 範例、
  例外、機械檢查、不改寫歷史、參考）
- `CLAUDE.md` 加「Git commit message」段引向 spec
Commit: `M2: 新增 git commit message 中文規範 spec + repo CLAUDE.md 引用`

### M3 — validator + 測試 ✅
- `scripts/check_commit_msg.py`（純 stdlib）：
  - `_is_cjk()` 偵測 CJK Unified Ideographs
  - `PREFIX_RE` 認 `Mn:` / `feat:` / `fix:` / 等 prefix（不算進長度上限）
  - `SKIP_AUTO_RE` 跳過 merge / revert / dependabot / lockfile 機械訊息
  - `TRAILER_RE` 跳過 git trailer（不計 body 行寬）
  - 規則：subject 必含 ≥1 CJK 字 + ≤72 字（不含 prefix）+ body 行視覺寬度 ≤100
  - CLI：支援 `<ref>` / `--file` / `--stdin`、`--strict` 模式
  - 預設 lint 模式（exit 0），避免擋住正當開發
- `tests/test_check_commit_msg.py`：35 案例（中文/英文/prefix/長度/trailer/
  機械訊息/CLI 三種 input/strict exit code）
Commit: `M3: 加 check_commit_msg.py validator 與 35 個 pytest 案例`

### M4 — git hook 安裝機制 + 報告 ✅
- `scripts/hooks/commit-msg`：呼叫 validator；`STRICT=0` 預設 lint 不擋
- `scripts/install_hooks.sh`：`install` / `--uninstall` / `--status` 三 mode
  - 用 symlink 連到 `scripts/hooks/`（追蹤檔案，多人共享同一份）
  - 既有 hook 自動備份 `.backup-<ts>`
  - **本任務不自動 install**（per safe-yolo 強制停下：動 `.git/` 屬 working
    tree 外，需使用者明確跑 `./scripts/install_hooks.sh`）
- bash -n 語法檢查 + `--status` 印「未安裝」確認狀態正確
Commit: `M4: 加 commit-msg hook 與 install_hooks.sh（不自動掛載）`

## 結論

spec 從口頭約定變成可機械檢查的規範。validator 預設 lint 模式不擋人，要強制
阻擋的人自行把 `scripts/hooks/commit-msg` 的 `STRICT=0` 改 `1`。

啟用 hook：
```bash
./scripts/install_hooks.sh             # 安裝 symlink
./scripts/install_hooks.sh --status    # 看目前狀態
./scripts/install_hooks.sh --uninstall # 撤
```

## 後續方向

- 把 validator 加進 `daily-summary` / `git-tag` skill 的 sanity-check 步驟
- 接 GitHub Actions：PR 上的 commits 都跑一次 `--strict` lint，違規打 review comment
- 視需要擴 spec：規範 commit body 段落結構（e.g. 是否要 What / Why / How）
