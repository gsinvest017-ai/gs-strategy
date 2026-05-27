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
