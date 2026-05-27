"""Tests for the management-UI data layer (quant_crawler.webui.stats)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
import yaml

from quant_crawler.webui import stats


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE papers (
            source TEXT, source_id TEXT, title TEXT, authors TEXT,
            abstract TEXT, published TEXT, updated TEXT, url TEXT,
            pdf_url TEXT, categories TEXT, keywords_hit TEXT, doi TEXT,
            raw_extra TEXT, fetched_at TEXT, PRIMARY KEY (source, source_id)
        );
        CREATE TABLE crawl_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, started_at TEXT,
            finished_at TEXT, items_seen INTEGER, items_kept INTEGER, error TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO papers (source, source_id, title, published, url, fetched_at) "
        "VALUES (?,?,?,?,?,?)",
        [
            ("arxiv", "1", "Momentum paper", "2026-05-01", "u1", "2026-05-27T01:00:00Z"),
            ("arxiv", "2", "Carry paper", "2026-04-01", "u2", "2026-05-27T02:00:00Z"),
            ("wiley", "3", "Vol paper", "2026-03-01", "u3", "2026-05-10T02:00:00Z"),
        ],
    )
    conn.executemany(
        "INSERT INTO crawl_runs (source, started_at, finished_at, items_seen, items_kept, error) "
        "VALUES (?,?,?,?,?,?)",
        [
            ("arxiv", "2026-05-27T01:00:00Z", "2026-05-27T01:00:05Z", 34, 2, None),
            ("wiley", "2026-05-27T01:01:00Z", "2026-05-27T01:01:02Z", 28, 0, None),
            ("nber", "2026-05-27T01:02:00Z", None, 0, 0, "timeout"),
            ("aqr", "2026-05-10T02:00:00Z", "2026-05-10T02:00:01Z", 10, 10, None),
        ],
    )
    conn.commit()
    conn.close()


def _make_bundle(root: Path, bundle_id: str, *, generated: bool = False,
                 requires_review: bool = False, template: str | None = None) -> None:
    sub = root / "_generated" / bundle_id if generated else root / bundle_id
    sub.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": bundle_id,
        "name": bundle_id.replace("_", " ").title(),
        "asset_class": "future",
        "bundle": "tquant_future",
        "tags": ["paper", "momentum"],
        "requires_review": requires_review,
        "source": {"kind": "generated" if generated else "manual"},
    }
    if template:
        manifest["source"]["template"] = template
    (sub / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    p = tmp_path / "papers.db"
    _make_db(p)
    return p


@pytest.fixture
def strat_root(tmp_path: Path) -> Path:
    root = tmp_path / "strategies"
    _make_bundle(root, "vgrsi_tx")                       # manual
    _make_bundle(root, "tsmom_tx_mtx")                   # manual
    _make_bundle(root, "arxiv_2605_01300", generated=True,
                 requires_review=True, template="momentum")
    return root


@pytest.fixture
def export_dir(tmp_path: Path) -> Path:
    # Pretend vgrsi_tx is already exported to gs-zipline-tej.
    exp = tmp_path / "zipline_strats"
    (exp / "vgrsi_tx").mkdir(parents=True)
    (exp / "vgrsi_tx" / "manifest.yaml").write_text("id: vgrsi_tx\n", encoding="utf-8")
    return exp


def test_papers_summary(db: Path) -> None:
    s = stats.papers_summary(db)
    assert s["total"] == 3
    by = {x["source"]: x["count"] for x in s["by_source"]}
    assert by == {"arxiv": 2, "wiley": 1}


def test_runs_on_specific_date(db: Path) -> None:
    runs = stats.runs_on("2026-05-27", db)
    assert len(runs) == 3
    sources = {r["source"] for r in runs}
    assert sources == {"arxiv", "wiley", "nber"}
    nber = next(r for r in runs if r["source"] == "nber")
    assert nber["ok"] is False           # errored + unfinished
    assert nber["error"] == "timeout"
    arxiv = next(r for r in runs if r["source"] == "arxiv")
    assert arxiv["ok"] is True


def test_runs_on_other_date(db: Path) -> None:
    runs = stats.runs_on("2026-05-10", db)
    assert len(runs) == 1
    assert runs[0]["source"] == "aqr"


def test_new_papers_on(db: Path) -> None:
    rows = stats.new_papers_on("2026-05-27", db_path=db)
    assert len(rows) == 2
    assert {r["source_id"] for r in rows} == {"1", "2"}
    # ordered by published DESC -> 2026-05-01 (id 1) before 2026-04-01 (id 2)
    assert rows[0]["source_id"] == "1"


def test_latest_papers(db: Path) -> None:
    rows = stats.latest_papers(limit=2, db_path=db)
    assert len(rows) == 2
    # newest fetched_at first
    assert rows[0]["source_id"] == "2"


def test_crawl_dates(db: Path) -> None:
    dates = stats.crawl_dates(db)
    assert dates == ["2026-05-27", "2026-05-10"]


def test_strategy_inventory_and_export(strat_root: Path, export_dir: Path) -> None:
    inv = stats.strategy_inventory(strat_root, export_dir)
    by_id = {s["id"]: s for s in inv}
    assert set(by_id) == {"vgrsi_tx", "tsmom_tx_mtx", "arxiv_2605_01300"}
    # origins
    assert by_id["vgrsi_tx"]["origin"] == "manual"
    assert by_id["arxiv_2605_01300"]["origin"] == "generated"
    assert by_id["arxiv_2605_01300"]["template"] == "momentum"
    assert by_id["arxiv_2605_01300"]["requires_review"] is True
    # export status
    assert by_id["vgrsi_tx"]["exported"] is True
    assert by_id["tsmom_tx_mtx"]["exported"] is False
    assert by_id["arxiv_2605_01300"]["exported"] is False


def test_summary_counts(db: Path, strat_root: Path, export_dir: Path) -> None:
    s = stats.summary(db, strat_root, export_dir)
    assert s["papers_total"] == 3
    assert s["strategies_total"] == 3
    assert s["strategies_manual"] == 2
    assert s["strategies_generated"] == 1
    assert s["strategies_exported"] == 1
    assert s["strategies_pending"] == 2
    assert s["runs_today"] == stats.summary(db, strat_root, export_dir)["runs_today"]


def test_paper_row_attaches_pdf_local(db: Path, monkeypatch) -> None:
    """new_papers_on marks pdf_local when the downloaded file exists.

    Patch stats.has_local_pdf (the dependency stats uses) so the test doesn't
    touch the real data/pdfs dir.
    """
    monkeypatch.setattr(
        stats, "has_local_pdf",
        lambda source, sid: source == "arxiv" and sid == "1",
    )
    rows = stats.new_papers_on("2026-05-27", db_path=db)
    by = {r["source_id"]: r for r in rows}
    assert by["1"]["pdf_local"] == "arxiv_1.pdf"
    assert by["2"]["pdf_local"] is None


def test_bundle_dir_for(strat_root: Path) -> None:
    assert stats.bundle_dir_for("vgrsi_tx", strat_root) == strat_root / "vgrsi_tx"
    assert stats.bundle_dir_for("arxiv_2605_01300", strat_root) == \
        strat_root / "_generated" / "arxiv_2605_01300"
    assert stats.bundle_dir_for("nope", strat_root) is None


def test_inventory_reports_spec_files(strat_root: Path, export_dir: Path) -> None:
    inv = stats.strategy_inventory(strat_root, export_dir)
    rec = next(s for s in inv if s["id"] == "vgrsi_tx")
    # fixture bundles only write manifest.yaml (no README), so has_spec_md False
    assert rec["has_spec_md"] is False
    assert "manifest.yaml" in rec["spec_files"]


def test_missing_db_is_graceful(tmp_path: Path) -> None:
    missing = tmp_path / "nope.db"
    assert stats.papers_summary(missing) == {"total": 0, "by_source": []}
    assert stats.runs_on("2026-05-27", missing) == []
    assert stats.new_papers_on("2026-05-27", db_path=missing) == []
