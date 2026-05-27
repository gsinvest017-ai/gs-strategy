"""CLI entry point: `quant-crawl <subcommand>`."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from quant_crawler.config import SOURCES
from quant_crawler.orchestrator import REGISTRY, append_experiment_log, run_all
from quant_crawler.storage.db import Storage
from quant_crawler.utils.logging import get_logger

log = get_logger("cli")


def cmd_run(args: argparse.Namespace) -> int:
    only = args.source if args.source else None
    storage = Storage()
    results = run_all(storage, only=only, include_disabled=args.include_disabled)
    if args.log_run:
        append_experiment_log(results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    storage = Storage()
    items = storage.latest(args.limit, source=args.source)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "source": p.source,
                        "id": p.source_id,
                        "title": p.title,
                        "authors": p.authors,
                        "published": p.published,
                        "url": p.url,
                        "categories": p.categories,
                        "keywords_hit": p.keywords_hit,
                    }
                    for p in items
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    for p in items:
        pub = (p.published or "?")[:10]
        cats = ",".join(p.categories[:3])
        print(f"[{p.source}] {pub}  {p.title[:90]}  ({cats})")
        print(f"    {p.url}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    storage = Storage()
    items = storage.search(args.query, limit=args.limit)
    for p in items:
        pub = (p.published or "?")[:10]
        print(f"[{p.source}] {pub}  {p.title[:90]}")
        print(f"    {p.url}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    storage = Storage()
    print(f"total: {storage.count()}")
    for src, n in storage.stats_by_source():
        print(f"  {src:10s} {n}")
    return 0


def cmd_fetch_pdfs(args: argparse.Namespace) -> int:
    from quant_crawler.pdf_fetch import fetch_pending

    storage = Storage()
    summary = fetch_pending(storage, limit=args.limit, source=args.source)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_rag_ingest(args: argparse.Namespace) -> int:
    from quant_crawler.rag.ingest import ingest_all

    summary = ingest_all(limit=args.limit, source=args.source, reindex=args.reindex)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_sources(args: argparse.Namespace) -> int:
    for name in REGISTRY:
        cfg = SOURCES.get(name)
        if cfg is None:
            continue
        flag = "ENABLED " if cfg.enabled else "disabled"
        print(
            f"{flag}  {name:10s}  delay={cfg.min_delay}s  max={cfg.max_items_per_run}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quant-crawl", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pr = sub.add_parser("run", help="Run crawlers")
    pr.add_argument("--source", "-s", action="append", help="limit to source(s)")
    pr.add_argument(
        "--include-disabled",
        action="store_true",
        help="also run sources marked enabled=False",
    )
    pr.add_argument(
        "--log-run",
        action="store_true",
        help="append a per-run summary to docs/EXPERIMENT_LOG.md",
    )
    pr.set_defaults(func=cmd_run)

    pl = sub.add_parser("list", help="List recent papers")
    pl.add_argument("--source", "-s")
    pl.add_argument("--limit", "-n", type=int, default=20)
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    ps = sub.add_parser("search", help="Search papers")
    ps.add_argument("query")
    ps.add_argument("--limit", "-n", type=int, default=50)
    ps.set_defaults(func=cmd_search)

    pst = sub.add_parser("stats", help="Show counts per source")
    pst.set_defaults(func=cmd_stats)

    pso = sub.add_parser("sources", help="List configured sources")
    pso.set_defaults(func=cmd_sources)

    pf = sub.add_parser("fetch-pdfs", help="Download papers' PDFs to data/pdfs/")
    pf.add_argument("--source", "-s", help="limit to one source")
    pf.add_argument("--limit", "-n", type=int, default=None,
                    help="max PDFs to download this run")
    pf.set_defaults(func=cmd_fetch_pdfs)

    pri = sub.add_parser("rag-ingest",
                         help="Extract downloaded PDFs into the RAG full-text store")
    pri.add_argument("--source", "-s", help="limit to one source")
    pri.add_argument("--limit", "-n", type=int, default=None,
                     help="max papers to ingest this run")
    pri.add_argument("--reindex", action="store_true",
                     help="re-extract even if already indexed")
    pri.set_defaults(func=cmd_rag_ingest)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
