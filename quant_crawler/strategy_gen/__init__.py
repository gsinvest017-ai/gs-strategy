"""Rule-based paper -> strategy-bundle skeleton generator.

See ``docs/progress-daily-strategy-gen.md`` for the scope contract: this
package emits *skeleton* bundles that pass the dashboard import spec and
carry paper provenance, but their strategy.py is a no-trade placeholder
until a human fills in the signal logic.
"""
from .classify import TEMPLATES, classify_paper
from .generate import generate_bundle, paper_slug

__all__ = ["TEMPLATES", "classify_paper", "generate_bundle", "paper_slug"]
