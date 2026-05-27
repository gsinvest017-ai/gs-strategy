"""Tests for the multi-dimensional strategy-category taxonomy."""
from __future__ import annotations

import pytest

from quant_crawler.strategy_gen.taxonomy import (
    ALL_DIMENSIONS,
    DEFAULT_BUNDLE_DIMENSIONS,
    TAG_VOCABULARY,
    extract_tags,
    flat_tags,
)


def test_extract_multi_label_family() -> None:
    paper = {"title": "Trend-following and momentum in managed futures"}
    tags = extract_tags(paper, dimensions=["family"])
    assert "momentum" in tags["family"]
    assert "trend-following" in tags["family"]


def test_extract_signal_dimension() -> None:
    paper = {
        "title": "A cross-sectional momentum study",
        "abstract": "We apply a regime-switching filter and an RSI overlay.",
    }
    sig = extract_tags(paper, dimensions=["signal"])["signal"]
    assert "cross-sectional" in sig
    assert "regime-aware" in sig
    assert "technical" in sig


def test_direction_dimension() -> None:
    assert "long-short" in extract_tags(
        {"title": "A long-short equity strategy"}, dimensions=["direction"]
    )["direction"]
    assert "market-neutral" in extract_tags(
        {"title": "Beta-neutral portfolio"}, dimensions=["direction"]
    )["direction"]


def test_flat_tags_default_dimensions_dedupe_and_order() -> None:
    paper = {
        "title": "Long-short cross-sectional momentum with a regime filter",
        "abstract": "Time-series momentum and trend-following overlay.",
    }
    tags = flat_tags(paper)  # default: family, signal, direction
    # family tags come before signal tags before direction tags
    assert tags.index("momentum") < tags.index("cross-sectional")
    assert tags.index("cross-sectional") < tags.index("long-short")
    # no duplicates
    assert len(tags) == len(set(tags))


def test_flat_tags_empty_when_no_match() -> None:
    paper = {"title": "An unrelated macroeconomics survey", "abstract": ""}
    assert flat_tags(paper) == []


def test_value_requires_qualified_phrase() -> None:
    """Bare 'value' must NOT trigger the value family tag (false-positive guard)."""
    assert "value" not in extract_tags(
        {"title": "The value of liquidity in markets"}, dimensions=["family"]
    ).get("family", [])
    # but a qualified phrase does
    assert "value" in extract_tags(
        {"title": "The value premium revisited"}, dimensions=["family"]
    )["family"]


def test_graph_requires_qualified_phrase() -> None:
    """'neural network' must not be tagged graph-based; 'visibility graph' must."""
    assert "graph-based" not in extract_tags(
        {"title": "A neural network for prices"}, dimensions=["signal"]
    ).get("signal", [])
    assert "graph-based" in extract_tags(
        {"title": "Visibility graph trading"}, dimensions=["signal"]
    )["signal"]


def test_region_not_in_default_bundle_dimensions() -> None:
    """A US-equity paper should NOT leak a 'us' tag into bundle tags."""
    paper = {"title": "Momentum in US equities (S&P 500)"}
    bundle_tags = flat_tags(paper)  # default dims only
    assert "us" not in bundle_tags
    assert "equity" not in bundle_tags
    # …but it IS discoverable when explicitly requested
    region = extract_tags(paper, dimensions=["region"])
    assert "us" in region["region"]


def test_vocabulary_covers_all_emitted_tags() -> None:
    """Every tag any dimension can emit is in TAG_VOCABULARY."""
    samples = [
        "momentum trend-following mean-reversion breakout pairs trading",
        "statistical arbitrage carry value premium factor model volatility",
        "event-driven earnings drift market-making arbitrage",
        "technical fundamental cross-sectional time-series regime markov",
        "machine learning sentiment microstructure visibility graph",
        "long-short market-neutral long-only index futures single-stock",
    ]
    for s in samples:
        for dim, tags in extract_tags({"title": s}).items():
            for t in tags:
                assert t in TAG_VOCABULARY, f"{t} (dim={dim}) missing from vocab"


def test_all_dimensions_present() -> None:
    for d in ("family", "signal", "direction", "instrument", "region", "asset_class"):
        assert d in ALL_DIMENSIONS


def test_default_bundle_dimensions_are_strategy_descriptive() -> None:
    assert DEFAULT_BUNDLE_DIMENSIONS == ("family", "signal", "direction")
