"""MCP server exposing the RAG store so Claude can fetch original paper/report
context (correct formulas, parameter definitions) when generating a faithful
strategy/factor spec.

Run (stdio transport):
    python -m quant_crawler.rag.mcp_server

Register in Claude Code via .mcp.json (see repo root) or:
    claude mcp add gs-strategy-rag -- \\
        /home/kevin/gs-strategy/.venv/bin/python -m quant_crawler.rag.mcp_server
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from quant_crawler.rag import retrieve
from quant_crawler.rag.store import RagStore

mcp = FastMCP("gs-strategy-rag")


@mcp.tool()
def search_paper_chunks(
    query: str, kind: Optional[str] = None, limit: int = 8
) -> List[Dict[str, Any]]:
    """Full-text (BM25) search across all indexed paper/report chunks.

    Use this to locate where a concept, formula, or definition appears across
    the crawled corpus when you don't yet know which paper to read.

    Args:
        query: free-text query, e.g. "cubic momentum critical threshold formula".
        kind: optional filter, "strategy" or "factor" (paper classification).
        limit: max chunks to return (default 8).

    Returns a list of chunks, each with: source, source_id, title, kind, url,
    page, chunk_idx, score (lower = more relevant), and text.
    """
    return retrieve.search_chunks(query, limit=limit, kind=kind)


@mcp.tool()
def get_paper_context(
    source: str, source_id: str, query: str, max_chunks: int = 6
) -> Dict[str, Any]:
    """Targeted retrieval WITHIN a single known paper.

    Use this when you already know which paper you're writing a spec for (its
    source + source_id) and want the passages most relevant to `query` — e.g.
    the exact signal/factor formula or parameter values — to quote faithfully.

    Returns {source, source_id, title, kind, url, query, chunks:[{page,
    chunk_idx, score, text}]}.
    """
    return retrieve.paper_context(source, source_id, query=query,
                                  max_chunks=max_chunks)


@mcp.tool()
def get_paper_fulltext(source: str, source_id: str) -> Dict[str, Any]:
    """Return the full extracted text of one indexed paper/report.

    Use when you need the complete context of a paper (small/medium papers).
    Returns {source, source_id, title, kind, url, fulltext, n_chunks} or
    {indexed: False} if the paper has no indexed text yet.
    """
    return retrieve.paper_context(source, source_id)


@mcp.tool()
def list_indexed_papers(kind: Optional[str] = None) -> List[Dict[str, Any]]:
    """List papers/reports that have indexed full text available for RAG.

    Args:
        kind: optional "strategy" or "factor" filter.

    Returns [{source, source_id, title, kind, n_chunks}].
    """
    return retrieve.list_indexed(kind=kind)


@mcp.tool()
def rag_stats() -> Dict[str, int]:
    """Index health: number of papers indexed and total chunks."""
    return RagStore().stats()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
