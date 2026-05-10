from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord


def _rec(source="t", sid="1", title="Futures momentum", abstract="trend following carry"):
    return PaperRecord(
        source=source,
        source_id=sid,
        title=title,
        authors=["A", "B"],
        abstract=abstract,
        published="2026-04-01",
        url=f"https://example.com/{sid}",
        categories=["q-fin.TR"],
        keywords_hit=["futures", "momentum"],
    )


def test_upsert_inserts_then_updates(tmp_db):
    s = Storage(tmp_db)
    rec = _rec(sid="x1", title="Original")
    assert s.upsert(rec) is True
    assert s.count() == 1
    rec2 = _rec(sid="x1", title="Updated")
    assert s.upsert(rec2) is False  # update path
    rows = s.latest(5)
    assert rows[0].title == "Updated"


def test_search_matches_title_or_abstract(tmp_db):
    s = Storage(tmp_db)
    s.upsert(_rec(sid="a", title="Carry in commodities", abstract="x"))
    s.upsert(_rec(sid="b", title="Equity factors", abstract="discusses momentum heavily"))
    s.upsert(_rec(sid="c", title="Crypto microstructure", abstract="nothing here"))
    titles = {p.title for p in s.search("momentum")}
    assert "Equity factors" in titles
    assert "Crypto microstructure" not in titles


def test_stats_by_source(tmp_db):
    s = Storage(tmp_db)
    for i, src in enumerate(["arxiv", "arxiv", "nber"]):
        s.upsert(_rec(source=src, sid=f"{src}-{i}"))
    stats = dict(s.stats_by_source())
    assert stats["arxiv"] == 2
    assert stats["nber"] == 1


def test_run_accounting(tmp_db):
    s = Storage(tmp_db)
    rid = s.start_run("arxiv", "2026-05-10T00:00:00Z")
    assert rid > 0
    s.finish_run(rid, "2026-05-10T00:01:00Z", items_seen=5, items_kept=3)
