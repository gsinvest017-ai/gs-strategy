"""SSRN crawler — Top Papers RSS feeds for futures-relevant journals.

SSRN exposes per-journal "top recent papers" RSS at:
    https://papers.ssrn.com/sol3/JELJOUR_Results.cfm?form_name=journalbrowse&journal_id=<id>&action=feed

We use the following journals (configurable in SOURCES['ssrn'].extras['journal_ids']):
    203978  Derivatives eJournal
    203956  Futures & Other Derivatives Modeling: Pricing, Hedging & Trading

If feeds are blocked or empty, we fall back to scraping the journal's recent papers
HTML page. SSRN is sensitive — we keep min_delay >= 4s and never download PDFs.
"""
from __future__ import annotations

import re
from typing import Iterator
from urllib.parse import urlparse, parse_qs

import feedparser
from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

FEED_URL = (
    "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm"
    "?form_name=journalbrowse&journal_id={jid}&action=feed"
)
HTML_URL = (
    "https://papers.ssrn.com/sol3/JELJOUR_Results.cfm"
    "?form_name=journalbrowse&journal_id={jid}"
)
ABS_ID_RE = re.compile(r"abstract_id=(\d+)")


class SSRNCrawler(BaseCrawler):
    name = "ssrn"

    def fetch(self) -> Iterator[PaperRecord]:
        journal_ids: list[str] = self.config.extras.get("journal_ids", [])
        if not journal_ids:
            self.log.warning("ssrn: no journal_ids configured")
            return

        # Probe once: if Cloudflare's anti-bot is up, every subsequent request will
        # 403, so fail fast instead of burning the rate budget.
        probe = self.session.get(FEED_URL.format(jid=journal_ids[0]))
        if probe.status_code == 403 or "Just a moment" in probe.text[:500]:
            self.log.warning(
                "ssrn behind Cloudflare anti-bot challenge — skipping (status=%d). "
                "To enable, run with a headless browser (Playwright) or an API key.",
                probe.status_code,
            )
            return

        for jid in journal_ids:
            yielded = 0
            try:
                yielded = yield from self._fetch_feed(jid)
            except Exception as e:
                self.log.warning("ssrn feed %s failed: %s", jid, e)
                yielded = 0
            if yielded == 0:
                # fallback to HTML
                try:
                    yield from self._fetch_html(jid)
                except Exception as e:
                    self.log.warning("ssrn html %s failed: %s", jid, e)

    def _fetch_feed(self, jid: str):
        url = FEED_URL.format(jid=jid)
        self.log.info("ssrn feed: %s", url)
        resp = self.session.get(url)
        if resp.status_code != 200 or not resp.text.strip():
            self.log.warning("ssrn feed %s status %d", jid, resp.status_code)
            return 0
        feed = feedparser.parse(resp.text)
        count = 0
        for entry in feed.entries:
            try:
                rec = self._entry_to_record(entry, jid)
                if rec is None:
                    continue
                count += 1
                yield rec
            except Exception as e:
                self.log.warning("skip ssrn entry: %s", e)
        return count

    def _entry_to_record(self, entry, jid: str):
        link = entry.link or entry.id or ""
        m = ABS_ID_RE.search(link)
        if not m:
            qs = parse_qs(urlparse(link).query)
            aid = qs.get("abstract_id", [""])[0]
        else:
            aid = m.group(1)
        if not aid:
            return None
        title = (entry.title or "").strip()
        desc = BeautifulSoup(getattr(entry, "summary", ""), "lxml").get_text(" ", strip=True)
        return PaperRecord(
            source="ssrn",
            source_id=aid,
            title=title,
            authors=[],  # SSRN feed sometimes omits structured authors
            abstract=desc,
            published=getattr(entry, "published", None),
            url=f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={aid}",
            pdf_url="",
            categories=[f"ssrn_journal:{jid}"],
            raw_extra={"journal_id": jid},
        )

    def _fetch_html(self, jid: str) -> Iterator[PaperRecord]:
        url = HTML_URL.format(jid=jid)
        self.log.info("ssrn html fallback: %s", url)
        resp = self.session.get(url)
        if resp.status_code != 200:
            self.log.warning("ssrn html %s status %d", jid, resp.status_code)
            return
        soup = BeautifulSoup(resp.text, "lxml")
        for a in soup.select("a[href*='abstract_id=']"):
            href = a.get("href", "")
            m = ABS_ID_RE.search(href)
            if not m:
                continue
            aid = m.group(1)
            title = a.get_text(strip=True)
            if not title:
                continue
            yield PaperRecord(
                source="ssrn",
                source_id=aid,
                title=title,
                authors=[],
                abstract="",
                published=None,
                url=f"https://papers.ssrn.com/sol3/papers.cfm?abstract_id={aid}",
                categories=[f"ssrn_journal:{jid}"],
                raw_extra={"journal_id": jid, "via": "html"},
            )
