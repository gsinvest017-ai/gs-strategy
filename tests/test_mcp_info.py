"""Tests for webui MCP-info surface."""
from __future__ import annotations

from quant_crawler.webui import mcp_info


def test_mcp_config_parses_repo_mcp_json():
    cfg = mcp_info.mcp_config()
    assert cfg["found"] is True
    names = {s["name"] for s in cfg["servers"]}
    assert "gs-strategy-rag" in names
    rag = next(s for s in cfg["servers"] if s["name"] == "gs-strategy-rag")
    assert rag["transport"] == "stdio"
    assert "quant_crawler.rag.mcp_server" in rag["args"]


def test_mcp_tools_lists_rag_tools():
    tools = mcp_info.mcp_tools()
    names = {t["name"] for t in tools}
    assert {"search_paper_chunks", "get_paper_context", "rag_stats"} <= names
    # each has a one-line description
    assert all(t["description"] for t in tools)


def test_running_servers_returns_list():
    # may be empty (no session spawned one) — just assert shape
    procs = mcp_info.running_servers()
    assert isinstance(procs, list)
    for p in procs:
        assert "pid" in p


def test_mcp_info_combines_all():
    info = mcp_info.mcp_info()
    assert "config" in info and "tools" in info and "running" in info
    assert "rag" in info
    assert "papers_indexed" in info["rag"] and "chunks" in info["rag"]
