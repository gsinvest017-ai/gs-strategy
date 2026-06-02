#!/usr/bin/env python3
"""一次性修復 papers.db 內被 latin-1 誤解碼的 mojibake 標題（中文亂碼）。

背景：上傳功能早期版本用 latin-1 解 multipart header，UTF-8 中文檔名變
mojibake，存進 `papers.title`。本工具把可還原的標題改回正確中文。

只動「重新 latin-1→utf-8 解碼後**會改變且仍為有效 UTF-8**」的 row，
純 ASCII / 已正確的中文都不碰。預設 dry-run，需 `--apply` 才寫 DB。

用法：
    fix_manual_titles.py                 # dry-run：列出會改的 row
    fix_manual_titles.py --apply         # 實際更新
    fix_manual_titles.py --source manual # 限定來源（預設全部）
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from quant_crawler.config import DB_PATH
from quant_crawler.webui.upload import _fix_utf8


def _looks_mojibake(s: str) -> bool:
    """判斷字串是否像「UTF-8 被 latin-1 解碼」的 mojibake。

    特徵：含 latin-1 補充區常見的 mojibake 前導位元組（Ã / Â / å / ä / é …）
    且 _fix_utf8 後字串確實改變。
    """
    fixed = _fix_utf8(s)
    return fixed != s


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DB_PATH)
    p.add_argument("--source", help="限定 source（預設全部）")
    p.add_argument("--apply", action="store_true", help="實際寫 DB（預設 dry-run）")
    args = p.parse_args(argv)

    if not Path(args.db).is_file():
        print(f"找不到 DB：{args.db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    sql = "SELECT source, source_id, title FROM papers"
    params = []
    if args.source:
        sql += " WHERE source = ?"
        params.append(args.source)
    rows = conn.execute(sql, params).fetchall()

    fixes = []
    for r in rows:
        title = r["title"] or ""
        if _looks_mojibake(title):
            fixes.append((r["source"], r["source_id"], title, _fix_utf8(title)))

    if not fixes:
        print("沒有需要修復的標題。")
        conn.close()
        return 0

    for src, sid, old, new in fixes:
        print(f"[{src}:{sid}]")
        print(f"  舊: {old!r}")
        print(f"  新: {new}")

    if not args.apply:
        print(f"\nDry-run：{len(fixes)} 筆可修復。加 --apply 實際更新。")
        conn.close()
        return 0

    for src, sid, _old, new in fixes:
        conn.execute(
            "UPDATE papers SET title = ? WHERE source = ? AND source_id = ?",
            (new, src, sid),
        )
    conn.commit()
    conn.close()
    print(f"\n已修復 {len(fixes)} 筆標題。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
