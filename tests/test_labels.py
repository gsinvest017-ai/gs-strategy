"""Tests for the paper_labels store (manual kind override + subcat tags)."""
from __future__ import annotations

from pathlib import Path

import pytest

from quant_crawler.storage.labels import LabelStore


@pytest.fixture
def store(tmp_path: Path) -> LabelStore:
    return LabelStore(tmp_path / "papers.db")


def test_empty_get(store: LabelStore) -> None:
    assert store.get("arxiv", "1") == {"kind_override": None, "manual_subcats": []}


def test_add_and_remove_subcat(store: LabelStore) -> None:
    store.add_subcat("arxiv", "1", "Carry")
    assert store.get("arxiv", "1")["manual_subcats"] == ["carry"]   # lowercased
    store.add_subcat("arxiv", "1", "value")
    assert store.get("arxiv", "1")["manual_subcats"] == ["carry", "value"]
    # idempotent add
    store.add_subcat("arxiv", "1", "value")
    assert store.get("arxiv", "1")["manual_subcats"] == ["carry", "value"]
    store.remove_subcat("arxiv", "1", "carry")
    assert store.get("arxiv", "1")["manual_subcats"] == ["value"]


def test_empty_subcat_rejected(store: LabelStore) -> None:
    with pytest.raises(ValueError):
        store.add_subcat("arxiv", "1", "   ")


def test_set_kind_override(store: LabelStore) -> None:
    store.set_kind("arxiv", "1", "factor")
    assert store.get("arxiv", "1")["kind_override"] == "factor"
    store.set_kind("arxiv", "1", None)   # clear
    assert store.get("arxiv", "1")["kind_override"] is None


def test_set_kind_validates(store: LabelStore) -> None:
    with pytest.raises(ValueError):
        store.set_kind("arxiv", "1", "bogus")


def test_kind_and_subcats_coexist(store: LabelStore) -> None:
    store.add_subcat("arxiv", "1", "macro")
    store.set_kind("arxiv", "1", "factor")
    rec = store.get("arxiv", "1")
    assert rec["kind_override"] == "factor"
    assert rec["manual_subcats"] == ["macro"]


def test_all_labels_bulk(store: LabelStore) -> None:
    store.add_subcat("arxiv", "1", "value")
    store.set_kind("wiley", "2", "strategy")
    alll = store.all_labels()
    assert alll[("arxiv", "1")]["manual_subcats"] == ["value"]
    assert alll[("wiley", "2")]["kind_override"] == "strategy"
