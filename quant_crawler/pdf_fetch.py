"""Download crawled papers' PDFs to data/pdfs/ for local archival + linking.

The crawler stores only a remote ``pdf_url`` by default (``download_pdfs=False``).
This module fetches those PDFs to a deterministic local path so the management
UI can hyperlink the on-disk file.

Filename rule (shared with webui.stats so paths agree):
    pdf_filename("arxiv", "2605.01300") -> "arxiv_2605_01300.pdf"

CLI (wired in quant_crawler.cli):
    quant-crawl fetch-pdfs [-n N] [-s SOURCE]
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from quant_crawler.config import PDF_DIR
from quant_crawler.storage.db import Storage
from quant_crawler.utils.http import RateLimitedSession
from quant_crawler.utils.logging import get_logger

log = get_logger("pdf_fetch")

_SANITISE_RE = re.compile(r"[^a-z0-9]+")


def pdf_filename(source: str, source_id: str) -> str:
    """Deterministic, filesystem-safe PDF filename for a paper."""
    base = f"{source}_{source_id}".lower()
    slug = _SANITISE_RE.sub("_", base).strip("_")[:80] or "unknown"
    return f"{slug}.pdf"


def local_pdf_path(source: str, source_id: str, pdf_dir: Path = PDF_DIR) -> Path:
    return Path(pdf_dir) / pdf_filename(source, source_id)


def has_local_pdf(source: str, source_id: str, pdf_dir: Path = PDF_DIR) -> bool:
    p = local_pdf_path(source, source_id, pdf_dir)
    return p.is_file() and p.stat().st_size > 0


def fetch_pending(
    storage: Optional[Storage] = None,
    limit: Optional[int] = None,
    source: Optional[str] = None,
    pdf_dir: Path = PDF_DIR,
    session: Optional[RateLimitedSession] = None,
) -> Dict[str, Any]:
    """Download PDFs for papers that have a pdf_url but no local file yet.

    Returns a summary dict: {targets, downloaded, skipped, failed, files}.
    """
    storage = storage or Storage()
    session = session or RateLimitedSession(min_delay=3.0)
    pdf_dir = Path(pdf_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    targets = storage.papers_with_pdf(source=source)
    downloaded = skipped = failed = 0
    files: list[str] = []
    for src, sid, pdf_url in targets:
        if limit is not None and downloaded >= limit:
            break
        dest = local_pdf_path(src, sid, pdf_dir)
        if dest.is_file() and dest.stat().st_size > 0:
            skipped += 1
            continue
        try:
            n = session.download(pdf_url, dest)
        except Exception as exc:  # network etc. — isolate per-paper
            log.warning("pdf download error %s:%s -> %r", src, sid, exc)
            n = None
        if n and n > 0:
            downloaded += 1
            files.append(dest.name)
            log.info("downloaded %s:%s -> %s (%d bytes)", src, sid, dest.name, n)
        else:
            failed += 1
            # remove empty/partial file if created
            if dest.is_file() and dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
    return {
        "targets": len(targets),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
        "files": files,
    }
