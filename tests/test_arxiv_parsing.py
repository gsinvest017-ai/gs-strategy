"""Offline test: feed the arXiv crawler a fixture and check filtering."""
from pathlib import Path
from unittest.mock import MagicMock

import dataclasses

from quant_crawler.config import SOURCES
from quant_crawler.crawlers.arxiv import ArxivCrawler
from quant_crawler.storage.db import Storage

FIXTURE = Path(__file__).parent / "fixtures" / "arxiv_sample.xml"


def test_arxiv_parses_and_filters(tmp_db):
    cfg = dataclasses.replace(SOURCES["arxiv"], min_delay=0.0, max_items_per_run=10)
    storage = Storage(tmp_db)
    c = ArxivCrawler(cfg, storage)

    # Patch the session.get to return our fixture text
    fake = MagicMock()
    fake.status_code = 200
    fake.text = FIXTURE.read_text(encoding="utf-8")
    c.session.get = MagicMock(return_value=fake)

    result = c.run()
    assert result["items_seen"] == 2
    # The unrelated education paper should be filtered out.
    assert result["items_kept"] == 1

    rows = storage.latest(5, "arxiv")
    assert len(rows) == 1
    assert "Trend Following" in rows[0].title
    assert "futures" in [k.lower() for k in rows[0].keywords_hit] or any(
        "futures" in k for k in rows[0].keywords_hit
    )
    assert rows[0].source_id == "2605.12345"  # version stripped
