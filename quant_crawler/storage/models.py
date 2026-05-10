"""Schema for paper records."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class PaperRecord:
    source: str  # e.g. "arxiv", "nber"
    source_id: str  # provider-specific stable id
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    published: Optional[str] = None  # ISO date
    updated: Optional[str] = None  # ISO date
    url: str = ""  # canonical landing page
    pdf_url: str = ""
    categories: list[str] = field(default_factory=list)
    keywords_hit: list[str] = field(default_factory=list)
    doi: str = ""
    raw_extra: dict = field(default_factory=dict)
    fetched_at: str = ""

    def __post_init__(self) -> None:
        if not self.fetched_at:
            self.fetched_at = (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            )

    def as_row(self) -> dict:
        d = asdict(self)
        # SQLite-friendly: lists/dicts -> JSON string at write time (handled by storage layer)
        return d
