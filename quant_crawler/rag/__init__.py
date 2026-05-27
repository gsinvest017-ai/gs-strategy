"""RAG layer: full-text store + retrieval over crawled paper/report PDFs.

Lets Claude (via the MCP server) fetch the *original* paper context — correct
formulas, parameter definitions — when generating a faithful strategy/factor
spec, instead of relying on memory.

    store.RagStore   -- SQLite FTS5 chunk store + BM25 search
    ingest           -- pypdf text extraction -> chunks -> store
    mcp_server       -- FastMCP server exposing search/fetch tools
"""
from .store import RagStore

__all__ = ["RagStore"]
