"""Tests for the RAG MCP server (tool registration + in-process dispatch).

The full stdio wire protocol is exercised manually (see progress doc); these
tests cover the MCP-specific surface fast and deterministically against the
live repo index (read-only).
"""
from __future__ import annotations

import asyncio
import json

import pytest

from quant_crawler.rag.mcp_server import mcp

EXPECTED_TOOLS = {
    "search_paper_chunks", "get_paper_context", "get_paper_fulltext",
    "list_indexed_papers", "rag_stats",
}


def test_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS


def test_tools_have_descriptions_and_schemas():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name, t in tools.items():
        assert t.description and len(t.description) > 20, f"{name} lacks docs"
        assert t.inputSchema is not None


def _call(name, args):
    res = asyncio.run(mcp.call_tool(name, args))
    # Newer FastMCP returns (content_list, structured_result); the structured
    # result is the actual Python return value — prefer it.
    if isinstance(res, tuple):
        content, structured = res[0], (res[1] if len(res) > 1 else None)
        if isinstance(structured, dict):
            # FastMCP wraps non-dict returns under {"result": ...}
            return structured.get("result", structured)
        if structured is not None:
            return structured
        res = content
    # Fallback: concatenate text content items and JSON-parse.
    texts = [getattr(i, "text", "") for i in res]
    if len(texts) == 1:
        return json.loads(texts[0])
    return [json.loads(t) for t in texts]


def test_rag_stats_dispatch():
    out = _call("rag_stats", {})
    assert "papers_indexed" in out and "chunks" in out
    assert isinstance(out["papers_indexed"], int)


def test_list_indexed_papers_dispatch():
    out = _call("list_indexed_papers", {})
    assert isinstance(out, list)
    if out:
        assert {"source", "source_id", "n_chunks"} <= set(out[0])
