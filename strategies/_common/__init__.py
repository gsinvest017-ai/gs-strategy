"""Shared helpers for Zipline-TEJ x TQuant-Lab Taiwan futures strategies.

Imports here are **lazy** (PEP 562). ``futures_setup`` and ``runner`` both pull
in ``zipline``, and importing zipline is not free: ``exchange_calendars``
resolves the TEJ trading calendar at module-import time, which fires a live
``tejapi`` request and raises ``AuthenticationError`` without a valid
``TEJAPI_KEY``.

Eagerly re-exporting them therefore made every submodule of this package
zipline-dependent by association -- including the two that deliberately are
not: ``validation`` (numpy/scipy/pandas only, documented as lift-ready into
``gs_common.quant.validation``) and ``quantdata`` (pandas only). That in turn
made ``pytest tests/`` abort during *collection* on any machine without a TEJ
key, which is every CI runner.

The public API is unchanged -- ``from strategies._common import
run_strategy_from_config`` still works -- it just doesn't happen until someone
actually asks for one of those names.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

_LAZY_EXPORTS = {
    "apply_taiwan_futures_costs": ".futures_setup",
    "make_continuous_taiwan_futures": ".futures_setup",
    "make_roll_futures_handler": ".futures_setup",
    "load_config": ".runner",
    "run_strategy_from_config": ".runner",
}

__all__ = list(_LAZY_EXPORTS)

if TYPE_CHECKING:  # pragma: no cover - for type checkers / IDEs only
    from .futures_setup import (
        apply_taiwan_futures_costs,
        make_continuous_taiwan_futures,
        make_roll_futures_handler,
    )
    from .runner import load_config, run_strategy_from_config


def __getattr__(name: str):
    """Resolve a re-exported name on first access (PEP 562)."""
    module_name = _LAZY_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(module_name, __name__), name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_EXPORTS))
