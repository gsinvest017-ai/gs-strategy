"""Tests for the RAG store + chunking (no PDF needed for store tests)."""
from __future__ import annotations

from pathlib import Path

import pytest

from quant_crawler.rag.store import RagStore, _fts_query
from quant_crawler.rag.ingest import _chunk_page


@pytest.fixture
def store(tmp_path: Path) -> RagStore:
    return RagStore(tmp_path / "papers.db")


def test_chunk_page_short_text():
    assert _chunk_page("hello world") == ["hello world"]
    assert _chunk_page("") == []


def test_chunk_page_overlap_and_size():
    text = " ".join(f"w{i}" for i in range(800))   # long
    chunks = _chunk_page(text, size=200, overlap=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 + 1 for c in chunks)
    # consecutive chunks overlap (share some tail/head content)
    joined = " ".join(chunks)
    assert "w0" in joined and "w799" in joined


def test_fts_query_sanitises_operators():
    # FTS5 operators / punctuation must not blow up the MATCH
    q = _fts_query("cubic momentum: f(x) = a*x - b*x^3")
    assert '"cubic"' in q and '"momentum"' in q
    assert "(" not in q and "*" not in q


def test_replace_and_get_chunks(store: RagStore):
    n = store.replace_paper("arxiv", "1", [
        (0, 1, "cubic momentum signal definition"),
        (1, 1, "the critical threshold is sqrt(a/(3b))"),
        (2, 2, "volatility targeting overlay"),
    ])
    assert n == 3
    chunks = store.get_chunks("arxiv", "1")
    assert len(chunks) == 3
    assert chunks[1]["page"] == 1
    assert "threshold" in chunks[1]["text"]
    assert store.is_indexed("arxiv", "1")
    assert not store.is_indexed("arxiv", "2")


def test_fulltext_concatenates(store: RagStore):
    store.replace_paper("arxiv", "1", [(0, 1, "alpha"), (1, 1, "beta")])
    assert store.fulltext("arxiv", "1") == "alpha\n\nbeta"


def test_search_bm25_ranks_relevant_first(store: RagStore):
    store.replace_paper("arxiv", "1", [
        (0, 1, "the cubic momentum critical threshold formula is sqrt of a over three b"),
        (1, 1, "unrelated discussion about portfolio diversification"),
    ])
    store.replace_paper("wiley", "9", [
        (0, 1, "time series momentum twelve minus one lookback"),
    ])
    hits = store.search("cubic momentum threshold formula", limit=5)
    assert hits, "expected at least one hit"
    assert hits[0]["source"] == "arxiv" and hits[0]["chunk_idx"] == 0


def test_search_scoped_to_paper(store: RagStore):
    store.replace_paper("arxiv", "1", [(0, 1, "momentum signal")])
    store.replace_paper("arxiv", "2", [(0, 1, "momentum factor")])
    hits = store.search("momentum", source="arxiv", source_id="2")
    assert all(h["source_id"] == "2" for h in hits)


def test_replace_paper_is_idempotent(store: RagStore):
    store.replace_paper("arxiv", "1", [(0, 1, "old text alpha")])
    store.replace_paper("arxiv", "1", [(0, 1, "new text beta"), (1, 1, "gamma")])
    chunks = store.get_chunks("arxiv", "1")
    assert len(chunks) == 2
    assert "old" not in store.fulltext("arxiv", "1")
    # FTS index updated too: searching old term returns nothing
    assert store.search("alpha") == []
    assert store.search("beta")


def test_indexed_papers_and_stats(store: RagStore):
    store.replace_paper("arxiv", "1", [(0, 1, "a"), (1, 1, "b")])
    store.replace_paper("wiley", "9", [(0, 1, "c")])
    assert ("arxiv", "1", 2) in store.indexed_papers()
    s = store.stats()
    assert s["papers_indexed"] == 2 and s["chunks"] == 3


# ---------- retrieve.py (enriched, kind-aware) ----------

import sqlite3  # noqa: E402

from quant_crawler.rag import retrieve  # noqa: E402


def _seed_papers(db: Path):
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS papers (
            source TEXT, source_id TEXT, title TEXT, authors TEXT, abstract TEXT,
            published TEXT, updated TEXT, url TEXT, pdf_url TEXT, categories TEXT,
            keywords_hit TEXT, doi TEXT, raw_extra TEXT, fetched_at TEXT,
            PRIMARY KEY (source, source_id)
        );
        """
    )
    conn.executemany(
        "INSERT INTO papers (source, source_id, title, abstract, url) VALUES (?,?,?,?,?)",
        [
            ("arxiv", "s1", "A trend-following trading strategy",
             "backtest of a trend-following trading rule", "us1"),
            ("arxiv", "f1", "The value premium factor",
             "cross-sectional value factor and risk premia", "uf1"),
        ],
    )
    conn.commit()
    conn.close()


@pytest.fixture
def db_with_papers(tmp_path: Path) -> Path:
    db = tmp_path / "papers.db"
    _seed_papers(db)
    st = RagStore(db)
    st.replace_paper("arxiv", "s1", [(0, 1, "trend following entry and exit signal")])
    st.replace_paper("arxiv", "f1", [(0, 1, "the value premium and book-to-market factor")])
    return db


def test_search_chunks_enriches_title_and_kind(db_with_papers: Path):
    hits = retrieve.search_chunks("value premium factor", db_path=db_with_papers)
    assert hits
    top = hits[0]
    assert top["source_id"] == "f1"
    assert top["kind"] == "factor"
    assert top["title"] == "The value premium factor"


def test_search_chunks_kind_filter(db_with_papers: Path):
    # 'signal' appears in the strategy paper; kind=factor must exclude it
    strat = retrieve.search_chunks("signal trend", kind="strategy", db_path=db_with_papers)
    assert all(h["kind"] == "strategy" for h in strat)
    assert any(h["source_id"] == "s1" for h in strat)
    fac = retrieve.search_chunks("signal trend", kind="factor", db_path=db_with_papers)
    assert all(h["kind"] == "factor" for h in fac)


def test_paper_context_targeted_query(db_with_papers: Path):
    ctx = retrieve.paper_context("arxiv", "f1", query="book-to-market", db_path=db_with_papers)
    assert ctx["indexed"] is True
    assert ctx["kind"] == "factor"
    assert ctx["chunks"] and "book-to-market" in ctx["chunks"][0]["text"]


def test_paper_context_fulltext(db_with_papers: Path):
    ctx = retrieve.paper_context("arxiv", "s1", db_path=db_with_papers)
    assert "trend following" in ctx["fulltext"]
    assert ctx["n_chunks"] == 1


def test_paper_context_not_indexed(db_with_papers: Path):
    ctx = retrieve.paper_context("arxiv", "missing", db_path=db_with_papers)
    assert ctx["indexed"] is False
    assert ctx["chunks"] == []


def test_list_indexed_kind_filter(db_with_papers: Path):
    fac = retrieve.list_indexed(kind="factor", db_path=db_with_papers)
    assert {p["source_id"] for p in fac} == {"f1"}
