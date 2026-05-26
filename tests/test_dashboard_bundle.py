"""Tests for the gs-zipline-tej strategy-import-spec compliance layer.

Covers:
1. Every bundle under <repo>/strategies/ (skipping `_common`) passes the
   `scripts/validate_dashboard_bundle.py` validator end-to-end.
2. `scripts/config_to_manifest.py` is idempotent — re-running on an already
   converted bundle leaves manually-edited fields intact.
3. The converter's field-inference rules handle a synthetic minimum config.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_ROOT = REPO_ROOT / "strategies"
SCRIPTS = REPO_ROOT / "scripts"

VALIDATE = SCRIPTS / "validate_dashboard_bundle.py"
CONVERT = SCRIPTS / "config_to_manifest.py"


def _bundles() -> list[Path]:
    bundles = []
    for p in sorted(STRATEGIES_ROOT.iterdir()):
        if not p.is_dir() or p.name.startswith("_"):
            continue
        if (p / "manifest.yaml").is_file():
            bundles.append(p)
    return bundles


BUNDLES = _bundles()


@pytest.mark.parametrize("bundle", BUNDLES, ids=lambda p: p.name)
def test_bundle_passes_validator(bundle: Path) -> None:
    """Every shipped bundle must pass the dashboard-spec validator."""
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(bundle)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        f"validator failed for {bundle.name}:\n"
        f"stdout: {r.stdout}\nstderr: {r.stderr}"
    )


@pytest.mark.parametrize("bundle", BUNDLES, ids=lambda p: p.name)
def test_manifest_has_required_fields(bundle: Path) -> None:
    """Sanity-check manifest schema beyond what the validator enforces."""
    m = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    assert m["id"] == bundle.name, "id should match dir name by convention"
    assert m["asset_class"] in {"equity", "future"}
    assert m["bundle"]
    assert m["start"] < m["end"]
    assert m["capital_base"] > 0
    assert isinstance(m["params"], dict)
    assert isinstance(m["tags"], list) and m["tags"]
    assert isinstance(m["requires_tej_key"], bool)
    assert isinstance(m["extra_deps"], list)
    # source provenance present
    assert "source" in m and m["source"]["kind"] in {"manual", "generated"}


def test_converter_is_idempotent(tmp_path: Path) -> None:
    """Re-running the converter must preserve user-edited fields."""
    bundle = tmp_path / "demo_bundle"
    bundle.mkdir()
    (bundle / "config.yaml").write_text(
        "start: '2020-01-01'\n"
        "end: '2024-12-31'\n"
        "capital_base: 1000000\n"
        "bundle: tquant_future\n"
        "params:\n  root_symbol: TX\n  window: 30\n",
        encoding="utf-8",
    )
    (bundle / "strategy.py").write_text(
        '"""Demo strategy.\n\nReference: arxiv 2605.99999."""\n'
        "def initialize(context):\n    context.params\n\n"
        "def handle_data(context, data):\n    pass\n",
        encoding="utf-8",
    )
    # First run — creates manifest
    r1 = subprocess.run(
        [sys.executable, str(CONVERT), str(bundle)],
        capture_output=True, text=True,
    )
    assert r1.returncode == 0, r1.stderr
    m1 = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    # User edits name + description
    m1["name"] = "Hand-Polished Name"
    m1["description"] = "Bespoke description that must survive a re-run."
    (bundle / "manifest.yaml").write_text(
        yaml.safe_dump(m1, sort_keys=False, allow_unicode=True), encoding="utf-8",
    )
    # Second run — must preserve user edits
    r2 = subprocess.run(
        [sys.executable, str(CONVERT), str(bundle)],
        capture_output=True, text=True,
    )
    assert r2.returncode == 0, r2.stderr
    m2 = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    assert m2["name"] == "Hand-Polished Name"
    assert m2["description"] == "Bespoke description that must survive a re-run."


def test_converter_force_overrides(tmp_path: Path) -> None:
    """--force should rebuild every field from scratch."""
    bundle = tmp_path / "demo_force"
    bundle.mkdir()
    (bundle / "config.yaml").write_text(
        "start: '2020-01-01'\nend: '2024-12-31'\n"
        "capital_base: 1000000\nbundle: tquant_future\n"
        "params: {root_symbol: TX}\n",
        encoding="utf-8",
    )
    (bundle / "strategy.py").write_text(
        '"""S."""\n'
        "def initialize(c):\n    pass\n"
        "def handle_data(c,d):\n    pass\n",
        encoding="utf-8",
    )
    (bundle / "manifest.yaml").write_text(
        "id: demo_force\nname: stale\ndescription: stale\n"
        "asset_class: equity\nbundle: WRONG\nstart: '1999-01-01'\n"
        "end: '2000-01-01'\ncapital_base: 1\nparams: {}\nspec_version: 1\n",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, str(CONVERT), str(bundle), "--force"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    m = yaml.safe_load((bundle / "manifest.yaml").read_text(encoding="utf-8"))
    assert m["bundle"] == "tquant_future"
    assert m["start"] == "2020-01-01"
    assert m["asset_class"] == "future"


def test_no_sibling_imports_in_strategy(tmp_path: Path) -> None:
    """The validator must reject strategies that import _common.*."""
    bundle = tmp_path / "bad_bundle"
    bundle.mkdir()
    (bundle / "config.yaml").write_text(
        "start: '2020-01-01'\nend: '2024-12-31'\n"
        "capital_base: 1000000\nbundle: tquant_future\nparams: {}\n",
        encoding="utf-8",
    )
    (bundle / "strategy.py").write_text(
        '"""bad."""\nfrom _common.futures_setup import apply_taiwan_futures_costs\n'
        "def initialize(c):\n    pass\n"
        "def handle_data(c,d):\n    pass\n",
        encoding="utf-8",
    )
    # Generate a manifest first so other validation rules don't intervene
    subprocess.run(
        [sys.executable, str(CONVERT), str(bundle)],
        capture_output=True, text=True, check=True,
    )
    r = subprocess.run(
        [sys.executable, str(VALIDATE), str(bundle)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0
    assert "forbidden sibling-bundle imports" in r.stderr
