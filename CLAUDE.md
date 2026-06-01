# yolo-claude

實驗用 sandbox：測試 Claude Code 在「不停下來問問題」模式下的行為。

## 權限設定 (僅作用於此專案)

`.claude/settings.json` 的設定只在此目錄被 Claude Code 啟動時生效，不影響其他專案：

- `defaultMode: bypassPermissions` — 啟動時自動進入 YOLO 模式，跳過所有權限提示
- `permissions.allow` — 預先放行常用工具
- `permissions.deny` — 即使 YOLO 模式仍封鎖明顯危險指令（`rm -rf /`、`sudo`、`curl | sh` 等）

## 快速測試其他模式

```bash
# 進入此目錄後
cd ~/yolo-claude

# 預設 (此 repo 已是 bypassPermissions)
claude

# 切回較保守的 acceptEdits
claude --permission-mode acceptEdits

# Headless / 一次跑完不互動
claude -p "幫我寫個 fizzbuzz.py"

# 互動中按 Shift+Tab 可在 plan / acceptEdits / bypassPermissions 間切換
```

## 行為指令

- 視此目錄為可拋棄的 sandbox：可大膽嘗試危險操作的測試。
- 除非觸碰 `permissions.deny` 範圍，不需中途確認。
- 仍須避免影響此目錄以外的檔案系統。

## Git commit message

**主體用繁體中文**，保留 prefix（`Mn:` / `feat:` / `fix:` 等）、git trailer、
檔名/函式/CLI flag/專案名等技術識別符原文。Subject ≤ 72 字，不寫小說。
完整 spec 見 [`docs/spec/git-commit-style.md`](docs/spec/git-commit-style.md)；
全域對應規則在 `~/.claude/CLAUDE.md` Behavior rule #3。

機械檢查：`scripts/check_commit_msg.py HEAD`
（自動掛 hook：`./scripts/install_hooks.sh`）
