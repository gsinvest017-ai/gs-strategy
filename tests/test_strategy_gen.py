"""Tests for the quant_crawler.strategy_gen pipeline.

Covers classification rules and (in M3+) the jinja generator + idempotency.
"""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from quant_crawler.strategy_gen.classify import (
    TEMPLATES,
    classify_paper,
)
from quant_crawler.strategy_gen.generate import (
    generate_bundle,
    paper_slug,
    select_recent_papers,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATE = REPO_ROOT / "scripts" / "validate_dashboard_bundle.py"


@pytest.mark.parametrize("title,abstract,expected", [
    # momentum bucket
    ("Cross-sectional momentum in commodity futures", "", "momentum"),
    ("Time-Series Momentum signals", "", "momentum"),
    ("Trend-following CTA over a century", "", "momentum"),
    ("Breakout strategy on TX", "", "momentum"),
    # mean-reversion bucket
    ("RSI-based contrarian trades", "", "mean_reversion"),
    ("A pairs trading approach for ETFs", "", "mean_reversion"),
    ("Statistical arbitrage on tech stocks", "", "mean_reversion"),
    ("Cointegration-based portfolio construction", "", "mean_reversion"),
    # fallback bucket
    ("On the dividend yield anomaly", "Discusses payout policy.", "buy_and_hold"),
    ("Implied volatility surfaces — a survey", "", "buy_and_hold"),
])
def test_classify_known_buckets(title: str, abstract: str, expected: str) -> None:
    paper = {"title": title, "abstract": abstract}
    r = classify_paper(paper)
    assert r.template == expected


def test_classify_priority_momentum_over_mean_rev() -> None:
    """If a title hits both buckets, the higher-priority one wins."""
    paper = {"title": "Momentum strategies and RSI signals — a unified view"}
    r = classify_paper(paper)
    assert r.template == "momentum", f"Expected momentum priority, got {r.template}"
    # The matched keywords should be from the momentum bucket
    assert any("momentum" in k for k in r.matched_keywords)


def test_classify_returns_default_params() -> None:
    paper = {"title": "TSMOM revisited"}
    r = classify_paper(paper)
    assert r.template == "momentum"
    # default_params is what we'll feed into the manifest.params block
    assert r.default_params["lookback"] == 252
    assert r.default_params["skip"] == 21
    assert "root_symbol" in r.default_params


def test_classify_uses_abstract_and_keywords_hit() -> None:
    """Classifier should also scan abstract + the crawler's keywords_hit."""
    paper = {
        "title": "Some neutral title",
        "abstract": "We analyse mean reversion in the SPY ETF.",
        "keywords_hit": ["mean reversion"],
    }
    r = classify_paper(paper)
    assert r.template == "mean_reversion"


def test_fallback_is_marked_is_fallback() -> None:
    r = classify_paper({"title": "Unrelated macro paper", "abstract": ""})
    assert r.is_fallback is True
    assert r.template == "buy_and_hold"


def test_specific_template_is_not_marked_fallback() -> None:
    r = classify_paper({"title": "Momentum"})
    assert r.is_fallback is False


def test_classify_categories_field() -> None:
    """arxiv categories field (list-typed) should be searched too."""
    paper = {
        "title": "A note",
        "abstract": "",
        "categories": ["q-fin.TR", "stat.AP"],
        "keywords_hit": ["breakout"],
    }
    r = classify_paper(paper)
    assert r.template == "momentum"
    assert "breakout" in r.matched_keywords


def test_templates_have_unique_names() -> None:
    names = [t.name for t in TEMPLATES]
    assert len(names) == len(set(names)), f"duplicate template name in {names}"


def test_buy_and_hold_is_last_template() -> None:
    """Order matters — fallback MUST be last so signal templates take precedence."""
    assert TEMPLATES[-1].name == "buy_and_hold"
    # … and is the only one with an empty keyword pattern set
    empty_patterns = [t.name for t in TEMPLATES if not t.keyword_patterns]
    assert empty_patterns == ["buy_and_hold"]


# --------------------------- generate.py tests ----------------------------

class TestPaperSlug:
    @pytest.mark.parametrize("src,sid,expected", [
        ("arxiv", "2605.01300", "arxiv_2605_01300"),
        ("nber", "w30001", "nber_w30001"),
        ("wiley", "fut.70093", "wiley_fut_70093"),
        ("repec", "RePEc:elg:eechap:21376_5", "repec_repec_elg_eechap_21376_5"),
    ])
    def test_basic_shapes(self, src: str, sid: str, expected: str) -> None:
        assert paper_slug(src, sid) == expected

    def test_truncates_to_64(self) -> None:
        s = paper_slug("arxiv", "x" * 200)
        assert len(s) <= 64

    def test_strips_punctuation(self) -> None:
        s = paper_slug("doi", "10.1093/rfs/abc-123.def")
        assert "/" not in s
        assert "." not in s
        assert s.startswith("doi_10_1093")

    def test_starts_with_alphanumeric(self) -> None:
        s = paper_slug("___", "9.99")
        assert s[0].isalnum()


_DUMMY_PAPER = {
    "source": "arxiv",
    "source_id": "2605.01300",
    "title": "Cross-sectional momentum across global equities",
    "authors": ["Alice", "Bob"],
    "abstract": "We document a momentum effect using a 12-1 lookback.",
    "published": "2026-04-15",
    "url": "https://arxiv.org/abs/2605.01300",
    "doi": None,
    "categories": ["q-fin.TR", "stat.AP"],
    "keywords_hit": ["momentum"],
}


def test_generate_bundle_layout(tmp_path: Path) -> None:
    out_root = tmp_path / "gen"
    path = generate_bundle(_DUMMY_PAPER, out_root=out_root)
    assert path == out_root / "arxiv_2605_01300"
    assert (path / "manifest.yaml").is_file()
    assert (path / "strategy.py").is_file()
    assert (path / "futures_setup.py").is_file()
    assert (path / "README.md").is_file()


def test_generate_bundle_manifest_picks_momentum_template(tmp_path: Path) -> None:
    path = generate_bundle(_DUMMY_PAPER, out_root=tmp_path / "g")
    manifest = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["id"] == "arxiv_2605_01300"
    assert manifest["source"]["kind"] == "generated"
    assert manifest["source"]["template"] == "momentum"
    assert manifest["requires_review"] is True
    assert manifest["params"]["lookback"] == 252
    # The strategy.py should be the momentum skeleton — pick a unique marker
    strategy_src = (path / "strategy.py").read_text(encoding="utf-8")
    assert "_generate_signal" in strategy_src
    assert "Auto-generated MOMENTUM skeleton" in strategy_src


def test_generate_bundle_mean_reversion_template(tmp_path: Path) -> None:
    paper = dict(
        _DUMMY_PAPER,
        title="RSI mean reversion in TX futures",
        abstract="An oscillator-based contrarian rule on TX.",
        source_id="9999.99999",
        keywords_hit=["rsi", "mean reversion"],
        categories=[],
    )
    path = generate_bundle(paper, out_root=tmp_path / "g")
    manifest = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["source"]["template"] == "mean_reversion"
    assert "_compute_oscillator" in (path / "strategy.py").read_text(encoding="utf-8")


def test_generate_bundle_buy_and_hold_fallback(tmp_path: Path) -> None:
    paper = dict(_DUMMY_PAPER, title="Implied vol surfaces — a survey",
                 abstract="No signal here.", keywords_hit=[], categories=[])
    path = generate_bundle(paper, out_root=tmp_path / "g")
    manifest = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["source"]["template"] == "buy_and_hold"
    assert "BUY-AND-HOLD" in (path / "strategy.py").read_text(encoding="utf-8")


def test_generate_bundle_passes_validator(tmp_path: Path) -> None:
    """End-to-end: the emitted bundle must pass the dashboard validator."""
    path = generate_bundle(_DUMMY_PAPER, out_root=tmp_path / "gen")
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        f"validator failed:\nstdout: {r.stdout}\nstderr: {r.stderr}"
    )


def test_generate_bundle_idempotent_preserves_edits(tmp_path: Path) -> None:
    """A re-run on the same paper preserves human edits and refreshes only
    the generator's own bookkeeping (matched_keywords, updated_at)."""
    out_root = tmp_path / "gen"
    path = generate_bundle(_DUMMY_PAPER, out_root=out_root)
    manifest = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8"))
    manifest["name"] = "Manually polished name"
    manifest["params"]["lookback"] = 60   # human override
    (path / "manifest.yaml").write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    original_generated_at = manifest["source"]["generated_at"]
    # Re-run
    generate_bundle(_DUMMY_PAPER, out_root=out_root)
    redo = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8"))
    assert redo["name"] == "Manually polished name"
    assert redo["params"]["lookback"] == 60
    # source.generated_at preserved; updated_at added
    assert redo["source"]["generated_at"] == original_generated_at
    assert "updated_at" in redo["source"]


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    out_root = tmp_path / "gen"
    path = generate_bundle(_DUMMY_PAPER, out_root=out_root, dry_run=True)
    assert not path.exists()  # no files written


def test_select_recent_papers_filters_by_fetched_at(tmp_path: Path) -> None:
    """select_recent_papers uses the schema we expect on data/papers.db."""
    db = tmp_path / "papers.db"
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE papers (
            source TEXT NOT NULL, source_id TEXT NOT NULL,
            title TEXT, authors TEXT, abstract TEXT,
            published TEXT, updated TEXT, url TEXT, pdf_url TEXT,
            categories TEXT, keywords_hit TEXT, doi TEXT,
            raw_extra TEXT, fetched_at TEXT,
            PRIMARY KEY (source, source_id)
        )
    """)
    rows = [
        ("arxiv", "1", "t1", '["A"]', "ab", None, None, None, None,
         None, None, None, None, "2026-05-25"),
        ("arxiv", "2", "t2", '["B"]', "ab", None, None, None, None,
         None, None, None, None, "2026-05-20"),
    ]
    conn.executemany(
        "INSERT INTO papers VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    conn.close()

    recent = select_recent_papers(db, since="2026-05-22")
    assert len(recent) == 1
    assert recent[0]["source_id"] == "1"
