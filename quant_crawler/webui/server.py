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
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import stats

STATIC_DIR = Path(__file__).resolve().parent / "static"

_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


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
                self._send_json(stats.summary())
            elif path == "/api/runs":
                date = qs.get("date", [None])[0]
                self._send_json({"date": date or stats._today_iso(),
                                 "runs": stats.runs_on(date)})
            elif path == "/api/papers":
                date = qs.get("date", [None])[0]
                limit = int(qs.get("limit", ["100"])[0])
                rows = stats.new_papers_on(date, limit=limit)
                fallback = False
                if not rows and date is None:
                    rows = stats.latest_papers(limit=limit)
                    fallback = True
                self._send_json({
                    "date": date or stats._today_iso(),
                    "fallback_latest": fallback,
                    "papers": rows,
                })
            elif path == "/api/strategies":
                self._send_json({"strategies": stats.strategy_inventory()})
            elif path == "/api/dates":
                self._send_json({"dates": stats.crawl_dates()})
            else:
                self._send_text("not found", 404)
        except BrokenPipeError:
            pass
        except Exception as exc:  # surface errors as JSON for the UI
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
