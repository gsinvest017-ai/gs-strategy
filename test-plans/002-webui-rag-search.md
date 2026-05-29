---
id: 002-webui-rag-search
title: RAG 全文檢索 panel — 搜公式關鍵字驗結果
runner: playwright-mcp
created: 2026-05-29
tags: [webui, rag, fuzzy]
estimated_seconds: 75
---

## 我想知道

打開 gs-strategy webui (`http://localhost:5057/`)，捲到「RAG 全文檢索」面板，
驗證它確實能搜原始論文段落：

1. 在搜尋框輸入 `cubic momentum threshold`
2. 點「搜尋」（或按 Enter）
3. 截圖結果表 — 應有至少 1 筆命中，最頂端通常是 arxiv:2605.00854
   （cubic-momentum 論文）
4. 點命中列的論文標題，下方應展開該篇 chunks 預覽
5. 截「子類別 — kind=strategy」按一下 panel 過濾器、回報還剩多少筆

最後 summary 一段：搜尋是否準確、回傳速度、有無 UI 缺陷（例如 sticky header
或 chip 樣式）。

## 提示

- 預設 panel 是 `有 PDF`，要切到 RAG panel（往下捲）
- 結果表有 `score` 欄；分數越**負**越相關（BM25 慣例）
