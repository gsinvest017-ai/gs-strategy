"""High-level RAG retrieval: chunk search/fetch enriched with paper metadata.

Shared by the CLI (`quant-crawl rag-search`) and the MCP server, so Claude and
humans get the same enriched view (title + strategy/factor kind alongside the
matched text).
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from quant_crawler import paper_class
from quant_crawler.config import DB_PATH
from quant_crawler.rag.store import RagStore
from quant_crawler.storage.labels import LabelStore


def _paper_meta(db_path: Path) -> Dict[tuple, Dict[str, Any]]:
    """(source, source_id) -> {title, url, kind} for kind-aware enrichment."""
    if not Path(db_path).is_file():
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT source, source_id, title, url, abstract, keywords_hit, categories "
            "FROM papers"
        ).fetchall()
    finally:
        conn.close()
    labels = LabelStore(db_path).all_labels()
    out: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        d = dict(r)
        key = (d["source"], d["source_id"])
        override = labels.get(key, {}).get("kind_override")
        kind = override or paper_class.classify_kind(d).kind
        out[key] = {"title": d.get("title"), "url": d.get("url"), "kind": kind}
    return out


def search_chunks(
    query: str, limit: int = 8, kind: Optional[str] = None,
    source: Optional[str] = None, source_id: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """BM25 chunk search enriched with paper title + kind. `kind` filters
    results to strategy/factor papers."""
    store = RagStore(db_path)
    # over-fetch when kind-filtering since the filter is applied post-hoc
    raw = store.search(query, limit=limit * 4 if kind else limit,
                       source=source, source_id=source_id)
    meta = _paper_meta(db_path)
    out: List[Dict[str, Any]] = []
    for h in raw:
        m = meta.get((h["source"], h["source_id"]), {})
        if kind and m.get("kind") != kind:
            continue
        out.append({
            "source": h["source"],
            "source_id": h["source_id"],
            "title": m.get("title"),
            "kind": m.get("kind"),
            "url": m.get("url"),
            "page": h["page"],
            "chunk_idx": h["chunk_idx"],
            "score": round(h["score"], 3),
            "text": h["text"],
        })
        if len(out) >= limit:
            break
    return out


def paper_context(
    source: str, source_id: str, query: Optional[str] = None,
    max_chunks: int = 6, db_path: Path = DB_PATH,
) -> Dict[str, Any]:
    """Context for a KNOWN paper. With `query`, returns the top matching chunks
    within that paper (targeted formula lookup); without, returns full text."""
    store = RagStore(db_path)
    meta = _paper_meta(db_path).get((source, source_id), {})
    if not store.is_indexed(source, source_id):
        return {"source": source, "source_id": source_id, "indexed": False,
                **meta, "chunks": [], "fulltext": ""}
    if query:
        hits = store.search(query, limit=max_chunks,
                            source=source, source_id=source_id)
        chunks = [{"page": h["page"], "chunk_idx": h["chunk_idx"],
                   "score": round(h["score"], 3), "text": h["text"]} for h in hits]
        return {"source": source, "source_id": source_id, "indexed": True,
                **meta, "query": query, "chunks": chunks}
    return {"source": source, "source_id": source_id, "indexed": True,
            **meta, "fulltext": store.fulltext(source, source_id),
            "n_chunks": len(store.get_chunks(source, source_id))}


def list_indexed(kind: Optional[str] = None,
                 db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    store = RagStore(db_path)
    meta = _paper_meta(db_path)
    out: List[Dict[str, Any]] = []
    for src, sid, n in store.indexed_papers():
        m = meta.get((src, sid), {})
        if kind and m.get("kind") != kind:
            continue
        out.append({"source": src, "source_id": sid, "n_chunks": n,
                    "title": m.get("title"), "kind": m.get("kind")})
    return out
