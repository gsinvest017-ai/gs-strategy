"""arXiv q-fin crawler — uses the public Atom API.

API doc: https://arxiv.org/help/api
Endpoint:  http://export.arxiv.org/api/query
Rate-limit: arXiv asks for >= 3s between requests. Configured via SourceConfig.min_delay.
"""
from __future__ import annotations

from typing import Iterator
from urllib.parse import urlencode

import feedparser

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

API_URL = "http://export.arxiv.org/api/query"


class ArxivCrawler(BaseCrawler):
    name = "arxiv"

    def fetch(self) -> Iterator[PaperRecord]:
        cats: list[str] = self.config.extras.get("categories", ["q-fin.TR"])
        # arXiv search expression: cat:q-fin.TR OR cat:q-fin.PM ...
        search_query = " OR ".join(f"cat:{c}" for c in cats)
        params = {
            "search_query": search_query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "start": 0,
            "max_results": min(self.config.max_items_per_run * 2, 100),
        }
        url = f"{API_URL}?{urlencode(params)}"
        self.log.info("arxiv query: %s", url)
        resp = self.session.get(url)
        if resp.status_code != 200:
            self.log.error("arxiv returned %d", resp.status_code)
            return

        feed = feedparser.parse(resp.text)
        if feed.bozo:
            self.log.warning("arxiv feed parse warning: %s", feed.bozo_exception)

        for entry in feed.entries:
            try:
                yield self._entry_to_record(entry)
            except Exception as e:
                self.log.warning("skip arxiv entry: %s", e)

    def _entry_to_record(self, entry) -> PaperRecord:
        # entry.id is like 'http://arxiv.org/abs/2401.12345v2'
        arxiv_id = entry.id.rsplit("/", 1)[-1]
        # strip version suffix for stable id (we still keep full id in raw_extra)
        bare_id = arxiv_id.split("v")[0] if "v" in arxiv_id else arxiv_id

        authors = [a.name for a in getattr(entry, "authors", []) if hasattr(a, "name")]
        cats = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]

        pdf_url = ""
        for link in getattr(entry, "links", []):
            if getattr(link, "type", "") == "application/pdf":
                pdf_url = link.href
                break

        return PaperRecord(
            source="arxiv",
            source_id=bare_id,
            title=(entry.title or "").replace("\n", " ").strip(),
            authors=authors,
            abstract=(entry.summary or "").replace("\n", " ").strip(),
            published=getattr(entry, "published", None),
            updated=getattr(entry, "updated", None),
            url=entry.id,
            pdf_url=pdf_url,
            categories=cats,
            doi=(getattr(entry, "arxiv_doi", "") or ""),
            raw_extra={"version_id": arxiv_id},
        )
