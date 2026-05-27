"""Tests for the strategy/factor paper classifier."""
from __future__ import annotations

import pytest

from quant_crawler import paper_class as pc


@pytest.mark.parametrize("title,abstract,expected", [
    ("The value premium and size factor in cross-sectional returns",
     "We study factor models and risk premia.", "factor"),
    ("A factor zoo: replicating anomalies", "", "factor"),
    ("Betting against beta across markets", "", "factor"),
    ("Fama-French five-factor model revisited", "", "factor"),
    # strategy-leaning
    ("A trend-following trading strategy with backtest", "", "strategy"),
    ("Pairs trading via cointegration: execution and signals", "", "strategy"),
    ("Market making in the limit order book", "", "strategy"),
    ("Visibility graphs can make money: a technical trading rule", "", "strategy"),
])
def test_classify_kind(title, abstract, expected):
    r = pc.classify_kind({"title": title, "abstract": abstract})
    assert r.kind == expected


def test_kind_tie_defaults_to_strategy():
    # No factor/strategy keywords at all -> default strategy.
    r = pc.classify_kind({"title": "On the geometry of returns", "abstract": ""})
    assert r.kind == "strategy"
    assert r.factor_score == 0 and r.strategy_score == 0


def test_kind_factor_wins_only_when_strictly_greater():
    # Equal scores -> strategy.
    paper = {"title": "factor model trading strategy"}  # 1 factor, 1 strategy-ish
    r = pc.classify_kind(paper)
    # "factor model" = factor 2 (factors + factor model); "trading strategy" = 1
    # -> factor strictly greater -> factor
    assert r.kind == "factor"


def test_factor_subcategories():
    paper = {"title": "Value and momentum everywhere",
             "abstract": "We examine the value premium, the momentum factor, and the quality premium."}
    subs = pc.subcategories(paper, "factor")
    assert "value" in subs
    assert "momentum" in subs
    assert "quality" in subs   # requires qualified phrase ('quality premium')


def test_strategy_subcategories():
    paper = {"title": "A mean-reversion and breakout trading system",
             "abstract": "RSI technical indicator with statistical arbitrage overlay."}
    subs = pc.subcategories(paper, "strategy")
    assert "mean-reversion" in subs
    assert "breakout" in subs
    assert "technical" in subs
    assert "statistical-arbitrage" in subs


def test_subcategories_are_kind_specific():
    paper = {"title": "value premium", "abstract": ""}
    # asking for strategy subcats on a factor paper yields no value tag
    assert "value" not in pc.subcategories(paper, "strategy")
    assert "value" in pc.subcategories(paper, "factor")


def test_classify_one_shot():
    out = pc.classify({"title": "The quality factor and low-volatility anomaly"})
    assert out["kind"] == "factor"
    assert "quality" in out["subcats"]
    assert "low-volatility" in out["subcats"]
    assert out["factor_score"] >= 1


def test_subcat_vocabulary():
    assert "value" in pc.subcat_vocabulary("factor")
    assert "trend-following" in pc.subcat_vocabulary("strategy")
    assert pc.subcat_vocabulary("factor") == pc.FACTOR_SUBCAT_NAMES


def test_subcat_names_unique():
    assert len(set(pc.FACTOR_SUBCAT_NAMES)) == len(pc.FACTOR_SUBCAT_NAMES)
    assert len(set(pc.STRATEGY_SUBCAT_NAMES)) == len(pc.STRATEGY_SUBCAT_NAMES)
