"""Text-processing helpers."""
from __future__ import annotations

import hashlib
import re
import unicodedata

from quant_crawler.config import RELEVANCE_REGEX

_WS = re.compile(r"\s+")


def normalize_whitespace(s: str) -> str:
    return _WS.sub(" ", s).strip()


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    return normalize_whitespace(s)


def is_relevant(*texts: str) -> bool:
    """Returns True if any of the given strings hits a relevance keyword."""
    for t in texts:
        if t and RELEVANCE_REGEX.search(t):
            return True
    return False


def relevance_hits(*texts: str) -> list[str]:
    """Returns the matched keywords (deduped, lowercased)."""
    found: set[str] = set()
    for t in texts:
        if not t:
            continue
        for m in RELEVANCE_REGEX.finditer(t):
            found.add(m.group(0).lower())
    return sorted(found)


def stable_hash(*parts: str) -> str:
    """Deterministic short hash for cross-source dedup."""
    h = hashlib.sha1()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]
