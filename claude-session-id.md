# Claude Code Session 恢復資訊

## 當前 Session
- **Session ID**: `f3349183-1543-4def-9ec5-6b3782f8b1d2`
- **建立日期**: 2026-05-10
- **工作目錄**: `/home/kevin/yolo-claude`
- **模型**: claude-opus-4-7 (1M context)
- **JSONL 路徑**: `~/.claude/projects/-home-kevin-yolo-claude/f3349183-1543-4def-9ec5-6b3782f8b1d2.jsonl`

## SSH 斷線後恢復方式

```bash
# 1. 重新 ssh 進入機器後
cd ~/yolo-claude

# 2. 用 --resume 旗標帶 session id 恢復
claude --resume f3349183-1543-4def-9ec5-6b3782f8b1d2

# 或是互動式選擇
claude --resume
# 然後從清單裡挑這個 session id
```

## 替代方案

```bash
# 如果 --resume 失效，可改用 --continue 接續最近一次對話
claude --continue
```

## 當前任務脈絡 (給未來的我參考)

從 `data/papers.db` (87 篇論文 metadata) 篩出可在台灣期貨市場跑的策略，
直接寫成 **Zipline-TEJ × TQuant-Lab** 框架的回測程式碼 + config。
產出物存放於 `strategies/` 目錄，進度紀錄於 `docs/progress-taiwan-futures.md`。

## 歷史 Sessions

| Session ID | 日期 | 用途 |
|---|---|---|
| `d4c2df18-af39-4f44-9178-9a8dad8541c8` | 2026-05-10 早 | 較舊 |
| `ef7a3fe2-e7af-4ca2-8531-e875f246ba57` | 2026-05-10 中 | 中間 |
| `f3349183-1543-4def-9ec5-6b3782f8b1d2` | 2026-05-10 晚 | **目前** — 台灣期貨策略 |
