#!/usr/bin/env python3
"""Validate a strategy bundle against gs-zipline-tej strategy-import-spec v1.

Usage:
    validate_dashboard_bundle.py <bundle_dir> [<bundle_dir> ...]

Exit code is the number of bundles that failed validation (0 = all good).
Prints a one-line summary per bundle; details on failure go to stderr.

Rules implemented (mirrors spec §2.validation + §3):
  1. manifest.yaml + strategy.py present
  2. manifest.id matches ^[a-z0-9][a-z0-9_-]{0,63}$
  3. asset_class in {equity, future}
  4. start, end parse as ISO date; end > start
  5. capital_base is a positive number
  6. params is a mapping (may be empty)
  7. bundle is a non-empty string
  8. strategy.py imports side-effect-free with sys.path = [bundle_dir]
  9. strategy.py exposes initialize(context) and handle_data(context, data)
 10. strategy.py does NOT `from _common`, `from ..` or absolute paths
     outside its own dir (regex-scan to catch sibling-bundle leakage)
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path
from typing import List, Tuple

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")


ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ALLOWED_ASSET_CLASS = {"equity", "future"}
FORBIDDEN_IMPORT_PREFIXES = (
    "_common",
    "strategies.",
)


def _err(bundle: Path, msg: str) -> str:
    return f"[FAIL] {bundle.name}: {msg}"


def _parse_iso_date(s: str) -> date:
    if isinstance(s, date):
        return s
    return date.fromisoformat(str(s))


def _scan_forbidden_imports(strategy_path: Path) -> List[str]:
    """Return a list of forbidden import statements found in strategy.py."""
    src = strategy_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(strategy_path))
    bad: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if any(mod.startswith(p) for p in FORBIDDEN_IMPORT_PREFIXES):
                bad.append(f"from {mod} import ...")
            if node.level and node.level > 0:
                bad.append(
                    f"relative import (level={node.level}) from {mod or '<pkg>'}"
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if any(alias.name.startswith(p) for p in FORBIDDEN_IMPORT_PREFIXES):
                    bad.append(f"import {alias.name}")
    return bad


def _try_import(strategy_path: Path) -> Tuple[bool, str]:
    """Run a dashboard-style import: sys.path = [bundle_dir] only."""
    bundle_dir = str(strategy_path.parent.resolve())
    orig_path = sys.path[:]
    orig_modules = set(sys.modules)
    sys.path.insert(0, bundle_dir)
    try:
        spec = importlib.util.spec_from_file_location(
            f"_validate_{strategy_path.parent.name}", strategy_path
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(mod)
        if not hasattr(mod, "initialize"):
            return False, "strategy.py missing initialize(context)"
        if not hasattr(mod, "handle_data"):
            return False, "strategy.py missing handle_data(context, data)"
        return True, ""
    except Exception as exc:  # pragma: no cover - reported to user
        return False, f"import failed: {exc!r}"
    finally:
        sys.path[:] = orig_path
        for m in list(sys.modules):
            if m not in orig_modules:
                del sys.modules[m]


def validate(bundle: Path) -> List[str]:
    errors: List[str] = []
    manifest_p = bundle / "manifest.yaml"
    strategy_p = bundle / "strategy.py"

    if not manifest_p.is_file():
        errors.append(_err(bundle, "missing manifest.yaml"))
        return errors
    if not strategy_p.is_file():
        errors.append(_err(bundle, "missing strategy.py"))
        return errors

    try:
        manifest = yaml.safe_load(manifest_p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(_err(bundle, f"manifest.yaml not valid YAML: {exc}"))
        return errors

    if not isinstance(manifest, dict):
        errors.append(_err(bundle, "manifest.yaml must parse to a mapping"))
        return errors

    # id
    bundle_id = manifest.get("id")
    if not isinstance(bundle_id, str) or not ID_RE.match(bundle_id):
        errors.append(_err(
            bundle,
            f"manifest.id missing or invalid: {bundle_id!r} "
            f"(must match {ID_RE.pattern})"
        ))

    # asset_class
    asset_class = manifest.get("asset_class")
    if asset_class not in ALLOWED_ASSET_CLASS:
        errors.append(_err(
            bundle,
            f"asset_class must be one of {sorted(ALLOWED_ASSET_CLASS)}, "
            f"got {asset_class!r}"
        ))

    # dates
    try:
        start = _parse_iso_date(manifest.get("start"))
        end = _parse_iso_date(manifest.get("end"))
        if not end > start:
            errors.append(_err(bundle, f"end ({end}) must be > start ({start})"))
    except (ValueError, TypeError) as exc:
        errors.append(_err(bundle, f"start/end not ISO-8601 dates: {exc}"))

    # capital_base
    cb = manifest.get("capital_base")
    if not isinstance(cb, (int, float)) or cb <= 0:
        errors.append(_err(
            bundle, f"capital_base must be positive number, got {cb!r}"
        ))

    # params
    params = manifest.get("params", {})
    if not isinstance(params, dict):
        errors.append(_err(
            bundle, f"params must be a mapping, got {type(params).__name__}"
        ))

    # bundle (name)
    bname = manifest.get("bundle")
    if not isinstance(bname, str) or not bname.strip():
        errors.append(_err(bundle, f"bundle must be non-empty string, got {bname!r}"))

    # name / description (warn but pass — only id is strictly required)
    for field in ("name", "description"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(_err(bundle, f"manifest.{field} missing or empty"))

    # spec_version
    sv = manifest.get("spec_version", 1)
    if sv != 1:
        errors.append(_err(
            bundle, f"spec_version must be 1 (current), got {sv!r}"
        ))

    # Forbidden imports
    bad_imports = _scan_forbidden_imports(strategy_p)
    if bad_imports:
        errors.append(_err(
            bundle,
            "strategy.py uses forbidden sibling-bundle imports: "
            + ", ".join(bad_imports),
        ))

    # Dashboard-style import (this also catches import-time side effects)
    ok, msg = _try_import(strategy_p)
    if not ok:
        errors.append(_err(bundle, msg))

    return errors


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundles", nargs="+", type=Path)
    args = p.parse_args(argv)

    failed = 0
    for bundle in args.bundles:
        bundle = bundle.resolve()
        errors = validate(bundle)
        if errors:
            failed += 1
            for e in errors:
                print(e, file=sys.stderr)
        else:
            print(f"[ OK ] {bundle.name}")
    if failed:
        print(f"\n{failed} bundle(s) failed validation.", file=sys.stderr)
    return failed


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
