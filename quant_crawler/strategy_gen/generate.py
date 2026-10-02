"""Generator: papers.db row -> dashboard-spec v1 bundle on disk.

Usage as a library:
    from quant_crawler.strategy_gen import generate_bundle
    path = generate_bundle(paper_dict, out_root=Path("strategies/_generated"))

Usage as a CLI (see ``scripts/daily_refresh.sh`` for the wrapping shell):
    python -m quant_crawler.strategy_gen.generate --since 2026-05-25 \\
        --out-root strategies/_generated

The generator is idempotent on `paper_slug`: re-running on the same paper
preserves any human edits in `manifest.yaml` (matching the behaviour of
``scripts/config_to_manifest.py``).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from quant_crawler.utils.logging import get_logger

from .classify import ClassificationResult, classify_paper
from .taxonomy import TAG_VOCABULARY, flat_tags

log = get_logger("strategy_gen")

PKG_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PKG_DIR / "templates"
REPO_ROOT = PKG_DIR.parent.parent
DEFAULT_DB = REPO_ROOT / "data" / "papers.db"
DEFAULT_OUT_ROOT = REPO_ROOT / "strategies" / "_generated"
CANONICAL_FUTURES_SETUP = REPO_ROOT / "strategies" / "_common" / "futures_setup.py"

# Default backtest window for generated bundles. Bounded so the dashboard
# doesn't try to load missing data. Override via `manifest.params` later.
DEFAULT_START = "2020-01-01"
DEFAULT_END = "2026-04-30"
DEFAULT_CAPITAL = 5_000_000

# Template -> targeted RAG query used to auto-retrieve the paper's signal
# definition into the generated README. Augmented with the matched keywords.
_RAG_QUERY_BY_TEMPLATE = {
    "momentum": "momentum signal formula lookback skip ranking",
    "mean_reversion": "mean reversion oscillator threshold signal formula",
    "buy_and_hold": "strategy definition parameters position sizing",
}
_RAG_CONTEXT_CHUNKS = 3
_RAG_CHUNK_PREVIEW_CHARS = 700

_SLUG_SANITISE_RE = re.compile(r"[^a-z0-9]+")

# Roots that are stock-index futures; everything else is a single-stock future.
_INDEX_FUTURE_ROOTS = frozenset({"TX", "MTX", "TXF", "MXF", "TE", "TF", "GTF", "XIF"})

# Fixed execution-context tags every generated bundle carries.
_FIXED_BUNDLE_TAGS = ("paper", "auto-generated", "needs-review", "taiwan", "futures")


def _instrument_tag(root: str) -> str:
    return "index-future" if root.upper() in _INDEX_FUTURE_ROOTS else "stock-future"


def assemble_tags(
    paper: Mapping[str, Any], classification: "ClassificationResult"
) -> List[str]:
    """Build the searchable manifest.tags list for a generated bundle.

    Order: fixed execution tags -> instrument -> taxonomy (family/signal/
    direction) -> the template's own tags. De-duped, order-preserving.
    """
    root = str(classification.default_params.get("root_symbol", "TX"))
    ordered = (
        list(_FIXED_BUNDLE_TAGS)
        + [_instrument_tag(root)]
        + flat_tags(paper)
        + list(classification.tags)
    )
    seen: Dict[str, None] = {}
    return [t for t in ordered if not (t in seen or seen.update({t: None}))]


def paper_slug(source: str, source_id: str) -> str:
    """Stable, filesystem-safe slug for a paper.

    Example: source='arxiv', source_id='2605.01300' -> 'arxiv_2605_01300'
    Rules:
      - join with `_`
      - lowercase
      - replace any non-alnum run with `_`
      - strip leading/trailing `_`
      - truncate to <=64 chars
      - ensure first char is alnum (prefix `s_` if not)
    """
    base = f"{source}_{source_id}".lower()
    slug = _SLUG_SANITISE_RE.sub("_", base).strip("_")
    if not slug:
        slug = "unknown"
    if not slug[0].isalnum():
        slug = "s_" + slug
    return slug[:64]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )


def _normalise_paper(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert sqlite3.Row / dict / PaperRecord into a plain dict + decode
    JSON-serialised list fields (authors, categories, keywords_hit)."""
    paper = dict(row)
    for k in ("authors", "categories", "keywords_hit"):
        v = paper.get(k)
        if isinstance(v, str):
            try:
                paper[k] = json.loads(v)
            except (TypeError, ValueError):
                paper[k] = [s.strip() for s in v.split(",") if s.strip()]
    return paper


def _description(paper: Mapping[str, Any], result_template: str,
                 matched_keywords: Iterable[str]) -> str:
    keywords = list(matched_keywords) or ["(none — fallback bundle)"]
    abstract = (paper.get("abstract") or "").strip().replace("\n", " ")
    if len(abstract) > 400:
        abstract = abstract[:397] + "..."
    return (
        f"Auto-generated {result_template} skeleton seeded from "
        f"{paper.get('source')}:{paper.get('source_id')}. "
        f"Matched keywords: {', '.join(keywords)}. "
        f"Abstract: {abstract or '(no abstract)'} "
        f"REQUIRES HUMAN REVIEW before deployment."
    )


def _rag_context_section(
    paper: Mapping[str, Any],
    classification: "ClassificationResult",
    rag_db_path: Optional[Path] = None,
) -> str:
    """Build the README's "RAG source context" section.

    When the paper is indexed, auto-retrieves the top passages for the
    template's signal and embeds them inline so a reviewer (or Claude) sees the
    original formula text without an extra MCP round-trip. Always falls back to
    the ingest hint when retrieval is unavailable — generation never fails on a
    RAG problem.
    """
    source = str(paper["source"])
    source_id = str(paper["source_id"])
    query = " ".join(
        [_RAG_QUERY_BY_TEMPLATE.get(classification.template, "signal formula definition")]
        + list(classification.matched_keywords)[:5]
    )
    try:
        from quant_crawler.config import DB_PATH
        from quant_crawler.rag.retrieve import paper_context

        ctx = paper_context(
            source, source_id, query=query,
            max_chunks=_RAG_CONTEXT_CHUNKS, db_path=rag_db_path or DB_PATH,
        )
    except Exception:
        ctx = {"indexed": False, "chunks": []}

    if not ctx.get("indexed"):
        return (
            "## RAG source context\n\n"
            "Paper text NOT yet indexed. Run `quant-crawl fetch-pdfs` then\n"
            "`quant-crawl rag-ingest` to enable formula retrieval via MCP.\n\n"
        )

    lines = [
        "## RAG source context (use to extract the correct formula)\n",
        f"This paper's full text is indexed. Below are the top passages "
        f"auto-retrieved\nfor the **{classification.template}** signal — verify "
        f"the formula against them.\nFor a targeted lookup, query the "
        f"`gs-strategy-rag` MCP server:\n",
        "```",
        f'get_paper_context(source="{source}", source_id="{source_id}",',
        '                  query="<the signal/factor formula you need>")',
        "```",
        f'or `get_paper_fulltext("{source}", "{source_id}")`.\n',
    ]
    chunks = ctx.get("chunks") or []
    if chunks:
        lines.append("### Auto-retrieved passages\n")
        for ch in chunks:
            text = " ".join((ch.get("text") or "").split())
            if len(text) > _RAG_CHUNK_PREVIEW_CHARS:
                text = text[:_RAG_CHUNK_PREVIEW_CHARS] + " …"
            page = ch.get("page")
            loc = f"p.{page}" if page is not None else f"chunk {ch.get('chunk_idx')}"
            score = ch.get("score")
            head = f"- **{loc}**" + (f" (BM25 {score})" if score is not None else "") + ":"
            lines.append(head)
            lines.append(f"  > {text}\n")
    return "\n".join(lines) + "\n"


def generate_bundle(
    paper: Mapping[str, Any],
    out_root: Path = DEFAULT_OUT_ROOT,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    capital_base: int = DEFAULT_CAPITAL,
    dry_run: bool = False,
    rag_db_path: Optional[Path] = None,
) -> Path:
    """Render a skeleton bundle for one paper.

    Returns the bundle directory path (whether or not files were written).
    """
    paper = _normalise_paper(paper)
    if not paper.get("source") or not paper.get("source_id"):
        raise ValueError("paper dict requires source + source_id")

    classification = classify_paper(paper)
    slug = paper_slug(paper["source"], paper["source_id"])
    bundle_dir = out_root / slug

    env = _env()
    desc = _description(paper, classification.template, classification.matched_keywords)

    # We pass the description as `description_indented` because jinja's
    # ``| indent`` would otherwise indent the first line of a multi-line
    # block too. Single line is fine here.
    params_yaml = yaml.safe_dump(
        dict(classification.default_params), sort_keys=False, allow_unicode=True
    ).rstrip()
    paper_published = (
        paper.get("published") or paper.get("updated") or date.today().isoformat()
    )
    paper_authors = paper.get("authors") or []
    if isinstance(paper_authors, str):
        paper_authors = [paper_authors]
    paper_categories = paper.get("categories") or []
    if isinstance(paper_categories, str):
        paper_categories = [paper_categories]

    manifest_ctx = {
        "bundle_id": slug,
        "name": paper.get("title") or slug,
        "description_indented": desc,
        "start": start,
        "end": end,
        "capital_base": capital_base,
        "params_yaml": params_yaml,
        "tags": assemble_tags(paper, classification),
        "symbols": [classification.default_params.get("root_symbol", "TX")],
        "template": classification.template,
        "matched_keywords": list(classification.matched_keywords),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "paper_source": paper.get("source"),
        "paper_source_id": str(paper.get("source_id")),
        "paper_title": paper.get("title") or "(no title)",
        "paper_authors": paper_authors,
        "paper_published": paper_published,
        "paper_url": paper.get("url") or "",
        "paper_doi": paper.get("doi"),
        "paper_categories": paper_categories,
    }
    strategy_ctx = {
        "paper_title": manifest_ctx["paper_title"],
        "paper_url": manifest_ctx["paper_url"],
    }

    manifest_yaml = env.get_template("manifest.yaml.j2").render(**manifest_ctx)
    strategy_py = env.get_template(
        f"strategy_{classification.template}.py.j2"
    ).render(**strategy_ctx)

    if dry_run:
        return bundle_dir

    bundle_dir.mkdir(parents=True, exist_ok=True)

    # Idempotency: preserve manually-edited manifest fields when one already
    # exists.
    manifest_path = bundle_dir / "manifest.yaml"
    existing = None
    if manifest_path.is_file():
        try:
            existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            # 既有 manifest 讀不了時**不能**讓整個重生失敗，否則就成了死結：
            # 一份寫壞的 manifest 會擋住那個唯一能把它修好的動作，於是損壞永久化。
            # 實際踩過：repec 的 mojibake 讓 14 份 manifest 含 U+0080 控制字元，
            # YAML 拒收，重生時在這一行炸掉——修復腳本因此一個都修不了。
            #
            # 讀不了就當成「沒有既有檔案」整份重寫。這會丟掉手改過的欄位，所以
            # 一定要出聲；但保留一份無法解析的檔案並不會保住那些手改內容，
            # 只是把它們鎖在一個沒有東西讀得了的檔案裡。
            log.warning(
                "既有 manifest 無法解析，將整份重寫（手改欄位會遺失）：%s — %s",
                manifest_path, exc,
            )
            existing = None
    if existing is not None:
        new = yaml.safe_load(manifest_yaml) or {}
        # User edits to top-level scalars win; we only refresh
        # generated-at + matched_keywords + paper provenance block.
        merged = dict(new)
        for k, v in existing.items():
            if k not in {"source"}:
                merged[k] = v
        merged_source = dict(new["source"])
        if isinstance(existing.get("source"), dict):
            # keep the ORIGINAL generated_at so it doesn't churn each run;
            # add an updated_at instead.
            if "generated_at" in existing["source"]:
                merged_source["updated_at"] = new["source"]["generated_at"]
                merged_source["generated_at"] = existing["source"]["generated_at"]
        merged["source"] = merged_source
        manifest_yaml = yaml.safe_dump(
            merged, sort_keys=False, allow_unicode=True, default_flow_style=False
        )

    manifest_path.write_text(manifest_yaml, encoding="utf-8")
    (bundle_dir / "strategy.py").write_text(strategy_py, encoding="utf-8")

    # futures_setup.py — sibling helper, copy from canonical _common location
    if CANONICAL_FUTURES_SETUP.is_file():
        shutil.copyfile(
            CANONICAL_FUTURES_SETUP, bundle_dir / "futures_setup.py"
        )

    # Auto-retrieve the paper's signal passages from the RAG store (when
    # indexed) and embed them inline, so the reviewer/Claude sees the original
    # formula text without a separate MCP round-trip.
    rag_section = _rag_context_section(paper, classification, rag_db_path)

    (bundle_dir / "README.md").write_text(
        f"# {manifest_ctx['name']}\n\n"
        f"Auto-generated bundle from `{paper['source']}:{paper['source_id']}`.\n\n"
        f"Template: **{classification.template}**\n\n"
        f"Matched keywords: `{', '.join(classification.matched_keywords) or '(none)'}`\n\n"
        f"Paper URL: {manifest_ctx['paper_url']}\n\n"
        + rag_section +
        "## Review checklist\n\n"
        "1. Pull the paper's real formula from the RAG MCP server (above).\n"
        "2. Replace `_generate_signal()` / `_compute_oscillator()` body with it.\n"
        "3. Verify default params match the paper (lookback, thresholds,\n"
        "   instruments, etc.).\n"
        "4. Confirm cost / slippage / position-sizing assumptions.\n"
        "5. Set `manifest.requires_review: false` only after sign-off.\n",
        encoding="utf-8",
    )

    return bundle_dir


def select_recent_papers(
    db_path: Path = DEFAULT_DB,
    since: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Pull papers whose ``fetched_at`` >= since (ISO date). Newest first."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sql = "SELECT * FROM papers"
    args: List[Any] = []
    if since:
        sql += " WHERE fetched_at >= ?"
        args.append(since)
    sql += " ORDER BY fetched_at DESC, published DESC"
    if limit:
        sql += " LIMIT ?"
        args.append(limit)
    cur = conn.execute(sql, args)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    p.add_argument(
        "--since",
        help="ISO date; only papers fetched_at >= this date are processed",
    )
    p.add_argument(
        "--limit", type=int,
        help="cap the number of papers processed in one run",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="print what would be generated without writing files")
    p.add_argument("--list-tags", action="store_true",
                   help="print the full strategy-tag vocabulary and exit")
    args = p.parse_args(argv)

    if args.list_tags:
        for tag in sorted(TAG_VOCABULARY):
            print(tag)
        return 0

    papers = select_recent_papers(args.db, since=args.since, limit=args.limit)
    if not papers:
        print(f"[strategy_gen] no papers selected (since={args.since!r})")
        return 0

    written = 0
    for paper in papers:
        try:
            path = generate_bundle(
                paper, out_root=args.out_root, dry_run=args.dry_run
            )
            tag = "DRY" if args.dry_run else "OUT"
            print(f"  [{tag}] {paper['source']}:{paper['source_id']:30s} -> {path}")
            written += 1
        except Exception as exc:
            print(
                f"  [ERR] {paper.get('source')}:{paper.get('source_id')} "
                f"-> {exc!r}",
                file=sys.stderr,
            )
    print(
        f"[strategy_gen] processed {len(papers)} papers, "
        f"emitted {written} bundles (dry_run={args.dry_run})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
