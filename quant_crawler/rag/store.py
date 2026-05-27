"""SQLite FTS5 chunk store + BM25 retrieval for paper/report full text.

Lives in the same ``papers.db`` so chunks join cleanly to ``papers`` /
``paper_labels`` on (source, source_id).
"""
from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from quant_crawler.config import DB_PATH, ensure_dirs

SCHEMA = """
CREATE TABLE IF NOT EXISTS rag_chunks (
    source     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    chunk_idx  INTEGER NOT NULL,
    page       INTEGER,
    text       TEXT NOT NULL,
    PRIMARY KEY (source, source_id, chunk_idx)
);
CREATE VIRTUAL TABLE IF NOT EXISTS rag_fts USING fts5(
    text,
    source UNINDEXED,
    source_id UNINDEXED,
    chunk_idx UNINDEXED,
    tokenize = 'unicode61'
);
"""

# FTS5 query syntax is picky; strip operators from free-text user queries and
# OR the surviving terms so partial matches still rank.
_FTS_SANITISE = re.compile(r'[^\w\s]')


def _fts_query(q: str) -> str:
    terms = [t for t in _FTS_SANITISE.sub(" ", q).split() if t]
    if not terms:
        return '""'
    # quote each term to treat as literal; OR them for recall.
    return " OR ".join(f'"{t}"' for t in terms)


class RagStore:
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
    def replace_paper(
        self, source: str, source_id: str,
        chunks: Sequence[Tuple[int, Optional[int], str]],
    ) -> int:
        """Replace all chunks for a paper. `chunks` = [(chunk_idx, page, text)].
        Returns number of chunks stored."""
        with self._conn() as c:
            # clear old (both base + fts)
            old = c.execute(
                "SELECT rowid FROM rag_chunks WHERE source=? AND source_id=?",
                (source, source_id),
            ).fetchall()
            for r in old:
                c.execute("DELETE FROM rag_fts WHERE rowid=?", (r["rowid"],))
            c.execute("DELETE FROM rag_chunks WHERE source=? AND source_id=?",
                      (source, source_id))
            n = 0
            for idx, page, text in chunks:
                cur = c.execute(
                    "INSERT INTO rag_chunks (source, source_id, chunk_idx, page, text) "
                    "VALUES (?,?,?,?,?)",
                    (source, source_id, idx, page, text),
                )
                c.execute(
                    "INSERT INTO rag_fts (rowid, text, source, source_id, chunk_idx) "
                    "VALUES (?,?,?,?,?)",
                    (cur.lastrowid, text, source, source_id, idx),
                )
                n += 1
        return n

    # ---- reads ----
    def is_indexed(self, source: str, source_id: str) -> bool:
        with self._conn() as c:
            row = c.execute(
                "SELECT 1 FROM rag_chunks WHERE source=? AND source_id=? LIMIT 1",
                (source, source_id),
            ).fetchone()
        return row is not None

    def get_chunks(self, source: str, source_id: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT chunk_idx, page, text FROM rag_chunks "
                "WHERE source=? AND source_id=? ORDER BY chunk_idx",
                (source, source_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def fulltext(self, source: str, source_id: str) -> str:
        return "\n\n".join(c["text"] for c in self.get_chunks(source, source_id))

    def search(
        self, query: str, limit: int = 8,
        source: Optional[str] = None, source_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """BM25-ranked chunk search. Optionally scope to one source/paper."""
        match = _fts_query(query)
        sql = (
            "SELECT f.source AS source, f.source_id AS source_id, "
            "f.chunk_idx AS chunk_idx, c.page AS page, c.text AS text, "
            "bm25(rag_fts) AS score "
            "FROM rag_fts f JOIN rag_chunks c "
            "  ON c.source=f.source AND c.source_id=f.source_id AND c.chunk_idx=f.chunk_idx "
            "WHERE rag_fts MATCH ?"
        )
        params: List[Any] = [match]
        if source:
            sql += " AND f.source = ?"
            params.append(source)
        if source_id:
            sql += " AND f.source_id = ?"
            params.append(source_id)
        sql += " ORDER BY score LIMIT ?"   # bm25: lower = more relevant
        params.append(limit)
        with self._conn() as c:
            rows = c.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def indexed_papers(self) -> List[Tuple[str, str, int]]:
        """(source, source_id, n_chunks) for every indexed paper."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT source, source_id, COUNT(*) AS n FROM rag_chunks "
                "GROUP BY source, source_id ORDER BY source, source_id"
            ).fetchall()
        return [(r["source"], r["source_id"], r["n"]) for r in rows]

    def stats(self) -> Dict[str, int]:
        with self._conn() as c:
            papers = c.execute(
                "SELECT COUNT(DISTINCT source || '|' || source_id) FROM rag_chunks"
            ).fetchone()[0]
            chunks = c.execute("SELECT COUNT(*) FROM rag_chunks").fetchone()[0]
        return {"papers_indexed": papers, "chunks": chunks}
