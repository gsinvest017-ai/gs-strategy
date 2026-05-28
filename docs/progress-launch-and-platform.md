# One-button launch + platform compatibility

## 目標

(A) **One-button launch**：產生跨平台單一入口 `run.sh` + `run.ps1`，從零（沒 venv、沒 deps、沒 PDF）到 webui 跑起來一條龍。
(B) **Platform compatible**：稽核 cross-platform 風險、加 `.gitattributes` 統一 EOL，至少讓 Windows + WSL/Linux clone 後不會 LF/CRLF 衝突。

## 偵測現況

- 頂層 launcher：**無** `run.sh` / `run.ps1` / `Makefile` / `package.json`
- `scripts/` 內 6 個 `.sh`（setup-bt / ingest_futures / run_webui / run_strategy / daily_refresh / install_daily_refresh）— **零 `.ps1` 對應**
- `.gitattributes`：**無** → CRLF/LF 跨 OS 不受控
- `pyproject.toml`：有 `[project.scripts] quant-crawl = quant_crawler.cli:main`

## 計畫 Milestone

| # | 名稱 | 預期產出 |
|---|---|---|
| M1 | 進度檔 + 偵測 | 本檔 |
| M2 | /one-button-launch | 頂層 `run.sh` + `run.ps1`（detect → venv → install → optional ingest → start webui） |
| M3 | /platform-compatible 稽核 + 修補 | 稽核報告（嵌進本檔）+ `.gitattributes` 統一 EOL |
| M4 | docs + 報告 | README 補充、本檔總結 |

## /one-button-launch 設計

頂層 `run.sh` / `run.ps1`，no-arg = 啟動 webui（最常用）；子指令 = 進階流程：

```
./run.sh                 # = setup + start webui
./run.sh setup           # 建 .venv（若無）+ pip install -e . + 安裝 RAG 套件
./run.sh webui           # 啟動 webui dashboard（5057）
./run.sh crawl           # 跑爬蟲 + fetch-pdfs + rag-ingest
./run.sh test            # pytest tests/
./run.sh help
```

PowerShell 對應 `.\run.ps1 setup|webui|crawl|test|help`。

設計原則：
- 不重寫既有 `scripts/*.sh` 邏輯，**包裝 + 串接**
- 預設「沒 venv 就建」、「沒裝 deps 就裝」、「沒 .env 就提示」
- Windows 端在 WSL 下跑 `.sh` / 在 PowerShell 跑 `.ps1`；兩邊都連到 venv 內的 Python

## /platform-compatible 稽核重點

| 類別 | 現況 | 處理 |
|---|---|---|
| EOL / .gitattributes | 無 | 加 `.gitattributes`：`*.sh text eol=lf`、`*.ps1 text eol=crlf`、`*.py / *.md text` |
| 路徑分隔符 | Python 用 `pathlib.Path` ✓ | 略 |
| Shell script 跨平台 | 只有 `.sh` | M2 補上 `.ps1` 對應 |
| 環境變數語法 | `$VAR` (bash) vs `$env:VAR` (PowerShell) | M2 .ps1 直接寫 PowerShell 語法 |
| 原生相依 | sqlite3 / urllib / pypdf / requests / pyyaml / jinja2 / mcp — 全純 Python | ✓ |
| 檔名大小寫 / 保留字 | 無 `NUL`/`CON`/`AUX` 等 Windows 保留字；都 lowercase | ✓ |
| CI matrix | 無 CI | 略（本任務不引 CI） |
| 檔案編碼 | 全 UTF-8 | ✓ |

## Fallback 指引

- `run.sh` / `run.ps1` 只是 wrapper，刪了不影響任何既有功能；`git rm run.sh run.ps1`
- `.gitattributes`：移除即恢復現狀；不會 retroactive 改既有檔案
- 整段：`git revert <M4>..<M2>`，或 `git reset --hard a737a81`（layout-compact M3 commit）

## 進度日誌

（每完成一個 milestone 在下方追加 `## M<n> — <title>` 段落。）
