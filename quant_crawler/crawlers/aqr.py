"""AQR Capital Insights / Research index crawler.

AQR's research index page is server-rendered; we extract the article cards
(title + path) and treat each entry as a paper record. Abstracts are not
included on the listing page; we don't follow individual articles to keep
load light. Users can read the URL.
"""
from __future__ import annotations

import re
from typing import Iterator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

INDEX_URL = "https://www.aqr.com/Insights/Research"
BASE = "https://www.aqr.com"

# AQR groups research by type via path segment after /Research/
KIND_RE = re.compile(r"/Insights/Research/([^/]+)/", re.IGNORECASE)


class AQRCrawler(BaseCrawler):
    name = "aqr"
    bypass_relevance = True  # AQR research is publisher-curated; keep it all

    def fetch(self) -> Iterator[PaperRecord]:
        # AQR's CDN sometimes 403s the default UA; patch it for this source.
        self.session.session.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124"
        )
        resp = self.session.get(INDEX_URL)
        if resp.status_code != 200:
            self.log.error("aqr returned %d", resp.status_code)
            return
        soup = BeautifulSoup(resp.text, "lxml")
        seen: set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/Insights/Research/"):
                continue
            # Skip top-level category landing pages — only deep links to articles
            depth = href.rstrip("/").count("/")
            if depth < 4:
                continue
            title = a.get_text(" ", strip=True)
            if not title or len(title) < 6:
                continue
            if href in seen:
                continue
            seen.add(href)

            kind = ""
            m = KIND_RE.search(href)
            if m:
                kind = m.group(1).replace("-", " ")

            yield PaperRecord(
                source="aqr",
                source_id=href.rstrip("/"),
                title=title,
                authors=[],
                abstract="",
                published=None,
                url=urljoin(BASE, href),
                pdf_url="",
                categories=[f"aqr:{kind}"] if kind else ["aqr"],
                raw_extra={"path": href},
            )
