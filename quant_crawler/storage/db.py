"""SQLite persistence layer for PaperRecord."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Optional

from quant_crawler.config import DB_PATH, ensure_dirs
from quant_crawler.storage.models import PaperRecord
from quant_crawler.utils.logging import get_logger

log = get_logger("storage")


SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    source        TEXT NOT NULL,
    source_id     TEXT NOT NULL,
    title         TEXT NOT NULL,
    authors       TEXT NOT NULL DEFAULT '[]',
    abstract      TEXT NOT NULL DEFAULT '',
    published     TEXT,
    updated       TEXT,
    url           TEXT NOT NULL DEFAULT '',
    pdf_url       TEXT NOT NULL DEFAULT '',
    categories    TEXT NOT NULL DEFAULT '[]',
    keywords_hit  TEXT NOT NULL DEFAULT '[]',
    doi           TEXT NOT NULL DEFAULT '',
    raw_extra     TEXT NOT NULL DEFAULT '{}',
    fetched_at    TEXT NOT NULL,
    PRIMARY KEY (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published DESC);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi) WHERE doi != '';
CREATE INDEX IF NOT EXISTS idx_papers_source ON papers(source);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    items_seen   INTEGER NOT NULL DEFAULT 0,
    items_kept   INTEGER NOT NULL DEFAULT 0,
    error        TEXT
);
"""


_LIST_FIELDS = {"authors", "categories", "keywords_hit"}
_DICT_FIELDS = {"raw_extra"}


def _serialize(rec: PaperRecord) -> dict:
    d = rec.as_row()
    for k in _LIST_FIELDS:
        d[k] = json.dumps(d.get(k) or [], ensure_ascii=False)
    for k in _DICT_FIELDS:
        d[k] = json.dumps(d.get(k) or {}, ensure_ascii=False)
    return d


def _deserialize(row: sqlite3.Row) -> PaperRecord:
    d = dict(row)
    for k in _LIST_FIELDS:
        d[k] = json.loads(d.get(k) or "[]")
    for k in _DICT_FIELDS:
        d[k] = json.loads(d.get(k) or "{}")
    return PaperRecord(**d)


class Storage:
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

    # ---- writes ----
    def upsert(self, rec: PaperRecord) -> bool:
        """Returns True if newly inserted, False if updated."""
        d = _serialize(rec)
        with self._conn() as c:
            cur = c.execute(
                "SELECT 1 FROM papers WHERE source=? AND source_id=?",
                (d["source"], d["source_id"]),
            )
            existed = cur.fetchone() is not None
            c.execute(
                """
                INSERT INTO papers (
                    source, source_id, title, authors, abstract,
                    published, updated, url, pdf_url, categories,
                    keywords_hit, doi, raw_extra, fetched_at
                ) VALUES (
                    :source, :source_id, :title, :authors, :abstract,
                    :published, :updated, :url, :pdf_url, :categories,
                    :keywords_hit, :doi, :raw_extra, :fetched_at
                )
                ON CONFLICT(source, source_id) DO UPDATE SET
                    title=excluded.title,
                    authors=excluded.authors,
                    abstract=excluded.abstract,
                    published=excluded.published,
                    updated=excluded.updated,
                    url=excluded.url,
                    pdf_url=excluded.pdf_url,
                    categories=excluded.categories,
                    keywords_hit=excluded.keywords_hit,
                    doi=excluded.doi,
                    raw_extra=excluded.raw_extra,
                    fetched_at=excluded.fetched_at
                """,
                d,
            )
        return not existed

    def upsert_many(self, recs: Iterable[PaperRecord]) -> tuple[int, int]:
        new, updated = 0, 0
        for r in recs:
            if self.upsert(r):
                new += 1
            else:
                updated += 1
        return new, updated

    # ---- crawl run accounting ----
    def start_run(self, source: str, started_at: str) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO crawl_runs(source, started_at) VALUES (?, ?)",
                (source, started_at),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_id: int,
        finished_at: str,
        items_seen: int,
        items_kept: int,
        error: Optional[str] = None,
    ) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE crawl_runs SET finished_at=?, items_seen=?, items_kept=?, error=? WHERE id=?",
                (finished_at, items_seen, items_kept, error, run_id),
            )

    # ---- reads ----
    def count(self, source: Optional[str] = None) -> int:
        with self._conn() as c:
            if source:
                cur = c.execute("SELECT COUNT(*) FROM papers WHERE source=?", (source,))
            else:
                cur = c.execute("SELECT COUNT(*) FROM papers")
            return cur.fetchone()[0]

    def latest(self, limit: int = 20, source: Optional[str] = None) -> list[PaperRecord]:
        with self._conn() as c:
            if source:
                cur = c.execute(
                    "SELECT * FROM papers WHERE source=? ORDER BY published DESC NULLS LAST, fetched_at DESC LIMIT ?",
                    (source, limit),
                )
            else:
                cur = c.execute(
                    "SELECT * FROM papers ORDER BY published DESC NULLS LAST, fetched_at DESC LIMIT ?",
                    (limit,),
                )
            return [_deserialize(r) for r in cur.fetchall()]

    def search(self, query: str, limit: int = 50) -> list[PaperRecord]:
        like = f"%{query}%"
        with self._conn() as c:
            cur = c.execute(
                """
                SELECT * FROM papers
                WHERE title LIKE ? OR abstract LIKE ? OR authors LIKE ?
                ORDER BY published DESC NULLS LAST
                LIMIT ?
                """,
                (like, like, like, limit),
            )
            return [_deserialize(r) for r in cur.fetchall()]

    def stats_by_source(self) -> list[tuple[str, int]]:
        with self._conn() as c:
            cur = c.execute(
                "SELECT source, COUNT(*) FROM papers GROUP BY source ORDER BY 2 DESC"
            )
            return [(r[0], r[1]) for r in cur.fetchall()]
