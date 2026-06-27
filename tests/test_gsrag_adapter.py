"""接共用 gs-rag 的 adapter 測試 —— 用 tmp_db fixture，不打真實 LLM。"""
from quant_crawler.gsrag_adapter import ask_papers, build_index, paper_documents
from quant_crawler.storage.db import Storage
from quant_crawler.storage.models import PaperRecord


def _rec(sid="1", title="Futures momentum", abstract="time series momentum and carry in futures markets, trend following"):
    return PaperRecord(
        source="arxiv",
        source_id=sid,
        title=title,
        authors=["A", "B"],
        abstract=abstract,
        published="2026-04-01",
        url=f"https://arxiv.org/abs/{sid}",
        categories=["q-fin.TR"],
        keywords_hit=["futures", "momentum"],
    )


def test_paper_documents_skips_empty_abstract(tmp_db):
    s = Storage(tmp_db)
    s.upsert(_rec(sid="has", abstract="real abstract about volatility and hedging"))
    s.upsert(_rec(sid="empty", abstract=""))
    docs = list(paper_documents(Storage(tmp_db)))
    ids = {d.id for d in docs}
    assert any("has" in i for i in ids)
    assert not any("empty" in i for i in ids)
    d = next(d for d in docs if "has" in d.id)
    assert d.metadata["source"] == "arxiv" and d.metadata["title"]
    assert d.id == "arxiv:has"


def test_build_index_counts(tmp_db):
    s = Storage(tmp_db)
    s.upsert(_rec(sid="a"))
    s.upsert(_rec(sid="b", title="Volatility risk premium", abstract="variance risk premium in options"))
    gsrag_db = tmp_db.parent / "gsrag.db"
    n, fallback = build_index(papers_db=tmp_db, gsrag_db=gsrag_db)
    assert n >= 2 and fallback is None


def test_ask_off_topic_refused(tmp_db):
    s = Storage(tmp_db)
    s.upsert(_rec(sid="a"))
    gsrag_db = tmp_db.parent / "gsrag.db"
    build_index(papers_db=tmp_db, gsrag_db=gsrag_db)
    ans = ask_papers("how to cook pasta carbonara", gsrag_db=gsrag_db)
    assert ans.mode == "refused" and ans.grounded is False
    assert not ans.citations


def test_ask_on_topic_grounded_with_fake_generator(tmp_db, monkeypatch):
    s = Storage(tmp_db)
    s.upsert(_rec(sid="a"))
    gsrag_db = tmp_db.parent / "gsrag.db"
    build_index(papers_db=tmp_db, gsrag_db=gsrag_db)
    # 注入假 generator，避免呼叫真實 claude CLI（快速、確定性）。
    import gs_rag.answer as A
    monkeypatch.setattr(A, "default_generator",
                        lambda: (lambda prompt: "時間序列動量是一種趨勢跟隨策略 [1]。"))
    ans = ask_papers("what is momentum in futures markets", gsrag_db=gsrag_db)
    assert ans.mode == "llm" and ans.grounded is True
    assert ans.citations and ans.citations[0].doc_id == "arxiv:a"
