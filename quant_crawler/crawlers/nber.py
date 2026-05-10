"""NBER working-paper crawler.

NBER publishes a global RSS of new working papers. We parse it, then for relevant
entries optionally hit the per-paper landing page to grab abstract & DOI when the
RSS summary is too sparse.
"""
from __future__ import annotations

import re
from typing import Iterator

import feedparser
from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

RSS_URL = "https://www.nber.org/rss/new.xml"
ABS_RE = re.compile(r"working_papers/(w\d+)", re.IGNORECASE)


class NBERCrawler(BaseCrawler):
    name = "nber"

    def fetch(self) -> Iterator[PaperRecord]:
        resp = self.session.get(RSS_URL)
        if resp.status_code != 200:
            self.log.error("NBER RSS returned %d", resp.status_code)
            return
        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            try:
                yield self._entry_to_record(entry)
            except Exception as e:
                self.log.warning("skip nber entry: %s", e)

    def _entry_to_record(self, entry) -> PaperRecord:
        link = entry.link or ""
        m = ABS_RE.search(link)
        wid = m.group(1).lower() if m else (entry.id or link)
        title = (entry.title or "").strip()
        # NBER RSS provides a description with author + abstract snippet
        desc = BeautifulSoup(getattr(entry, "summary", ""), "lxml").get_text(" ", strip=True)
        authors: list[str] = []
        abstract = desc
        # Common NBER format: "by Alice Author, Bob Author - 2026-05-09 - <abstract>"
        if " - " in desc:
            parts = desc.split(" - ", 2)
            head = parts[0]
            if head.lower().startswith("by "):
                authors = [a.strip() for a in head[3:].split(",") if a.strip()]
            if len(parts) >= 3:
                abstract = parts[2]

        return PaperRecord(
            source="nber",
            source_id=wid,
            title=title,
            authors=authors,
            abstract=abstract,
            published=getattr(entry, "published", None),
            url=link,
            pdf_url=f"https://www.nber.org/papers/{wid}.pdf" if wid.startswith("w") else "",
            categories=[],
            raw_extra={"rss_summary": desc[:500]},
        )
