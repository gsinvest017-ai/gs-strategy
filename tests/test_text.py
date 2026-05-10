from quant_crawler.utils.text import is_relevant, normalize_text, relevance_hits, stable_hash


def test_is_relevant_hits_keywords():
    assert is_relevant("Managed futures and trend following", "")
    assert is_relevant("", "Term-structure carry in commodity futures markets")
    assert is_relevant("statistical arbitrage in oil futures", "")


def test_is_relevant_misses_unrelated():
    assert not is_relevant("Childhood education in rural villages", "About school policy")


def test_relevance_hits_dedupes_and_lowercases():
    hits = relevance_hits(
        "Momentum and carry in futures", "Carry strategies in futures markets are known"
    )
    assert "carry" in hits
    assert "momentum" in hits
    assert any("futures" in h for h in hits)


def test_normalize_text_strips_and_unicode():
    assert normalize_text("  hello   world  ") == "hello world"


def test_stable_hash_deterministic():
    assert stable_hash("a", "b") == stable_hash("a", "b")
    assert stable_hash("a", "b") != stable_hash("b", "a")
