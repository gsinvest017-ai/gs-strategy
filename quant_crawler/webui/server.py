"""Stdlib HTTP server for the gs-strategy management UI.

Zero external deps: serves a single-page dashboard from ``static/`` plus a
small read-only JSON API backed by ``stats.py``.

Routes
------
    GET /                     -> static/index.html
    GET /static/<file>        -> static asset (js/css)
    GET /api/summary          -> summary card payload
    GET /api/runs?date=...    -> crawl runs on date (default today)
    GET /api/papers?date=...&limit=N
                              -> papers fetched on date; if none and no date
                                 given, falls back to latest N
    GET /api/strategies       -> strategy inventory + export status
    GET /api/dates            -> distinct crawl dates (for the date picker)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from quant_crawler import paper_class
from quant_crawler.config import PDF_DIR, PROJECT_ROOT
from quant_crawler.storage.labels import LabelStore

from . import stats

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _git_rev() -> str:
    """Short git hash of the code this process is running (best-effort)."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# Captured ONCE when this process starts. If the on-disk code is newer than
# these, the running server is stale and must be restarted (http.server does
# not hot-reload Python). The UI footer surfaces these so staleness is visible.
SERVER_STARTED = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
CODE_REV = _git_rev()

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".pdf": "application/pdf",
    ".md": "text/markdown; charset=utf-8",
    ".yaml": "text/plain; charset=utf-8",
    ".yml": "text/plain; charset=utf-8",
    ".py": "text/plain; charset=utf-8",
}

# Files inside a strategy bundle we are willing to serve.
_STRATEGY_FILE_SUFFIXES = {".md", ".yaml", ".yml", ".py"}


class Handler(BaseHTTPRequestHandler):
    server_version = "gsStrategyWebUI/1.0"

    # Silence default noisy logging; keep a terse one-liner.
    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write(
            "[webui] %s - %s\n" % (self.address_string(), fmt % args)
        )

    # ---- helpers ----
    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel: str) -> None:
        # Prevent path traversal: resolve and ensure it stays under STATIC_DIR.
        target = (STATIC_DIR / rel).resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send_text("forbidden", 403)
            return
        if not target.is_file():
            self._send_text("not found", 404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            _CONTENT_TYPES.get(target.suffix, "application/octet-stream"),
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, target: Path, base: Path, allowed_suffixes=None,
                   inline: bool = True) -> None:
        """Serve a file after confirming it stays under `base` (anti-traversal)."""
        try:
            target = target.resolve()
            target.relative_to(base.resolve())
        except (ValueError, OSError):
            self._send_text("forbidden", 403)
            return
        if allowed_suffixes is not None and target.suffix.lower() not in allowed_suffixes:
            self._send_text("unsupported file type", 403)
            return
        if not target.is_file():
            self._send_text("not found", 404)
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            _CONTENT_TYPES.get(target.suffix.lower(), "application/octet-stream"),
        )
        disp = "inline" if inline else "attachment"
        self.send_header("Content-Disposition", f'{disp}; filename="{target.name}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---- routing ----
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path == "/" or path == "/index.html":
                self._send_static("index.html")
            elif path.startswith("/static/"):
                self._send_static(path[len("/static/"):])
            elif path == "/api/summary":
                payload = stats.summary()
                payload["server_started"] = SERVER_STARTED
                payload["code_rev"] = CODE_REV
                self._send_json(payload)
            elif path == "/api/runs":
                date = qs.get("date", [None])[0]
                self._send_json({"date": date or stats._today_iso(),
                                 "runs": stats.runs_on(date)})
            elif path == "/api/papers":
                date = qs.get("date", [None])[0]
                limit = int(qs.get("limit", ["100"])[0])
                pdf = qs.get("pdf", [None])[0]      # None | "any" | "local"
                kind = qs.get("kind", [None])[0]    # None | "strategy" | "factor"
                subcat = qs.get("subcat", [None])[0]
                if pdf in ("any", "local") or kind or subcat:
                    # Any active filter spans all papers (date ignored).
                    rows = stats.list_papers(
                        date=None, limit=limit, pdf=pdf, kind=kind, subcat=subcat
                    )
                    self._send_json({
                        "date": None, "filter": pdf, "kind": kind,
                        "subcat": subcat, "fallback_latest": False, "papers": rows,
                    })
                else:
                    rows = stats.new_papers_on(date, limit=limit)
                    fallback = False
                    if not rows and date is None:
                        rows = stats.latest_papers(limit=limit)
                        fallback = True
                    self._send_json({
                        "date": date or stats._today_iso(),
                        "filter": None, "kind": None, "subcat": None,
                        "fallback_latest": fallback,
                        "papers": rows,
                    })
            elif path == "/api/taxonomy":
                self._send_json({
                    "factor": list(paper_class.FACTOR_SUBCAT_NAMES),
                    "strategy": list(paper_class.STRATEGY_SUBCAT_NAMES),
                })
            elif path == "/api/strategies":
                self._send_json({"strategies": stats.strategy_inventory()})
            elif path == "/api/dates":
                self._send_json({"dates": stats.crawl_dates()})
            elif path == "/api/rag/stats":
                from quant_crawler.rag.store import RagStore
                from quant_crawler.rag.retrieve import list_indexed
                kind = qs.get("kind", [None])[0]
                self._send_json({
                    **RagStore().stats(),
                    "papers": list_indexed(kind=kind),
                })
            elif path == "/api/rag/search":
                from quant_crawler.rag.retrieve import search_chunks
                q = qs.get("q", [""])[0]
                kind = qs.get("kind", [None])[0]
                limit = int(qs.get("limit", ["20"])[0])
                hits = search_chunks(q, limit=limit, kind=kind) if q.strip() else []
                self._send_json({"query": q, "kind": kind, "chunks": hits})
            elif path == "/api/rag/paper":
                from quant_crawler.rag.retrieve import paper_context
                source = qs.get("source", [None])[0]
                source_id = qs.get("source_id", [None])[0]
                q = qs.get("q", [None])[0]
                if not source or not source_id:
                    self._send_json({"error": "source + source_id required"}, 400)
                else:
                    self._send_json(paper_context(source, source_id, query=q))
            elif path == "/api/mcp/info":
                from .mcp_info import mcp_info
                self._send_json(mcp_info())
            elif path.startswith("/files/pdf/"):
                name = path[len("/files/pdf/"):]
                self._send_file(PDF_DIR / name, PDF_DIR, {".pdf"})
            elif path.startswith("/files/strategy/"):
                rest = path[len("/files/strategy/"):]
                parts = rest.split("/", 1)
                if len(parts) != 2 or not parts[1]:
                    self._send_text("usage: /files/strategy/<id>/<file>", 400)
                    return
                bundle_id, fname = parts
                bundle = stats.bundle_dir_for(bundle_id)
                if bundle is None:
                    self._send_text("strategy not found", 404)
                    return
                self._send_file(bundle / fname, bundle, _STRATEGY_FILE_SUFFIXES)
            else:
                self._send_text("not found", 404)
        except BrokenPipeError:
            pass
        except Exception as exc:  # surface errors as JSON for the UI
            self._send_json({"error": repr(exc)}, status=500)

    def _handle_upload(self) -> None:
        """POST /api/upload — multipart 批次 PDF 上傳。"""
        try:
            from .upload import handle_upload
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                self._send_json({"error": "empty upload"}, 400)
                return
            # 上限保護：500 MB 總量（單檔上限在 upload module 內）
            if length > 500 * 1024 * 1024:
                self._send_json({"error": "upload too large (>500MB total)"}, 413)
                return
            ctype = self.headers.get("Content-Type", "")
            body = self.rfile.read(length)
            result = handle_upload(ctype, body)
            status = 200 if not result.get("error") else 400
            self._send_json(result, status=status)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"error": repr(exc)}, status=500)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            self._handle_upload()
            return
        if parsed.path != "/api/labels":
            self._send_text("not found", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body or b"{}")
            source = data.get("source")
            source_id = data.get("source_id")
            op = data.get("op")
            value = data.get("value")
            if not source or not source_id:
                self._send_json({"error": "source + source_id required"}, 400)
                return
            store = LabelStore()
            if op == "add_subcat":
                rec = store.add_subcat(source, str(source_id), str(value or ""))
            elif op == "remove_subcat":
                rec = store.remove_subcat(source, str(source_id), str(value or ""))
            elif op == "set_kind":
                rec = store.set_kind(source, str(source_id),
                                     value if value else None)
            else:
                self._send_json({"error": f"unknown op: {op!r}"}, 400)
                return
            self._send_json({"source": source, "source_id": source_id,
                             "label": rec})
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=400)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"error": repr(exc)}, status=500)


def serve(host: str = "127.0.0.1", port: int = 5057) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"[webui] serving gs-strategy dashboard on http://{host}:{port}")
    print("[webui] Ctrl-C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[webui] shutting down")
    finally:
        httpd.server_close()


def main(argv) -> int:
    p = argparse.ArgumentParser(description="gs-strategy management web UI")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5057)
    args = p.parse_args(argv)
    serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
