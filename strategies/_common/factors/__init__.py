"""Causal factor library (lift-ready into ``gs_common.quant.factors``).

Every factor exported here maps a time series to a time series without
look-ahead: the value at ``t`` uses inputs at indices ``<= t``, and every
normaliser is fitted on the sample ending at ``t-1``. Dependencies are limited
to numpy/scipy/pandas so this subpackage can be lifted verbatim, exactly like
``strategies/_common/validation``.
"""
from __future__ import annotations

from .volume import (
    NONCAUSAL_FUNCTIONS,
    DivergenceFlags,
    amihud_illiquidity,
    detrend,
    divergence_flag,
    excess_volume,
    obv,
    obv_slope,
    price_volume_divergence,
    rolling_vwap,
    standardize,
    twap,
    typical_price,
    volume_breakout,
    vwap_deviation,
)

__all__ = [
    "NONCAUSAL_FUNCTIONS",
    "DivergenceFlags",
    "obv",
    "obv_slope",
    "excess_volume",
    "volume_breakout",
    "price_volume_divergence",
    "divergence_flag",
    "typical_price",
    "rolling_vwap",
    "vwap_deviation",
    "twap",
    "amihud_illiquidity",
    "standardize",
    "detrend",
]

# The multiscale (wavelet / MRA) factors are written independently and may not
# be present in every checkout. Import them opportunistically so this package
# stays usable on its own; a missing sibling module is not an error here.
try:  # pragma: no cover - depends on whether multiscale.py has landed
    from . import multiscale as multiscale  # noqa: F401
except ImportError:  # pragma: no cover
    multiscale = None  # type: ignore[assignment]
else:  # pragma: no cover
    __all__.append("multiscale")
