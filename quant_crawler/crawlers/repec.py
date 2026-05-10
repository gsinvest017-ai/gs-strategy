"""RePEc NEP (New Economic Papers) crawler.

NEP publishes curated weekly reports per topic. We use:
    nep-fmk  Financial Markets
    nep-rmg  Risk Management
    nep-mst  Market Microstructure

Each report URL: https://nep.repec.org/<topic>/latest

Open-access — no anti-bot — perfect SSRN replacement.
"""
from __future__ import annotations

import re
from typing import Iterator

from bs4 import BeautifulSoup

from quant_crawler.crawlers.base import BaseCrawler
from quant_crawler.storage.models import PaperRecord

REPORT_URL = "https://nep.repec.org/{topic}/latest"
# RePEc IDs appear in URLs in two forms:
#   .../RePEc:pra:mprapa:128875?ref=...      (path)
#   .../redir.cgi?u=RePEc:foo:bar             (query param)
REPEC_ID_RE = re.compile(r"RePEc:[A-Za-z0-9_\-]+(?::[A-Za-z0-9._\-]+){1,3}")
DEFAULT_TOPICS = ["nep-fmk", "nep-rmg", "nep-mst", "nep-inv"]


class RepecCrawler(BaseCrawler):
    name = "repec"

    def fetch(self) -> Iterator[PaperRecord]:
        topics: list[str] = self.config.extras.get("topics", DEFAULT_TOPICS)
        for topic in topics:
            url = REPORT_URL.format(topic=topic)
            self.log.info("repec NEP report: %s", url)
            resp = self.session.get(url)
            if resp.status_code != 200:
                self.log.warning("repec %s status %d", topic, resp.status_code)
                continue
            yield from self._parse_report(resp.text, topic)

    def _parse_report(self, html: str, topic: str) -> Iterator[PaperRecord]:
        soup = BeautifulSoup(html, "lxml")

        # Each paper is a <div id="pN"> followed by <table class="basit"> with metadata rows.
        for div in soup.select("div[id^=p]"):
            div_id = div.get("id", "")
            if not re.match(r"^p\d+$", div_id):
                continue
            # title anchor inside the div
            a = div.find("a")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href", "")
            # Detail table: next <table class="basit"> sibling
            table = div.find_next("table", class_="basit")
            meta = self._parse_basit_table(table) if table else {}

            repec_id = self._extract_repec_id(href, "")
            if not repec_id:
                # try inside metadata "URL:" link
                repec_id = self._extract_repec_id(meta.get("url_href", ""), meta.get("url", ""))
            if not repec_id:
                continue

            jel = meta.get("jel", "")
            cats = [f"nep:{topic}"]
            if jel:
                cats.extend(f"jel:{j}" for j in jel.split() if j and len(j) <= 5)

            yield PaperRecord(
                source="repec",
                source_id=repec_id,
                title=title,
                authors=self._split_authors(meta.get("by", "")),
                abstract=meta.get("abstract", ""),
                published=self._normalize_date(meta.get("date", "")),
                url=href or meta.get("url_href", "") or f"https://econpapers.repec.org/{repec_id}",
                pdf_url="",
                categories=cats,
                raw_extra={"keywords": meta.get("keywords", ""), "topic": topic},
            )

    @staticmethod
    def _parse_basit_table(table) -> dict:
        out: dict = {}
        if not table:
            return out
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            label = cells[0].get_text(" ", strip=True).rstrip(":").lower()
            value_cell = cells[1]
            value = value_cell.get_text(" ", strip=True)
            if label == "by":
                out["by"] = value
            elif label == "abstract":
                out["abstract"] = value
            elif label == "keywords":
                out["keywords"] = value
            elif label == "jel":
                out["jel"] = value
            elif label == "date":
                out["date"] = value
            elif label == "url":
                out["url"] = value
                a = value_cell.find("a")
                if a and a.get("href"):
                    out["url_href"] = a["href"]
        return out

    @staticmethod
    def _extract_after(blob: str, markers: list[str]) -> str:
        for m in markers:
            i = blob.find(m)
            if i >= 0:
                return blob[i + len(m):].split("Abstract:")[0].strip(" :; ")
        return ""

    @staticmethod
    def _extract_between(blob: str, start: str, ends: list[str]) -> str:
        i = blob.find(start)
        if i < 0:
            return ""
        rest = blob[i + len(start):]
        cut = len(rest)
        for e in ends:
            j = rest.find(e)
            if 0 <= j < cut:
                cut = j
        return rest[:cut].strip(" :; ")

    @staticmethod
    def _split_authors(s: str) -> list[str]:
        if not s:
            return []
        # NEP usually formats authors as "Last, First; Last, First"
        return [a.strip() for a in re.split(r";|\sand\s", s) if a.strip()]

    @staticmethod
    def _extract_repec_id(url: str, blob: str) -> str:
        for s in (url, blob):
            if not s:
                continue
            m = REPEC_ID_RE.search(s)
            if m:
                return m.group(0)
        return ""

    @staticmethod
    def _normalize_date(s: str) -> str | None:
        if not s:
            return None
        s = s.replace("–", "-").replace("—", "-").strip()
        m = re.search(r"\d{4}-\d{2}-\d{2}", s)
        if m:
            return m.group(0)
        m = re.search(r"\d{4}-\d{2}", s)
        if m:
            return m.group(0) + "-01"
        m = re.search(r"\d{4}", s)
        return m.group(0) + "-01-01" if m else None
