"""Tests for quant_crawler.pdf_fetch (filename rules + fetch orchestration)."""
from __future__ import annotations

from pathlib import Path

import pytest

from quant_crawler import pdf_fetch
from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord


def test_pdf_filename_rules() -> None:
    assert pdf_fetch.pdf_filename("arxiv", "2605.01300") == "arxiv_2605_01300.pdf"
    assert pdf_fetch.pdf_filename("wiley", "10.1002/fut.70093") == "wiley_10_1002_fut_70093.pdf"
    # long source_id is truncated (excluding extension)
    long = pdf_fetch.pdf_filename("arxiv", "x" * 200)
    assert len(long) <= 84  # 80 slug + ".pdf"
    assert long.endswith(".pdf")


def test_local_pdf_path(tmp_path: Path) -> None:
    p = pdf_fetch.local_pdf_path("arxiv", "2605.01300", pdf_dir=tmp_path)
    assert p == tmp_path / "arxiv_2605_01300.pdf"


def test_has_local_pdf(tmp_path: Path) -> None:
    assert not pdf_fetch.has_local_pdf("arxiv", "1", pdf_dir=tmp_path)
    f = tmp_path / "arxiv_1.pdf"
    f.write_bytes(b"%PDF-1.4 dummy")
    assert pdf_fetch.has_local_pdf("arxiv", "1", pdf_dir=tmp_path)
    # zero-byte file does NOT count
    (tmp_path / "arxiv_2.pdf").write_bytes(b"")
    assert not pdf_fetch.has_local_pdf("arxiv", "2", pdf_dir=tmp_path)


class _FakeSession:
    """Stand-in for RateLimitedSession.download — writes a dummy PDF."""
    def __init__(self, fail_urls=()):
        self.fail_urls = set(fail_urls)
        self.calls = []

    def download(self, url, dest, chunk_size=1 << 15):
        self.calls.append(url)
        if url in self.fail_urls:
            return None
        Path(dest).write_bytes(b"%PDF-1.4 fake content")
        return 21


def _seed(storage: Storage) -> None:
    def rec(source, sid, pdf_url):
        return PaperRecord(
            source=source, source_id=sid, title=f"t-{sid}",
            authors=[], abstract="", published="2026-01-01", updated="",
            url="", pdf_url=pdf_url, categories=[], keywords_hit=[],
            doi="", raw_extra={}, fetched_at="2026-05-27T00:00:00Z",
        )
    storage.upsert(rec("arxiv", "1", "https://arxiv.org/pdf/1"))
    storage.upsert(rec("arxiv", "2", "https://arxiv.org/pdf/2"))
    storage.upsert(rec("nber", "w3", "https://nber.org/w3.pdf"))
    storage.upsert(rec("aqr", "noPdf", ""))   # no pdf_url -> excluded


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    s = Storage(tmp_path / "papers.db")
    _seed(s)
    return s


def test_papers_with_pdf_excludes_empty(storage: Storage) -> None:
    rows = storage.papers_with_pdf()
    ids = {(r[0], r[1]) for r in rows}
    assert ("aqr", "noPdf") not in ids
    assert len(rows) == 3


def test_papers_with_pdf_source_filter(storage: Storage) -> None:
    rows = storage.papers_with_pdf(source="arxiv")
    assert {r[1] for r in rows} == {"1", "2"}


def test_fetch_pending_downloads(tmp_path: Path, storage: Storage) -> None:
    pdf_dir = tmp_path / "pdfs"
    sess = _FakeSession()
    summary = pdf_fetch.fetch_pending(storage, pdf_dir=pdf_dir, session=sess)
    assert summary["targets"] == 3
    assert summary["downloaded"] == 3
    assert summary["failed"] == 0
    assert (pdf_dir / "arxiv_1.pdf").is_file()
    assert (pdf_dir / "nber_w3.pdf").is_file()


def test_fetch_pending_skips_existing(tmp_path: Path, storage: Storage) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    (pdf_dir / "arxiv_1.pdf").write_bytes(b"%PDF existing")
    sess = _FakeSession()
    summary = pdf_fetch.fetch_pending(storage, pdf_dir=pdf_dir, session=sess)
    assert summary["skipped"] == 1
    assert summary["downloaded"] == 2
    assert "https://arxiv.org/pdf/1" not in sess.calls


def test_fetch_pending_limit(tmp_path: Path, storage: Storage) -> None:
    sess = _FakeSession()
    summary = pdf_fetch.fetch_pending(storage, limit=1, pdf_dir=tmp_path / "pdfs", session=sess)
    assert summary["downloaded"] == 1


def test_fetch_pending_handles_failure(tmp_path: Path, storage: Storage) -> None:
    pdf_dir = tmp_path / "pdfs"
    sess = _FakeSession(fail_urls={"https://arxiv.org/pdf/2"})
    summary = pdf_fetch.fetch_pending(storage, pdf_dir=pdf_dir, session=sess)
    assert summary["failed"] == 1
    assert summary["downloaded"] == 2
