#!/usr/bin/env python3
"""Convert a legacy `config.yaml` to a dashboard-spec `manifest.yaml`.

Usage:
    config_to_manifest.py <bundle_dir> [<bundle_dir> ...]
    config_to_manifest.py --all              # scans <repo>/strategies/

The converter is intentionally idempotent: re-running on an already-converted
bundle preserves any manually-edited manifest fields it can't infer from
config.yaml (name, description, source.* …). It only fills in MISSING fields.

Field inference rules (see docs/progress-strategy-import-spec.md §"設計決策"):

| manifest field      | source                                              |
|---------------------|-----------------------------------------------------|
| id                  | bundle dir name                                     |
| name                | strategy.py first docstring line, or README h1      |
| description         | strategy.py docstring first paragraph               |
| asset_class         | bundle starts with `tquant_future` -> future        |
| bundle/start/end/.. | copied from config.yaml                             |
| capital_base        | copied                                              |
| params              | copied verbatim                                     |
| tags                | derived from id + signal heuristics                 |
| requires_tej_key    | bundle starts with `tquant` -> true                 |
| extra_deps          | AST-scan strategy.py imports, minus allow-list      |
| symbols             | from params.roots / root_symbol / universe_roots    |
| source.kind         | `manual` unless --generated is passed               |
| source.inputs.paper | scrape `arxiv NNNN.NNNNN` from docstring            |

This script is dependency-light (PyYAML only) so it can run inside the crawler
venv without pulling zipline.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGIES_ROOT = REPO_ROOT / "strategies"

PAPER_RE = re.compile(r"arxiv\s+(\d{4}\.\d{4,5})", re.IGNORECASE)
DOI_RE = re.compile(r"doi[:\s]+(10\.\d{4,9}/[\w./;()\-]+)", re.IGNORECASE)
WILEY_RE = re.compile(r"wiley[\s_/]+([a-zA-Z]+\.\d+)", re.IGNORECASE)

# stdlib + zipline + standard scientific stack: NEVER list these in extra_deps
ALLOW_LIST_IMPORT_ROOTS = {
    "numpy", "pandas", "scipy", "yaml", "zipline",
    "math", "os", "sys", "re", "datetime", "typing",
    "collections", "itertools", "functools", "pathlib", "json",
    "warnings", "dataclasses", "enum", "logging", "abc",
    "__future__",
    # crawler/test helpers (still pip-installed in the venv; safe to omit)
    "matplotlib", "tqdm", "pytest",
}


def _strategy_py(bundle: Path) -> Optional[Path]:
    p = bundle / "strategy.py"
    return p if p.is_file() else None


def _extract_docstring(strategy_path: Path) -> str:
    src = strategy_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(strategy_path))
    except SyntaxError:
        return ""
    return ast.get_docstring(tree) or ""


def _infer_name(bundle: Path, docstring: str) -> str:
    """First non-empty line of strategy.py docstring; fallback to dir name."""
    for line in docstring.splitlines():
        line = line.strip()
        if line:
            return line
    return bundle.name.replace("_", " ").title()


def _infer_description(docstring: str) -> str:
    """First paragraph (until blank line) of the docstring."""
    paras: List[str] = []
    buf: List[str] = []
    for line in docstring.splitlines():
        if line.strip():
            buf.append(line.strip())
        elif buf:
            paras.append(" ".join(buf))
            buf = []
            if paras:
                break
    if buf and not paras:
        paras.append(" ".join(buf))
    return paras[0] if paras else ""


def _infer_asset_class(bundle_name: str) -> str:
    if "future" in bundle_name.lower() or "txf" in bundle_name.lower():
        return "future"
    return "equity"


def _infer_tags(bundle_id: str, params: Dict[str, Any]) -> List[str]:
    tags = ["taiwan"]
    bid = bundle_id.lower()
    if "tx" in bid or "mtx" in bid or "stkfut" in bid or "future" in bid:
        tags.append("futures")
    if "momentum" in bid or "mom" in bid or "tsmom" in bid or "xsmom" in bid:
        tags.append("momentum")
    if "rsi" in bid or "vgrsi" in bid:
        tags.append("technical")
    if "cubic" in bid:
        tags.append("nonlinear")
    if "rmt" in bid:
        tags.append("regime")
    # always tag paper-derived
    tags.append("paper")
    # dedupe preserving order
    seen: Dict[str, None] = {}
    return [t for t in tags if not (t in seen or seen.update({t: None}))]


def _infer_requires_tej_key(bundle_name: str) -> bool:
    return bundle_name.startswith("tquant") or bundle_name.startswith("morning_")


def _infer_extra_deps(strategy_path: Path) -> List[str]:
    """AST-scan top-level imports; return whatever is not in ALLOW_LIST."""
    src = strategy_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(strategy_path))
    except SyntaxError:
        return []
    deps: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root and root not in ALLOW_LIST_IMPORT_ROOTS and root not in deps:
                    deps.append(root)
            continue
        else:
            continue
        if root and root not in ALLOW_LIST_IMPORT_ROOTS and root not in deps:
            deps.append(root)
    # filter out sibling-bundle-style imports (they're a violation — we'll
    # report them but not list them as extra_deps)
    return [d for d in deps if d != "_common" and not d.startswith("strategies")]


def _infer_symbols(params: Dict[str, Any]) -> List[str]:
    syms: List[str] = []
    for key in ("root_symbol", "roots", "universe_roots"):
        v = params.get(key)
        if isinstance(v, str):
            syms.append(v)
        elif isinstance(v, list):
            syms.extend(str(x) for x in v)
    # dedupe preserving order
    seen: Dict[str, None] = {}
    return [s for s in syms if not (s in seen or seen.update({s: None}))]


def _infer_source(docstring: str, generated: bool) -> Dict[str, Any]:
    src: Dict[str, Any] = {"kind": "generated" if generated else "manual"}
    m_arx = PAPER_RE.search(docstring)
    m_doi = DOI_RE.search(docstring)
    m_wil = WILEY_RE.search(docstring)
    paper: Dict[str, Any] = {}
    if m_arx:
        paper["arxiv"] = m_arx.group(1)
    if m_doi:
        paper["doi"] = m_doi.group(1)
    if m_wil:
        paper["ref"] = m_wil.group(0)
    if paper:
        src["inputs"] = {"paper": paper}
    return src


def _merge_preserving(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """Use existing values where present, fill in new values for the rest."""
    out = dict(new)
    for k, v in existing.items():
        out[k] = v   # caller already merged user edits
    return out


def convert_bundle(bundle: Path, generated: bool = False, force: bool = False) -> Dict[str, Any]:
    config_p = bundle / "config.yaml"
    manifest_p = bundle / "manifest.yaml"
    strategy_p = _strategy_py(bundle)
    if not config_p.is_file():
        raise FileNotFoundError(f"no config.yaml in {bundle}")
    if strategy_p is None:
        raise FileNotFoundError(f"no strategy.py in {bundle}")

    cfg = yaml.safe_load(config_p.read_text(encoding="utf-8")) or {}
    if not isinstance(cfg, dict):
        raise ValueError(f"{config_p} did not parse to a mapping")

    docstring = _extract_docstring(strategy_p)
    params = cfg.get("params", {}) or {}

    new: Dict[str, Any] = {
        "id": bundle.name,
        "name": _infer_name(bundle, docstring),
        "description": _infer_description(docstring),
        "asset_class": _infer_asset_class(cfg.get("bundle", "")),
        "bundle": cfg["bundle"],
        "start": str(cfg["start"]),
        "end": str(cfg["end"]),
        "capital_base": cfg["capital_base"],
        "params": params,
        "tags": _infer_tags(bundle.name, params),
        "requires_tej_key": _infer_requires_tej_key(cfg.get("bundle", "")),
        "extra_deps": _infer_extra_deps(strategy_p),
        "symbols": _infer_symbols(params),
        "spec_version": 1,
    }
    if "calendar" in cfg:
        new["calendar"] = cfg["calendar"]
    if "data_frequency" in cfg:
        new["data_frequency"] = cfg["data_frequency"]

    source_block = _infer_source(docstring, generated)
    source_block.setdefault(
        "generated_at",
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    new["source"] = source_block

    # Idempotent merge: keep user edits in existing manifest unless --force
    if manifest_p.is_file() and not force:
        existing = yaml.safe_load(manifest_p.read_text(encoding="utf-8")) or {}
        # preserve user-edited top-level scalars + nested params
        for k, v in existing.items():
            new[k] = v

    return new


def write_manifest(bundle: Path, manifest: Dict[str, Any], dry_run: bool) -> None:
    manifest_p = bundle / "manifest.yaml"
    text = yaml.safe_dump(
        manifest, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    if dry_run:
        print(f"--- {manifest_p} (dry run) ---")
        print(text)
        return
    manifest_p.write_text(text, encoding="utf-8")
    print(f"wrote {manifest_p}")


def discover_all() -> List[Path]:
    bundles = []
    for p in sorted(STRATEGIES_ROOT.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("_"):
            continue
        if (p / "config.yaml").is_file():
            bundles.append(p)
    return bundles


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundles", nargs="*", type=Path)
    p.add_argument("--all", action="store_true",
                   help="scan <repo>/strategies/ for every dir with config.yaml")
    p.add_argument("--generated", action="store_true",
                   help="set source.kind=generated (default: manual)")
    p.add_argument("--force", action="store_true",
                   help="overwrite all manifest fields, ignore existing edits")
    p.add_argument("--dry-run", action="store_true",
                   help="print YAML to stdout instead of writing")
    args = p.parse_args(argv)

    if args.all and args.bundles:
        sys.exit("--all is mutually exclusive with explicit bundle paths")
    targets = discover_all() if args.all else [b.resolve() for b in args.bundles]
    if not targets:
        sys.exit("no bundles specified (pass paths or --all)")

    for bundle in targets:
        try:
            manifest = convert_bundle(bundle, generated=args.generated, force=args.force)
        except Exception as exc:
            print(f"[error] {bundle.name}: {exc}", file=sys.stderr)
            continue
        write_manifest(bundle, manifest, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
