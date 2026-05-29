#!/usr/bin/env python3
"""Validator + generator for autogo-compatible test plans.

Mirrors autogo's `_is_plan_file()` filter so this repo can self-verify before
the dashboard tries to import. Pure stdlib — no extra deps.

Usage:
    test_plan_format.py validate <path> [<path>...]   # one or more files
    test_plan_format.py validate --all                # every *.md in test-plans/
    test_plan_format.py list                          # show all plans + status
    test_plan_format.py new [<id>] [--title T] [--runner R] [--tags a,b]

Exit codes:
    0  all good
    1  at least one file failed validation
    2  bad CLI usage
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_PLANS_DIR = REPO_ROOT / "test-plans"
FRONTMATTER_HEAD_LIMIT = 2048      # autogo reads first 2 KB only
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")

KNOWN_RUNNERS = {"playwright-mcp", "playwright-traced", "chrome-devtools-mcp"}


# --------------------------------------------------------------------------
# Frontmatter parser (autogo-compatible)
# --------------------------------------------------------------------------

@dataclass
class ParseResult:
    path: Path
    ok: bool
    reasons: List[str] = field(default_factory=list)
    frontmatter: Dict[str, str] = field(default_factory=dict)
    body: str = ""

    def add(self, msg: str) -> None:
        self.ok = False
        self.reasons.append(msg)


def _strip_bom(text: str) -> str:
    return text.lstrip("﻿")


def _read_head(path: Path) -> str:
    try:
        raw = path.read_bytes()[:FRONTMATTER_HEAD_LIMIT]
    except OSError as e:
        return ""
    try:
        return _strip_bom(raw.decode("utf-8", errors="replace"))
    except Exception:
        return ""


def parse_plan(path: Path) -> ParseResult:
    """Mirror autogo's _is_plan_file(): first 2 KB starts with `---`,
    contains a frontmatter block ending in `---`, and that block has
    `id` AND (`title` OR `runner`)."""
    r = ParseResult(path=path, ok=True)
    head = _read_head(path)
    if not head:
        r.add("empty or unreadable")
        return r
    if not head.lstrip().startswith("---"):
        r.add("file does not start with `---` frontmatter")
        return r

    m = _FRONTMATTER_RE.match(head.lstrip("\n"))
    if not m:
        r.add("no closing `---` for frontmatter (within first 2 KB)")
        return r

    fm_text = m.group(1)
    for ln_no, line in enumerate(fm_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        km = _KEY_RE.match(stripped)
        if not km:
            r.add(f"frontmatter line {ln_no} is not `key: value`: {stripped!r}")
            continue
        key, value = km.group(1), km.group(2).strip()
        # quotes are optional in autogo's hand-rolled parser
        if (len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}):
            value = value[1:-1]
        r.frontmatter[key] = value

    # body (after frontmatter close) — keep full file
    try:
        full = path.read_text(encoding="utf-8", errors="replace")
        full = _strip_bom(full)
        bm = _FRONTMATTER_RE.match(full.lstrip("\n"))
        if bm:
            r.body = full[bm.end():]
    except OSError:
        pass

    # autogo's gates
    fm = r.frontmatter
    if "id" not in fm:
        r.add("missing required `id:`")
    if "id_skip" in fm and "id" not in fm:
        r.add("file uses `id_skip:` — intentionally skipped by autogo")
    if "title" not in fm and "runner" not in fm:
        r.add("missing both `title:` AND `runner:` — need at least one")

    return r


# --------------------------------------------------------------------------
# Discovery (matches autogo skip rules)
# --------------------------------------------------------------------------

def _is_skip_filename(path: Path) -> bool:
    name = path.name
    if name.startswith("."):       # dotfile
        return True
    if name.lower() == "readme.md":
        return True
    return False


def discover_plans(root: Path = TEST_PLANS_DIR) -> List[Path]:
    """Return candidate `.md` files; mirrors autogo's discovery order:
    prefer `test-plans/*.md`, else fallback to repo root `*.md`."""
    if root.is_dir():
        return sorted(p for p in root.glob("*.md") if not _is_skip_filename(p))
    # fallback: repo root *.md
    return sorted(
        p for p in REPO_ROOT.glob("*.md") if not _is_skip_filename(p)
    )


# --------------------------------------------------------------------------
# Pretty-print
# --------------------------------------------------------------------------

def _fmt_result(r: ParseResult) -> str:
    try:
        rel = r.path.relative_to(REPO_ROOT) if r.path.is_absolute() else r.path
    except ValueError:
        rel = r.path
    if r.ok:
        fm = r.frontmatter
        bits = [f"id={fm.get('id','?')}"]
        if "title" in fm: bits.append(f"title={fm['title'][:30]!r}")
        if "runner" in fm: bits.append(f"runner={fm['runner']}")
        return f"[OK] {rel}  {' '.join(bits)}"
    return f"[FAIL] {rel}\n        - " + "\n        - ".join(r.reasons)


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_validate(args: argparse.Namespace) -> int:
    paths: List[Path] = []
    if args.all:
        paths = discover_plans()
        if not paths:
            print(f"(no .md files under {TEST_PLANS_DIR.relative_to(REPO_ROOT)}/)")
            return 0
    else:
        paths = [Path(p).resolve() for p in args.paths]
        if not paths:
            print("usage: test_plan_format.py validate <path>... | --all", file=sys.stderr)
            return 2
    failed = 0
    for p in paths:
        r = parse_plan(p)
        print(_fmt_result(r))
        if not r.ok:
            failed += 1
    if failed:
        print(f"\n{failed} of {len(paths)} file(s) failed.", file=sys.stderr)
    return 1 if failed else 0


def cmd_list(args: argparse.Namespace) -> int:
    paths = discover_plans()
    if not paths:
        print(f"(no .md files under {TEST_PLANS_DIR.relative_to(REPO_ROOT)}/)")
        return 0
    for p in paths:
        r = parse_plan(p)
        print(_fmt_result(r))
    return 0


_FUZZY_TEMPLATE = """\
---
id: {id}
title: {title}
runner: {runner}
created: {created}
tags: [{tags}]
estimated_seconds: 60
---

## 我想知道

（這裡寫一段給 Claude 看的自然語言：想驗什麼、想看什麼，越具體越好；
不必寫步驟，agent 會自己用 mcp__playwright__* 決定怎麼跑。）

## 提示（可選）

- ...
"""


def cmd_new(args: argparse.Namespace) -> int:
    bundle_id = args.id or (input("id (e.g. 003-my-plan): ").strip() or None)
    if not bundle_id:
        print("id required", file=sys.stderr); return 2
    title = args.title or (input("title: ").strip() or bundle_id)
    runner = args.runner or "playwright-mcp"
    if runner not in KNOWN_RUNNERS:
        print(f"warning: unknown runner {runner!r}; known: "
              f"{sorted(KNOWN_RUNNERS)}", file=sys.stderr)
    tags = args.tags or ""

    TEST_PLANS_DIR.mkdir(parents=True, exist_ok=True)
    out = TEST_PLANS_DIR / f"{bundle_id}.md"
    if out.exists() and not args.force:
        print(f"refusing to overwrite {out} (use --force)", file=sys.stderr)
        return 2
    text = _FUZZY_TEMPLATE.format(
        id=bundle_id, title=title, runner=runner,
        created=date.today().isoformat(), tags=tags,
    )
    out.write_text(text, encoding="utf-8")
    try:
        shown = out.relative_to(REPO_ROOT)
    except ValueError:
        shown = out
    print(f"wrote {shown}")
    r = parse_plan(out)
    print(_fmt_result(r))
    return 0 if r.ok else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="test_plan_format", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    pv = sub.add_parser("validate", help="validate one or more plan files")
    pv.add_argument("paths", nargs="*")
    pv.add_argument("--all", action="store_true",
                    help=f"validate every .md under {TEST_PLANS_DIR.relative_to(REPO_ROOT)}/")
    pv.set_defaults(func=cmd_validate)

    pl = sub.add_parser("list", help="list all plans + status")
    pl.set_defaults(func=cmd_list)

    pn = sub.add_parser("new", help="create a new fuzzy plan stub")
    pn.add_argument("id", nargs="?")
    pn.add_argument("--title")
    pn.add_argument("--runner", default="playwright-mcp")
    pn.add_argument("--tags", help="comma-separated, e.g. demo,smoke")
    pn.add_argument("--force", action="store_true",
                    help="overwrite if file exists")
    pn.set_defaults(func=cmd_new)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
