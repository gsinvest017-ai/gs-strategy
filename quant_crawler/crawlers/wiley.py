"""Wiley journal RSS crawler.

Targets peer-reviewed futures/derivatives journals via their public table-of-contents
RSS feeds. Default: Journal of Futures Markets (jc=10969934).

These RSS feeds embed PRISM and Dublin Core metadata, so authors and DOI are
typically clean and structured.
"""
from __future__ import annotations

from typing import Iterator

import feedparser
from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

DEFAULT_JOURNALS = [
    {"jc": "10969934", "name": "Journal of Futures Markets"},
    {"jc": "1467629X", "name": "Accounting and Finance"},
]
FEED_URL = "https://onlinelibrary.wiley.com/action/showFeed?type=etoc&feed=rss&jc={jc}"


class WileyCrawler(BaseCrawler):
    name = "wiley"

    def fetch(self) -> Iterator[PaperRecord]:
        journals = self.config.extras.get("journals", DEFAULT_JOURNALS)
        for j in journals:
            jc = j["jc"]
            url = FEED_URL.format(jc=jc)
            self.log.info("wiley: %s (%s)", j.get("name", jc), url)
            resp = self.session.get(url)
            if resp.status_code != 200:
                self.log.warning("wiley %s status %d", jc, resp.status_code)
                continue
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                try:
                    yield self._entry_to_record(entry, j)
                except Exception as e:
                    self.log.warning("skip wiley entry: %s", e)

    def _entry_to_record(self, entry, journal: dict) -> PaperRecord:
        title = (entry.title or "").strip()
        link = entry.link or ""
        # DOI is in entry.id like "doi:10.1002/fut.22458" or in prism:doi
        doi = ""
        for k in ("prism_doi", "id"):
            v = getattr(entry, k, "") or ""
            if v.lower().startswith("doi:"):
                doi = v[4:]
                break
            if v.startswith("10."):
                doi = v
                break

        authors = []
        # feedparser exposes Dublin Core authors as entry.authors
        for a in getattr(entry, "authors", []):
            n = a.get("name") if isinstance(a, dict) else getattr(a, "name", None)
            if n:
                authors.append(n.strip())
        if not authors:
            dc_creator = getattr(entry, "author", "")
            if dc_creator:
                authors = [s.strip() for s in dc_creator.split(",") if s.strip()]

        abstract = ""
        summary_html = getattr(entry, "summary", "") or ""
        if summary_html:
            abstract = BeautifulSoup(summary_html, "lxml").get_text(" ", strip=True)

        sid = doi or link or title[:80]

        return PaperRecord(
            source="wiley",
            source_id=sid,
            title=title,
            authors=authors,
            abstract=abstract,
            published=getattr(entry, "published", None) or getattr(entry, "prism_coverdate", None),
            url=link,
            pdf_url="",
            categories=[f"wiley:{journal.get('jc')}", journal.get("name", "")],
            doi=doi,
            raw_extra={"journal": journal.get("name")},
        )
