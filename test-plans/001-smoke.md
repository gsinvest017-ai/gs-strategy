---
id: 001-smoke
title: 最小可運作 smoke — gs-strategy
runner: playwright-mcp
created: 2026-05-29
tags: [demo, smoke]
estimated_seconds: 45
---

## 我想知道

開 `http://192.168.0.249:5057/` (gs-strategy webui dashboard)，截一張首頁圖，
確認以下幾件事，最後寫一段感想：

- summary 卡片區是否顯示「論文/報告總量」、「策略 / 因子」、「已下載 PDF」
- 「論文/報告來源分布」長條圖是否有資料（≥ 1 source）
- footer 是否顯示 server 啟動時間 + code git hash

## 提示

- 若 server 沒起，去  `~/gs-strategy` 跑 `./run.sh` 後再試
- LAN 主機 IP `192.168.0.249` 是 Windows 主機；若 portproxy 未設可改打
  `http://localhost:5057/` 或 `http://100.104.1.39:5057/`（tailnet）
