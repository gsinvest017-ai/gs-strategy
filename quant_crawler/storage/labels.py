"""Persistence for human-applied paper labels (kind override + manual subcats).

Kept in a separate table from ``papers`` so a re-crawl (which upserts papers)
never wipes manual annotations. Auto kind/sub-categories are derived on read
(see quant_crawler.paper_class); only human edits live here.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from quant_crawler.config import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_labels (
    source         TEXT NOT NULL,
    source_id      TEXT NOT NULL,
    kind_override  TEXT,
    manual_subcats TEXT NOT NULL DEFAULT '[]',
    updated_at     TEXT,
    PRIMARY KEY (source, source_id)
);
"""

_VALID_KINDS = {"strategy", "factor"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LabelStore:
    def __init__(self, path: Path = DB_PATH) -> None:
        ensure_dirs()
        self.path = Path(path)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- reads ----
    def get(self, source: str, source_id: str) -> Dict:
        with self._conn() as c:
            row = c.execute(
                "SELECT kind_override, manual_subcats FROM paper_labels "
                "WHERE source=? AND source_id=?",
                (source, source_id),
            ).fetchone()
        if row is None:
            return {"kind_override": None, "manual_subcats": []}
        return {
            "kind_override": row["kind_override"],
            "manual_subcats": json.loads(row["manual_subcats"] or "[]"),
        }

    def all_labels(self) -> Dict[Tuple[str, str], Dict]:
        """Bulk load every label keyed by (source, source_id) for fast joins."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT source, source_id, kind_override, manual_subcats "
                "FROM paper_labels"
            ).fetchall()
        return {
            (r["source"], r["source_id"]): {
                "kind_override": r["kind_override"],
                "manual_subcats": json.loads(r["manual_subcats"] or "[]"),
            }
            for r in rows
        }

    # ---- writes ----
    def _upsert(self, source: str, source_id: str,
                kind_override: Optional[str], manual_subcats: List[str]) -> None:
        with self._conn() as c:
            c.execute(
                """
                INSERT INTO paper_labels (source, source_id, kind_override,
                    manual_subcats, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source, source_id) DO UPDATE SET
                    kind_override=excluded.kind_override,
                    manual_subcats=excluded.manual_subcats,
                    updated_at=excluded.updated_at
                """,
                (source, source_id, kind_override,
                 json.dumps(manual_subcats, ensure_ascii=False), _now()),
            )

    def add_subcat(self, source: str, source_id: str, tag: str) -> Dict:
        tag = tag.strip().lower()
        if not tag:
            raise ValueError("empty subcategory tag")
        cur = self.get(source, source_id)
        subs = cur["manual_subcats"]
        if tag not in subs:
            subs = subs + [tag]
        self._upsert(source, source_id, cur["kind_override"], subs)
        return self.get(source, source_id)

    def remove_subcat(self, source: str, source_id: str, tag: str) -> Dict:
        tag = tag.strip().lower()
        cur = self.get(source, source_id)
        subs = [t for t in cur["manual_subcats"] if t != tag]
        self._upsert(source, source_id, cur["kind_override"], subs)
        return self.get(source, source_id)

    def set_kind(self, source: str, source_id: str,
                 kind: Optional[str]) -> Dict:
        if kind is not None and kind not in _VALID_KINDS:
            raise ValueError(f"kind must be one of {_VALID_KINDS} or null")
        cur = self.get(source, source_id)
        self._upsert(source, source_id, kind, cur["manual_subcats"])
        return self.get(source, source_id)
