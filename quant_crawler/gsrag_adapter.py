"""接共用模組 gs-rag —— 把 papers.db 的論文轉成可信賴的帶引用問答。

gs-strategy 是 gs-rag 的第二個 consumer（第一個是 gs-academy）。本檔只做兩件事：
1. 語料 adapter：papers 表每篇論文（title + abstract）轉成 gs_rag.Document。
2. 薄包裝：建索引 / 提問，把 source 對應成 gs-rag 的 where 過濾。

檢索（BM25，純 stdlib）、帶引用生成與兩道信任閘全在 gs-rag。索引落在獨立檔
data/gsrag.db，不碰既有 papers.db / quant_crawler.rag 的 FTS5 索引。
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional

from gs_rag import Answer, Document, ask, get_retriever

from quant_crawler.config import DATA_DIR
from quant_crawler.storage.db import Storage

GSRAG_DB = DATA_DIR / 'gsrag.db'


def paper_documents(storage: Storage) -> Iterator[Document]:
    """papers 表 → gs_rag.Document 串流（略過無 abstract 者）。"""
    total = storage.count()
    for p in storage.latest(limit=total or 1):
        abstract = (p.abstract or '').strip()
        if not abstract:
            continue
        yield Document(
            id=f'{p.source}:{p.source_id}',
            text=f'# {p.title}\n\n{abstract}',
            metadata={
                'title': p.title,
                'source': p.source,
                'source_id': p.source_id,
                'url': p.url,
                'year': (p.published or '')[:4],
            },
        )


def build_index(papers_db: Optional[Path] = None, gsrag_db: Path = GSRAG_DB,
                backend: str = 'bm25') -> tuple[int, Optional[str]]:
    """（重）建 gs-rag 索引。回 (chunk 數, fallback 原因或 None)。"""
    storage = Storage(papers_db) if papers_db else Storage()
    retriever, fallback = get_retriever(gsrag_db, backend=backend)
    n = retriever.rebuild(paper_documents(storage))
    return n, fallback


def ask_papers(question: str, gsrag_db: Path = GSRAG_DB, *, backend: str = 'bm25',
               top_k: int = 5, source: Optional[str] = None) -> Answer:
    """對論文庫提問，回傳帶引用的 Answer（source 對應 gs-rag 的 where 過濾）。"""
    retriever, _ = get_retriever(gsrag_db, backend=backend)
    where = {'source': source} if source else None
    return ask(question, retriever=retriever, where=where, top_k=top_k)
