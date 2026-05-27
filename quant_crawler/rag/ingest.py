"""Extract text from downloaded PDFs, chunk it, and store in the RAG store."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from quant_crawler.config import PDF_DIR
from quant_crawler.pdf_fetch import local_pdf_path
from quant_crawler.rag.store import RagStore
from quant_crawler.storage.db import Storage
from quant_crawler.utils.logging import get_logger

log = get_logger("rag.ingest")

CHUNK_CHARS = 1000
CHUNK_OVERLAP = 150


def _chunk_page(text: str, size: int = CHUNK_CHARS,
                overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split one page's text into overlapping char windows on whitespace."""
    text = " ".join(text.split())   # normalise whitespace
    if not text:
        return []
    if len(text) <= size:
        return [text]
    out: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        # try not to cut mid-word
        if end < len(text):
            sp = text.rfind(" ", start + size - overlap, end)
            if sp > start:
                end = sp
        out.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in out if c]


def extract_chunks(pdf_path: Path) -> List[Tuple[int, Optional[int], str]]:
    """Return [(chunk_idx, page_number, text)] for a PDF (page-aware)."""
    import pypdf  # local import so the rest of the package has no hard dep

    reader = pypdf.PdfReader(str(pdf_path))
    chunks: List[Tuple[int, Optional[int], str]] = []
    idx = 0
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - malformed page
            log.warning("extract_text failed on %s p%d: %r", pdf_path.name, page_no, exc)
            text = ""
        for piece in _chunk_page(text):
            chunks.append((idx, page_no, piece))
            idx += 1
    return chunks


def ingest_pdf(source: str, source_id: str, pdf_path: Path,
               store: Optional[RagStore] = None) -> int:
    store = store or RagStore()
    chunks = extract_chunks(pdf_path)
    if not chunks:
        log.warning("no extractable text in %s", pdf_path)
        return 0
    n = store.replace_paper(source, source_id, chunks)
    log.info("indexed %s:%s -> %d chunks from %s", source, source_id, n, pdf_path.name)
    return n


def ingest_all(
    storage: Optional[Storage] = None,
    store: Optional[RagStore] = None,
    limit: Optional[int] = None,
    source: Optional[str] = None,
    reindex: bool = False,
    pdf_dir: Path = PDF_DIR,
) -> Dict[str, Any]:
    """Ingest every downloaded PDF whose paper isn't yet indexed (unless
    reindex=True). Returns a summary dict."""
    storage = storage or Storage()
    store = store or RagStore()
    targets = storage.papers_with_pdf(source=source)
    indexed = skipped = no_file = failed = 0
    total_chunks = 0
    for src, sid, _pdf_url in targets:
        if limit is not None and indexed >= limit:
            break
        path = local_pdf_path(src, sid, pdf_dir)
        if not path.is_file():
            no_file += 1
            continue
        if not reindex and store.is_indexed(src, sid):
            skipped += 1
            continue
        try:
            n = ingest_pdf(src, sid, path, store=store)
        except Exception as exc:
            log.warning("ingest failed %s:%s -> %r", src, sid, exc)
            failed += 1
            continue
        if n > 0:
            indexed += 1
            total_chunks += n
        else:
            failed += 1
    return {
        "targets": len(targets),
        "indexed": indexed,
        "skipped": skipped,
        "no_pdf_file": no_file,
        "failed": failed,
        "chunks": total_chunks,
    }
