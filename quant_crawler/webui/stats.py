"""Data layer for the management UI.

Pure functions that read ``data/papers.db`` and the ``strategies/`` filesystem
and return JSON-serialisable dicts. No HTTP here so everything is unit-testable
in isolation.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date as _date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from quant_crawler.config import DB_PATH, PDF_DIR, PROJECT_ROOT
from quant_crawler.pdf_fetch import has_local_pdf, pdf_filename

# gs-strategy bundle roots scanned for the strategy inventory.
STRATEGIES_ROOT = PROJECT_ROOT / "strategies"
GENERATED_ROOT = STRATEGIES_ROOT / "_generated"


def _zipline_strategies_dir() -> Path:
    """Where exported bundles land in gs-zipline-tej. Overridable for tests."""
    env = os.environ.get("ZIPLINE_TEJ_STRATEGIES_DIR")
    if env:
        return Path(env).expanduser()
    return Path("~/gs-zipline-tej/strategies").expanduser()


def _today_iso() -> str:
    return _date.today().isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------------------------------
# Papers + crawl runs
# --------------------------------------------------------------------------

def papers_summary(db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Total paper count + per-source breakdown."""
    if not Path(db_path).is_file():
        return {"total": 0, "by_source": []}
    conn = _connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        rows = conn.execute(
            "SELECT source, COUNT(*) AS n FROM papers GROUP BY source ORDER BY n DESC"
        ).fetchall()
        by_source = [{"source": r["source"], "count": r["n"]} for r in rows]
    finally:
        conn.close()
    return {"total": total, "by_source": by_source}


def runs_on(date: Optional[str] = None, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """crawl_runs whose started_at falls on `date` (ISO, default today)."""
    day = date or _today_iso()
    if not Path(db_path).is_file():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT source, started_at, finished_at, items_seen, items_kept, error
            FROM crawl_runs
            WHERE substr(started_at, 1, 10) = ?
            ORDER BY started_at DESC
            """,
            (day,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "source": r["source"],
            "started_at": r["started_at"],
            "finished_at": r["finished_at"],
            "items_seen": r["items_seen"],
            "items_kept": r["items_kept"],
            "error": r["error"],
            "ok": r["error"] is None and r["finished_at"] is not None,
        }
        for r in rows
    ]


def new_papers_on(
    date: Optional[str] = None, limit: int = 100, db_path: Path = DB_PATH
) -> List[Dict[str, Any]]:
    """Papers fetched on `date` (default today). If no rows, callers may fall
    back to latest_papers()."""
    day = date or _today_iso()
    if not Path(db_path).is_file():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT source, source_id, title, published, url, pdf_url
            FROM papers
            WHERE substr(fetched_at, 1, 10) = ?
            ORDER BY published DESC NULLS LAST, fetched_at DESC
            LIMIT ?
            """,
            (day, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_paper_row(r) for r in rows]


def latest_papers(limit: int = 20, db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    if not Path(db_path).is_file():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT source, source_id, title, published, url, pdf_url, fetched_at
            FROM papers
            ORDER BY fetched_at DESC, published DESC NULLS LAST
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [_paper_row(r) for r in rows]


def _paper_row(r: sqlite3.Row) -> Dict[str, Any]:
    """Normalise a papers row + attach the local-PDF filename if downloaded."""
    d = dict(r)
    local = pdf_filename(d["source"], d["source_id"]) if has_local_pdf(
        d["source"], d["source_id"]
    ) else None
    d["pdf_local"] = local          # filename under PDF_DIR, or None
    return d


def list_papers(
    date: Optional[str] = None,
    limit: int = 100,
    pdf: Optional[str] = None,
    db_path: Path = DB_PATH,
) -> List[Dict[str, Any]]:
    """Unified paper listing with an optional PDF filter.

    pdf=None  -> no filter (papers on `date` if given, else most-recent)
    pdf="any"   -> only papers with a local OR remote PDF
    pdf="local" -> only papers with a downloaded local PDF

    When a pdf filter is active the scan spans ALL papers (date is ignored) so
    a downloaded PDF surfaces no matter when its paper was fetched.
    """
    if not Path(db_path).is_file():
        return []
    apply_filter = pdf in ("any", "local")
    conn = _connect(db_path)
    try:
        if date and not apply_filter:
            rows = conn.execute(
                """
                SELECT source, source_id, title, published, url, pdf_url
                FROM papers WHERE substr(fetched_at, 1, 10) = ?
                ORDER BY published DESC NULLS LAST, fetched_at DESC
                """,
                (date,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT source, source_id, title, published, url, pdf_url
                FROM papers
                ORDER BY fetched_at DESC, published DESC NULLS LAST
                """
            ).fetchall()
    finally:
        conn.close()

    papers = [_paper_row(r) for r in rows]
    if pdf == "local":
        papers = [p for p in papers if p["pdf_local"]]
    elif pdf == "any":
        papers = [p for p in papers if p["pdf_local"] or p["pdf_url"]]
    return papers[:limit]


def pdfs_downloaded(pdf_dir: Path = PDF_DIR) -> int:
    """Count .pdf files actually present in the local PDF dir."""
    p = Path(pdf_dir)
    if not p.is_dir():
        return 0
    return sum(1 for f in p.glob("*.pdf") if f.is_file() and f.stat().st_size > 0)


def crawl_dates(db_path: Path = DB_PATH, limit: int = 30) -> List[str]:
    """Distinct dates on which crawl_runs exist (newest first)."""
    if not Path(db_path).is_file():
        return []
    conn = _connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT substr(started_at, 1, 10) AS d
            FROM crawl_runs ORDER BY d DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [r["d"] for r in rows]


# --------------------------------------------------------------------------
# Strategy inventory + export status
# --------------------------------------------------------------------------

def _read_manifest(bundle: Path) -> Optional[Dict[str, Any]]:
    mp = bundle / "manifest.yaml"
    if not mp.is_file():
        return None
    try:
        data = yaml.safe_load(mp.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def _bundle_record(bundle: Path, origin: str, export_dir: Path) -> Dict[str, Any]:
    manifest = _read_manifest(bundle) or {}
    source = manifest.get("source") or {}
    bundle_id = manifest.get("id", bundle.name)
    exported = (export_dir / bundle_id / "manifest.yaml").is_file()
    # Spec markdown: the bundle README is the human-readable strategy spec.
    spec_files = [f for f in ("README.md", "manifest.yaml", "strategy.py")
                  if (bundle / f).is_file()]
    return {
        "id": bundle_id,
        "name": manifest.get("name", bundle_id),
        "origin": origin,                       # "manual" | "generated"
        "template": source.get("template"),     # only for generated
        "source_kind": source.get("kind"),
        "tags": manifest.get("tags", []),
        "requires_review": bool(manifest.get("requires_review", False)),
        "bundle": manifest.get("bundle"),
        "asset_class": manifest.get("asset_class"),
        "exported": exported,
        "path": str(bundle),
        "has_spec_md": (bundle / "README.md").is_file(),
        "spec_files": spec_files,               # served via /files/strategy/<id>/<f>
    }


def strategy_inventory(
    strategies_root: Path = STRATEGIES_ROOT,
    export_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """All gs-strategy bundles (hand-authored + generated) with export status.

    Hand-authored bundles live directly under strategies/ (dirs NOT starting
    with `_`); generated bundles live under strategies/_generated/.
    """
    export_dir = export_dir or _zipline_strategies_dir()
    records: List[Dict[str, Any]] = []

    if strategies_root.is_dir():
        for p in sorted(strategies_root.iterdir()):
            if not p.is_dir() or p.name.startswith("_"):
                continue
            if (p / "manifest.yaml").is_file():
                records.append(_bundle_record(p, "manual", export_dir))

    gen_root = strategies_root / "_generated"
    if gen_root.is_dir():
        for p in sorted(gen_root.iterdir()):
            if p.is_dir() and (p / "manifest.yaml").is_file():
                records.append(_bundle_record(p, "generated", export_dir))

    return records


def bundle_dir_for(bundle_id: str, strategies_root: Path = STRATEGIES_ROOT) -> Optional[Path]:
    """Resolve a strategy id to its on-disk bundle dir (manual or generated)."""
    for candidate in (strategies_root / bundle_id,
                      strategies_root / "_generated" / bundle_id):
        if (candidate / "manifest.yaml").is_file():
            return candidate
    return None


def summary(
    db_path: Path = DB_PATH,
    strategies_root: Path = STRATEGIES_ROOT,
    export_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Top-level dashboard summary card payload."""
    papers = papers_summary(db_path)
    inv = strategy_inventory(strategies_root, export_dir)
    exported = [s for s in inv if s["exported"]]
    manual = [s for s in inv if s["origin"] == "manual"]
    generated = [s for s in inv if s["origin"] == "generated"]
    today = _today_iso()
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today": today,
        "papers_total": papers["total"],
        "papers_by_source": papers["by_source"],
        "pdfs_downloaded": pdfs_downloaded(),
        "runs_today": len(runs_on(today, db_path)),
        "strategies_total": len(inv),
        "strategies_manual": len(manual),
        "strategies_generated": len(generated),
        "strategies_exported": len(exported),
        "strategies_pending": len(inv) - len(exported),
        "export_dir": str(export_dir or _zipline_strategies_dir()),
    }
