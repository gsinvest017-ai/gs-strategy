"""Discover the Taiwan single-stock futures universe via TEJ's helper.

Output: a sorted JSON file with (stock_code, future_root) pairs and an
optional top-N slice used to drive ingest of the `tquant_future` bundle.

Why this script exists
----------------------
The 4th strategy `xsmom_stkfut_rmt` needs at least `min_universe` (default 20)
stock-futures roots available in the bundle. We ingest a curated head of the
TEJ universe rather than all 247 roots to keep TEJ API time bounded.

Usage
-----
    .venv-bt/bin/python scripts/discover_stock_futures_universe.py \\
        --start 2020-01-01 --end 2026-04-30 --limit 30 \\
        --out data/stock_futures_universe.json

The output JSON has the shape:

    {
        "fetched_at": "...",
        "start": "...",
        "end":   "...",
        "all": [{"code": "1303", "root": "CAF"}, ...],   # full universe
        "head": ["CAF", "CBF", ...]                       # top-N roots only
    }
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def _load_env(env_file: Path) -> None:
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2020-01-01")
    ap.add_argument("--end", default=datetime.now().date().isoformat())
    ap.add_argument("--limit", type=int, default=30,
                    help="number of roots to write into 'head' slice (top N)")
    ap.add_argument("--out", default="data/stock_futures_universe.json")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    _load_env(repo_root / ".env")

    if not os.environ.get("TEJAPI_KEY"):
        print("[discover] TEJAPI_KEY not set (.env missing?)", file=sys.stderr)
        return 1

    from zipline.TQresearch.futures_package import get_stock_futures_universe

    codes, roots = get_stock_futures_universe(st=args.start, et=args.end)
    if len(codes) != len(roots):
        print(f"[discover] WARN length mismatch: codes={len(codes)} roots={len(roots)}",
              file=sys.stderr)

    pairs = [{"code": c, "root": r} for c, r in zip(codes, roots)]
    head = roots[: args.limit]

    out_path = repo_root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "start": args.start,
        "end": args.end,
        "n_total": len(pairs),
        "n_head": len(head),
        "all": pairs,
        "head": head,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    print(f"[discover] wrote {out_path}")
    print(f"[discover] total roots: {len(pairs)}, head ({args.limit}): {' '.join(head)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
