"""Surface MCP server info for the dashboard.

The gs-strategy-rag server is a stdio MCP server (no resident daemon — Claude
Code spawns it per session). So "running info" = config (.mcp.json) + exposed
tools (introspected) + RAG index health + best-effort live-process detection.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from quant_crawler.config import PROJECT_ROOT
from quant_crawler.rag.store import RagStore

MCP_JSON = PROJECT_ROOT / ".mcp.json"
_SERVER_MODULE = "quant_crawler.rag.mcp_server"


def mcp_config() -> Dict[str, Any]:
    """Parse .mcp.json; tag each server with its transport."""
    if not MCP_JSON.is_file():
        return {"servers": [], "config_path": str(MCP_JSON), "found": False}
    try:
        data = json.loads(MCP_JSON.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"servers": [], "config_path": str(MCP_JSON), "error": str(exc)}
    servers = []
    for name, cfg in (data.get("mcpServers") or {}).items():
        servers.append({
            "name": name,
            "command": cfg.get("command"),
            "args": cfg.get("args", []),
            "transport": "http" if cfg.get("url") else "stdio",
            "url": cfg.get("url"),
        })
    return {"servers": servers, "config_path": str(MCP_JSON), "found": True}


def mcp_tools() -> List[Dict[str, str]]:
    """Introspect the FastMCP app for tool name + description (best-effort)."""
    try:
        from quant_crawler.rag.mcp_server import mcp
        tools = asyncio.run(mcp.list_tools())
        return [
            {"name": t.name,
             "description": (t.description or "").strip().split("\n")[0]}
            for t in tools
        ]
    except Exception as exc:  # mcp not installed / import error
        return [{"name": "(unavailable)", "description": repr(exc)}]


def running_servers() -> List[Dict[str, str]]:
    """Detect live mcp_server processes (a session may have spawned one)."""
    try:
        out = subprocess.run(
            ["pgrep", "-af", _SERVER_MODULE],
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return []
    procs: List[Dict[str, str]] = []
    for line in out.stdout.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        pid = parts[0]
        started = ""
        try:
            ps = subprocess.run(["ps", "-o", "lstart=", "-p", pid],
                                capture_output=True, text=True, timeout=5)
            started = ps.stdout.strip()
        except Exception:
            pass
        procs.append({"pid": pid, "started": started})
    return procs


def mcp_info() -> Dict[str, Any]:
    cfg = mcp_config()
    return {
        "config": cfg,
        "tools": mcp_tools(),
        "running": running_servers(),
        "rag": RagStore().stats(),
        "server_module": _SERVER_MODULE,
    }
