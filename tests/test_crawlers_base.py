"""Unit tests for quant_crawler.crawlers.base.BaseCrawler (P0 / U-015..U-018).

Uses a fake subclass with a controllable fetch() iterator + tmp Storage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pytest

from quant_crawler.config import SourceConfig
from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord


def _rec(sid: str, title: str = "Cross-sectional momentum in futures",
         abstract: str = "trading rule based on momentum signals") -> PaperRecord:
    """Default rec is relevance-hitting (momentum) so it survives the filter."""
    return PaperRecord(
        source="fake", source_id=sid, title=title, authors=["A"],
        abstract=abstract, published="2026-01-01", url="https://x/" + sid,
        pdf_url="", categories=["q-fin.TR"], keywords_hit=[],
        doi="", raw_extra={}, fetched_at="2026-05-29T00:00:00Z",
    )


class _FakeCrawler(BaseCrawler):
    name = "fake"
    bypass_relevance = True   # default for tests: keep what fetch yields

    def __init__(self, storage: Storage, items: List, *,
                 bypass_relevance: bool = True,
                 max_items: int = 100, min_delay: float = 0.0,
                 raise_before_first: Exception | None = None):
        # set per-instance overrides BEFORE super().__init__ (which builds session)
        type(self).bypass_relevance = bypass_relevance
        cfg = SourceConfig(name="fake", enabled=True, min_delay=min_delay,
                           max_items_per_run=max_items)
        self._items = items
        self._raise_before_first = raise_before_first
        super().__init__(cfg, storage)

    def fetch(self) -> Iterable[PaperRecord]:
        if self._raise_before_first:
            raise self._raise_before_first
        for it in self._items:
            if isinstance(it, Exception):
                raise it
            yield it


@pytest.fixture
def store(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "papers.db")


# --------------------------------------------------------------------------
# U-015  happy: N papers fetched → all stored, counters correct
# --------------------------------------------------------------------------

def test_U_015_happy_three_papers_all_stored(store: Storage):
    items = [_rec("1"), _rec("2"), _rec("3")]
    c = _FakeCrawler(store, items)
    summary = c.run()
    assert summary["items_seen"] == 3 and summary["items_kept"] == 3
    assert summary["error"] is None
    assert store.count(source="fake") == 3


# --------------------------------------------------------------------------
# U-016  mid-stream exception: items before raise persist, error recorded
# --------------------------------------------------------------------------

def test_U_016_mid_stream_exception_is_isolated(store: Storage):
    items = [_rec("1"), _rec("2"), RuntimeError("boom"), _rec("3")]
    c = _FakeCrawler(store, items)
    summary = c.run()
    # 2 items kept BEFORE the raise; the 3rd never reached
    assert summary["items_kept"] == 2
    assert "RuntimeError" in (summary["error"] or "")
    assert store.count(source="fake") == 2
    # crawl_runs got finished_at + error
    import sqlite3
    conn = sqlite3.connect(store.path); conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM crawl_runs WHERE source='fake'").fetchone()
    assert row["error"] and "RuntimeError" in row["error"]
    assert row["finished_at"] is not None
    conn.close()


# --------------------------------------------------------------------------
# U-017  fetch raises before yielding: 0 stored, error captured, no crash
# --------------------------------------------------------------------------

def test_U_017_fetch_raises_immediately(store: Storage):
    c = _FakeCrawler(store, [], raise_before_first=ValueError("network down"))
    summary = c.run()
    assert summary["items_kept"] == 0
    assert summary["items_seen"] == 0
    assert "ValueError" in (summary["error"] or "")
    assert store.count(source="fake") == 0


# --------------------------------------------------------------------------
# U-018  dedup: same (source, source_id) twice → 1 row, second is update
# --------------------------------------------------------------------------

def test_U_018_dedup_on_source_source_id(store: Storage):
    items = [_rec("1", title="first"), _rec("1", title="updated")]
    c = _FakeCrawler(store, items)
    summary = c.run()
    assert summary["items_seen"] == 2 and summary["items_kept"] == 2
    # but DB has only 1 row (upsert: second write updated the first)
    rows = store.latest(limit=10, source="fake")
    assert len(rows) == 1
    assert rows[0].title == "updated"


# --------------------------------------------------------------------------
# Extras: relevance filter + max_items_per_run cap
# --------------------------------------------------------------------------

def test_base_relevance_filter_drops_unrelated(store: Storage):
    """With bypass_relevance=False, papers with no keyword hits are dropped."""
    items = [
        _rec("rel", title="Cross-sectional momentum factor"),  # keeps
        _rec("noise", title="Unrelated cooking blog post",
             abstract="how to bake cookies"),                   # drops
    ]
    c = _FakeCrawler(store, items, bypass_relevance=False)
    summary = c.run()
    assert summary["items_seen"] == 2
    assert summary["items_kept"] == 1
    assert store.count(source="fake") == 1


def test_base_cap_at_max_items_per_run(store: Storage):
    items = [_rec(str(i)) for i in range(20)]
    c = _FakeCrawler(store, items, max_items=5)
    summary = c.run()
    # cap kicks in after kept reaches 5
    assert summary["items_kept"] == 5
    assert store.count(source="fake") == 5
