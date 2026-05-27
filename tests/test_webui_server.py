"""Integration tests for the webui HTTP server.

Boots the real stdlib server on an ephemeral port in a background thread and
hits every route over HTTP. Asserts structural properties against the live
repo data (papers.db + strategies/) rather than exact counts, so the test is
robust to crawler activity.
"""
from __future__ import annotations

import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from quant_crawler.webui.server import Handler


@pytest.fixture(scope="module")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}"
    httpd.shutdown()
    httpd.server_close()


def _get(base: str, path: str):
    with urllib.request.urlopen(base + path, timeout=10) as r:
        return r.status, r.read(), r.headers.get("Content-Type", "")


def _get_status(base: str, path: str) -> int:
    try:
        with urllib.request.urlopen(base + path, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def test_index_served(server: str) -> None:
    status, body, ctype = _get(server, "/")
    assert status == 200
    assert "text/html" in ctype
    assert b"<title>gs-strategy" in body


def test_static_assets(server: str) -> None:
    for path, frag in [("/static/app.js", "application/javascript"),
                       ("/static/style.css", "text/css")]:
        status, body, ctype = _get(server, path)
        assert status == 200
        assert frag in ctype
        assert len(body) > 0


def test_api_summary_shape(server: str) -> None:
    status, body, ctype = _get(server, "/api/summary")
    assert status == 200
    assert "application/json" in ctype
    s = json.loads(body)
    for key in ("papers_total", "papers_by_source", "runs_today",
                "strategies_total", "strategies_exported",
                "strategies_pending", "export_dir", "today"):
        assert key in s, f"missing {key}"
    assert isinstance(s["papers_total"], int)
    assert isinstance(s["papers_by_source"], list)


def test_api_strategies_shape(server: str) -> None:
    status, body, _ = _get(server, "/api/strategies")
    assert status == 200
    data = json.loads(body)
    assert "strategies" in data
    for s in data["strategies"]:
        for key in ("id", "origin", "tags", "exported", "requires_review"):
            assert key in s
        assert s["origin"] in ("manual", "generated")
        assert isinstance(s["exported"], bool)


def test_api_runs_known_date(server: str) -> None:
    # 2026-05-10 has real crawl_runs in the repo's papers.db.
    status, body, _ = _get(server, "/api/runs?date=2026-05-10")
    assert status == 200
    data = json.loads(body)
    assert data["date"] == "2026-05-10"
    assert isinstance(data["runs"], list)
    if data["runs"]:
        r = data["runs"][0]
        for key in ("source", "started_at", "items_seen", "items_kept", "ok"):
            assert key in r


def test_api_papers_fallback_latest(server: str) -> None:
    # A date with no fetched papers + no explicit date triggers latest
    # fallback; here we just assert the endpoint returns the documented shape.
    status, body, _ = _get(server, "/api/papers?limit=5")
    assert status == 200
    data = json.loads(body)
    assert "papers" in data and "fallback_latest" in data
    assert len(data["papers"]) <= 5


def _post(base: str, path: str, payload: dict):
    import urllib.request

    def _parse(raw: bytes):
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return raw.decode(errors="replace")

    req = urllib.request.Request(
        base + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, _parse(r.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


def test_api_taxonomy(server: str) -> None:
    status, body, _ = _get(server, "/api/taxonomy")
    assert status == 200
    d = json.loads(body)
    assert "value" in d["factor"]
    assert "trend-following" in d["strategy"]


def test_api_papers_kind_filter(server: str) -> None:
    status, body, _ = _get(server, "/api/papers?kind=factor&limit=500")
    assert status == 200
    d = json.loads(body)
    assert d["kind"] == "factor"
    assert all(p["kind"] == "factor" for p in d["papers"])


def test_post_labels_roundtrip(server: str) -> None:
    """add_subcat -> appears; set_kind -> overridden; cleanup."""
    src, sid = "arxiv", "2604.19107"   # real paper in repo DB
    try:
        st, rec = _post(server, "/api/labels",
                        {"source": src, "source_id": sid,
                         "op": "add_subcat", "value": "srvtest"})
        assert st == 200
        assert "srvtest" in rec["label"]["manual_subcats"]
        st, rec = _post(server, "/api/labels",
                        {"source": src, "source_id": sid,
                         "op": "set_kind", "value": "factor"})
        assert st == 200
        assert rec["label"]["kind_override"] == "factor"
        # verify via GET
        _, body, _ = _get(server, "/api/papers?kind=factor&subcat=srvtest&limit=500")
        ids = {(p["source"], p["source_id"]) for p in json.loads(body)["papers"]}
        assert (src, sid) in ids
    finally:
        _post(server, "/api/labels", {"source": src, "source_id": sid,
                                      "op": "remove_subcat", "value": "srvtest"})
        _post(server, "/api/labels", {"source": src, "source_id": sid,
                                      "op": "set_kind", "value": None})


def test_post_labels_bad_op(server: str) -> None:
    st, rec = _post(server, "/api/labels",
                    {"source": "a", "source_id": "b", "op": "bogus"})
    assert st == 400


def test_post_labels_missing_fields(server: str) -> None:
    st, _ = _post(server, "/api/labels", {"op": "add_subcat", "value": "x"})
    assert st == 400


def test_post_unknown_path_404(server: str) -> None:
    st, _ = _post(server, "/api/nope", {})
    assert st == 404


def test_api_papers_local_filter(server: str) -> None:
    """pdf=local must only return papers that have a downloaded local file.
    The repo has 2 real downloaded arxiv PDFs (from the fetch-pdfs smoke)."""
    status, body, _ = _get(server, "/api/papers?pdf=local&limit=200")
    assert status == 200
    data = json.loads(body)
    assert data["filter"] == "local"
    # every returned paper must carry a non-null pdf_local
    assert all(p["pdf_local"] for p in data["papers"])


def test_api_papers_any_filter(server: str) -> None:
    status, body, _ = _get(server, "/api/papers?pdf=any&limit=500")
    assert status == 200
    data = json.loads(body)
    assert data["filter"] == "any"
    assert all((p["pdf_local"] or p["pdf_url"]) for p in data["papers"])


def test_api_dates(server: str) -> None:
    status, body, _ = _get(server, "/api/dates")
    assert status == 200
    assert isinstance(json.loads(body)["dates"], list)


def test_api_rag_stats(server: str) -> None:
    status, body, _ = _get(server, "/api/rag/stats")
    assert status == 200
    d = json.loads(body)
    assert "papers_indexed" in d and "chunks" in d and "papers" in d
    assert isinstance(d["papers"], list)


def test_api_rag_search(server: str) -> None:
    status, body, _ = _get(server, "/api/rag/search?q=momentum&limit=5")
    assert status == 200
    d = json.loads(body)
    assert d["query"] == "momentum"
    assert isinstance(d["chunks"], list)
    for c in d["chunks"]:
        assert {"source", "source_id", "page", "text", "score"} <= set(c)


def test_api_rag_search_empty_query(server: str) -> None:
    status, body, _ = _get(server, "/api/rag/search?q=")
    assert status == 200
    assert json.loads(body)["chunks"] == []


def test_api_rag_paper_requires_ids(server: str) -> None:
    assert _get_status(server, "/api/rag/paper") == 400


def test_api_mcp_info(server: str) -> None:
    status, body, _ = _get(server, "/api/mcp/info")
    assert status == 200
    d = json.loads(body)
    assert d["config"]["found"] is True
    assert any(t["name"] == "rag_stats" for t in d["tools"])
    assert "papers_indexed" in d["rag"]
    assert isinstance(d["running"], list)


def test_unknown_route_404(server: str) -> None:
    assert _get_status(server, "/api/nope") == 404


def test_static_traversal_blocked(server: str) -> None:
    # Encoded traversal must not escape the static dir.
    status = _get_status(server, "/static/%2e%2e/config.py")
    assert status in (403, 404)


# ---- file-serving routes (PDF + strategy spec markdown) ----

def test_strategy_spec_md_served(server: str) -> None:
    # vgrsi_tx is a real hand-authored bundle with a README.md spec.
    status, body, ctype = _get(server, "/files/strategy/vgrsi_tx/README.md")
    assert status == 200
    assert "text/markdown" in ctype
    assert len(body) > 0


def test_strategy_manifest_served(server: str) -> None:
    status, _, _ = _get(server, "/files/strategy/vgrsi_tx/manifest.yaml")
    assert status == 200


def test_strategy_unknown_id_404(server: str) -> None:
    assert _get_status(server, "/files/strategy/does_not_exist/README.md") == 404


def test_strategy_disallowed_suffix_403(server: str) -> None:
    # .pickle / arbitrary suffix not in the allow-list
    assert _get_status(server, "/files/strategy/vgrsi_tx/secret.env") == 403


def test_pdf_route_missing_is_404(server: str) -> None:
    assert _get_status(server, "/files/pdf/definitely_absent_xyz.pdf") == 404


def test_pdf_route_traversal_blocked(server: str) -> None:
    assert _get_status(server, "/files/pdf/..%2f..%2fconfig.py") in (403, 404)
