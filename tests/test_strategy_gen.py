"""Tests for the quant_crawler.strategy_gen pipeline.

Covers classification rules and (in M3+) the jinja generator + idempotency.
"""
from __future__ import annotations

import pytest

from quant_crawler.strategy_gen.classify import (
    TEMPLATES,
    classify_paper,
)


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
