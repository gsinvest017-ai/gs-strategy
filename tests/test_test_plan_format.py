"""Tests for scripts/test_plan_format.py — autogo-compatible plan validator.

Mirrors autogo's `_is_plan_file()` filter to catch malformed plans BEFORE
the dashboard tries to import them.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "test_plan_format.py"


@pytest.fixture(scope="module")
def fmt():
    """Load scripts/test_plan_format.py as a module."""
    spec = importlib.util.spec_from_file_location("_tpf", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_tpf"] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Skip-filename rules (mirror autogo: README.md lowercase + dotfiles)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name,skipped", [
    ("README.md", True),
    ("readme.md", True),
    ("Readme.md", True),
    (".hidden.md", True),
    (".eslintrc.md", True),
    ("001-smoke.md", False),
    ("CLAUDE.md", False),         # not readme — won't be skipped by name,
                                  # only by lack of frontmatter
])
def test_skip_filename_rules(fmt, name, skipped):
    p = Path("/tmp") / name
    assert fmt._is_skip_filename(p) is skipped


# --------------------------------------------------------------------------
# Happy path: real shipped plans pass
# --------------------------------------------------------------------------

def test_real_plans_all_pass(fmt):
    plans = fmt.discover_plans()
    assert plans, "expected at least one .md under test-plans/"
    for p in plans:
        r = fmt.parse_plan(p)
        assert r.ok, f"{p.name} should validate, reasons={r.reasons}"


# --------------------------------------------------------------------------
# Frontmatter parse — required fields
# --------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def test_missing_id_fails(fmt, tmp_path):
    p = _write(tmp_path, "x.md",
               "---\ntitle: hi\nrunner: playwright-mcp\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert not r.ok
    assert any("missing required `id:`" in m for m in r.reasons)


def test_missing_title_and_runner_fails(fmt, tmp_path):
    p = _write(tmp_path, "x.md", "---\nid: foo\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert not r.ok
    assert any("title" in m and "runner" in m for m in r.reasons)


def test_id_with_title_only_ok(fmt, tmp_path):
    p = _write(tmp_path, "x.md", "---\nid: foo\ntitle: hi\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert r.ok, r.reasons


def test_id_with_runner_only_ok(fmt, tmp_path):
    p = _write(tmp_path, "x.md",
               "---\nid: foo\nrunner: playwright-mcp\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert r.ok, r.reasons


# --------------------------------------------------------------------------
# Edge cases that autogo's hand-rolled parser cares about
# --------------------------------------------------------------------------

def test_no_frontmatter_fails(fmt, tmp_path):
    p = _write(tmp_path, "x.md", "# just a regular doc\n\nno fm here.\n")
    r = fmt.parse_plan(p)
    assert not r.ok
    assert any("frontmatter" in m for m in r.reasons)


def test_unclosed_frontmatter_fails(fmt, tmp_path):
    p = _write(tmp_path, "x.md", "---\nid: foo\ntitle: hi\n\n(no closing)\n")
    r = fmt.parse_plan(p)
    assert not r.ok
    assert any("closing" in m for m in r.reasons)


def test_bom_at_start_is_tolerated(fmt, tmp_path):
    p = tmp_path / "x.md"
    p.write_bytes("﻿---\nid: foo\ntitle: hi\n---\n\nbody\n".encode("utf-8"))
    r = fmt.parse_plan(p)
    assert r.ok, r.reasons


def test_inline_array_tags_captured(fmt, tmp_path):
    p = _write(tmp_path, "x.md",
               "---\nid: foo\ntitle: hi\ntags: [demo, smoke]\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert r.ok
    assert r.frontmatter["tags"] == "[demo, smoke]"


def test_quoted_values_unquoted(fmt, tmp_path):
    p = _write(tmp_path, "x.md",
               "---\nid: foo\ntitle: \"a quoted title\"\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert r.ok
    assert r.frontmatter["title"] == "a quoted title"


def test_body_captured_after_frontmatter(fmt, tmp_path):
    p = _write(tmp_path, "x.md",
               "---\nid: foo\ntitle: hi\n---\n\n## H\nbody text\n")
    r = fmt.parse_plan(p)
    assert "body text" in r.body


def test_frontmatter_must_be_in_first_2kb(fmt, tmp_path):
    """If frontmatter is pushed past the 2KB head window it's not detected."""
    p = _write(tmp_path, "x.md",
               "x" * 2100 + "\n---\nid: foo\ntitle: hi\n---\n\nbody\n")
    r = fmt.parse_plan(p)
    assert not r.ok


# --------------------------------------------------------------------------
# `new` command — generates a valid stub
# --------------------------------------------------------------------------

def test_new_generates_valid_plan(fmt, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fmt, "TEST_PLANS_DIR", tmp_path)
    import argparse
    ns = argparse.Namespace(
        id="099-temp", title="temp plan", runner="playwright-mcp",
        tags="demo,smoke", force=False,
    )
    rc = fmt.cmd_new(ns)
    assert rc == 0
    out = tmp_path / "099-temp.md"
    assert out.is_file()
    r = fmt.parse_plan(out)
    assert r.ok, r.reasons
    assert r.frontmatter["id"] == "099-temp"
    assert r.frontmatter["runner"] == "playwright-mcp"


def test_new_refuses_overwrite_without_force(fmt, tmp_path, monkeypatch):
    monkeypatch.setattr(fmt, "TEST_PLANS_DIR", tmp_path)
    (tmp_path / "x.md").write_text("existing", encoding="utf-8")
    import argparse
    ns = argparse.Namespace(id="x", title="t", runner="playwright-mcp",
                            tags="", force=False)
    rc = fmt.cmd_new(ns)
    assert rc == 2     # refused (no --force)
    assert (tmp_path / "x.md").read_text() == "existing"


# --------------------------------------------------------------------------
# `validate --all` exit codes via subprocess (CLI smoke)
# --------------------------------------------------------------------------

def test_cli_validate_all_passes_real_plans():
    import subprocess
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", "--all"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert "[OK]" in r.stdout
    assert "[FAIL]" not in r.stdout


def test_cli_validate_failing_file_exits_1(tmp_path):
    import subprocess
    bad = tmp_path / "bad.md"
    bad.write_text("---\ntitle: only title\n---\nbody\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "validate", str(bad)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "[FAIL]" in r.stdout
