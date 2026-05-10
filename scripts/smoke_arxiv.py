"""Tiny live smoke test against arXiv (limit=5)."""
import dataclasses

from quant_crawler.config import SOURCES
from quant_crawler.crawlers.arxiv import ArxivCrawler
from quant_crawler.storage.db import Storage


def main() -> None:
    cfg = dataclasses.replace(SOURCES["arxiv"], max_items_per_run=5)
    storage = Storage()
    c = ArxivCrawler(cfg, storage)
    result = c.run()
    print("RESULT:", result)
    print("total in db:", storage.count("arxiv"))
    for p in storage.latest(10, "arxiv"):
        cats = ",".join(p.categories[:3])
        pub = (p.published or "?")[:10]
        print(f"- {pub} | {p.title[:80]} | {cats}")


if __name__ == "__main__":
    main()
