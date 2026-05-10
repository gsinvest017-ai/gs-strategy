"""Federal Reserve FEDS Notes / FEDS working-paper crawler.

Uses the public RSS feed at https://www.federalreserve.gov/feeds/feds.xml
"""
from __future__ import annotations

import re
from typing import Iterator

import feedparser
from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

FEED_URL = "https://www.federalreserve.gov/feeds/feds.xml"
FEDS_ID_RE = re.compile(r"FEDS\s+(\d{4}-\d{3,4})", re.IGNORECASE)


class FedFedsCrawler(BaseCrawler):
    name = "fed_feds"

    def fetch(self) -> Iterator[PaperRecord]:
        resp = self.session.get(FEED_URL)
        if resp.status_code != 200:
            self.log.error("Fed FEDS RSS returned %d", resp.status_code)
            return
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            try:
                yield self._entry_to_record(entry)
            except Exception as e:
                self.log.warning("skip fed entry: %s", e)

    def _entry_to_record(self, entry) -> PaperRecord:
        title = (entry.title or "").strip()
        link = entry.link or ""
        desc_html = getattr(entry, "summary", "") or ""
        desc = BeautifulSoup(desc_html, "lxml").get_text(" ", strip=True)
        m = FEDS_ID_RE.search(desc) or FEDS_ID_RE.search(entry.id or "")
        feds_id = m.group(1) if m else (entry.id or link)
        return PaperRecord(
            source="fed_feds",
            source_id=feds_id,
            title=title,
            authors=[],  # the Fed RSS embeds authors in the description; left empty for now
            abstract=desc,
            published=getattr(entry, "published", None),
            url=link,
            pdf_url="",
            categories=["fed:FEDS"],
            doi="",
            raw_extra={},
        )
