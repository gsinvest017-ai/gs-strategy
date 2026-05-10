"""Abstract base class every source crawler implements."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable

from quant_crawler.config import SourceConfig
from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord
from quant_crawler.utils.http import RateLimitedSession
from quant_crawler.utils.logging import get_logger
from quant_crawler.utils.text import is_relevant, relevance_hits


class BaseCrawler(ABC):
    name: str = "base"
    # If True, skip the keyword relevance filter — useful for sources like AQR
    # whose entire research output is in-scope (curated by the publisher).
    bypass_relevance: bool = False

    def __init__(self, config: SourceConfig, storage: Storage) -> None:
        self.config = config
        self.storage = storage
        self.log = get_logger(self.name)
        self.session = RateLimitedSession(min_delay=config.min_delay)

    # ---- subclasses implement this ----
    @abstractmethod
    def fetch(self) -> Iterable[PaperRecord]:
        """Yields raw PaperRecord objects (relevance filtering done here in run())."""

    # ---- shared run loop ----
    def run(self) -> dict:
        started = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        run_id = self.storage.start_run(self.name, started)
        seen, kept = 0, 0
        error = None
        try:
            for rec in self.fetch():
                seen += 1
                hits = relevance_hits(rec.title, rec.abstract, " ".join(rec.categories))
                if not self.bypass_relevance:
                    if not hits and not is_relevant(rec.title, rec.abstract):
                        continue
                rec.keywords_hit = hits
                self.storage.upsert(rec)
                kept += 1
                if kept >= self.config.max_items_per_run:
                    self.log.info("hit max_items_per_run=%d", self.config.max_items_per_run)
                    break
            self.log.info("done — seen=%d kept=%d", seen, kept)
        except Exception as e:  # last-resort: never let one source kill the orchestrator
            error = f"{type(e).__name__}: {e}"
            self.log.exception("crawler %s failed: %s", self.name, error)
        finally:
            finished = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            self.storage.finish_run(run_id, finished, seen, kept, error)

        return {
            "source": self.name,
            "started": started,
            "items_seen": seen,
            "items_kept": kept,
            "error": error,
        }
