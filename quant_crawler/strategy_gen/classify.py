"""Keyword-based classification of crawled papers into strategy templates.

Public API:
    classify_paper(paper) -> ClassificationResult
        paper: dict with at least {title, abstract, keywords_hit, categories}
        returns (template_name, default_params, matched_keywords)

The classifier is intentionally simple — a curated keyword vocabulary per
template, applied in priority order (most specific first). This is enough
to seed dashboard bundles; refining the signal logic is human work.

Adding a new template:
    1. Append to TEMPLATES (preserving priority order)
    2. Add the corresponding strategy_<name>.py.j2 in templates/
    3. (Optional) Bump test fixtures in tests/test_strategy_gen.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple


@dataclass(frozen=True)
class TemplateSpec:
    """One classifier bucket + its template metadata."""
    name: str                          # template id, matches templates/strategy_<name>.py.j2
    description: str                   # one-liner shown in manifest
    keyword_patterns: Tuple[str, ...]  # case-insensitive regex alternation
    default_params: Mapping[str, Any] = field(default_factory=dict)
    tags: Tuple[str, ...] = ()


# IMPORTANT: order matters — first match wins. Place specific buckets before
# catch-alls (buy_and_hold is the final fallback).
TEMPLATES: Tuple[TemplateSpec, ...] = (
    TemplateSpec(
        name="momentum",
        description=(
            "Time-series / cross-sectional momentum skeleton. 12-1 lookback "
            "default. Replace _generate_signal() with the paper's actual "
            "score formula before deploying."
        ),
        keyword_patterns=(
            r"\bmomentum\b",
            r"\btime[- ]?series\s+momentum\b",
            r"\bcross[- ]?sectional\s+momentum\b",
            r"\btrend[- ]?following\b",
            r"\btsmom\b",
            r"\bxsmom\b",
            r"\bcta\b",
            r"\bbreakout\b",
        ),
        default_params={
            "root_symbol": "TX",
            "lookback": 252,
            "skip": 21,
            "allow_short": True,
            "position_contracts": 1,
            "days_before_close": 10,
            "per_contract_cost": {"TX": 150, "MTX": 60},
            "spread_points": 6.0,
        },
        tags=("momentum",),
    ),
    TemplateSpec(
        name="mean_reversion",
        description=(
            "Mean-reversion / oscillator skeleton (RSI 30/70 by default). "
            "Replace the threshold logic with the paper's specific "
            "indicator before deploying."
        ),
        keyword_patterns=(
            r"\bmean[- ]?reversion\b",
            r"\breversal\b",
            r"\bcontrarian\b",
            r"\brsi\b",
            r"\boscillator\b",
            r"\bovershoot\b",
            r"\bover[- ]?bought\b",
            r"\bover[- ]?sold\b",
            r"\bpairs\s+trad",
            r"\bstatistical\s+arbitrage\b",
            r"\bstat[- ]?arb\b",
            r"\bcointegrat",
        ),
        default_params={
            "root_symbol": "TX",
            "window": 14,
            "upper_threshold": 70.0,
            "lower_threshold": 30.0,
            "allow_short": True,
            "position_contracts": 1,
            "days_before_close": 10,
            "per_contract_cost": {"TX": 150, "MTX": 60},
            "spread_points": 6.0,
        },
        tags=("mean-reversion", "technical"),
    ),
    TemplateSpec(
        name="buy_and_hold",
        description=(
            "Buy-and-hold fallback skeleton — used when the paper does NOT "
            "match any signal-driven template. The strategy holds a single "
            "fixed position; tweak before treating as a real strategy."
        ),
        keyword_patterns=(),  # matches everything via the fallback path
        default_params={
            "root_symbol": "TX",
            "position_contracts": 1,
            "days_before_close": 10,
            "per_contract_cost": {"TX": 150, "MTX": 60},
            "spread_points": 6.0,
        },
        tags=("baseline", "buy-and-hold"),
    ),
)


@dataclass(frozen=True)
class ClassificationResult:
    template: str
    default_params: Mapping[str, Any]
    matched_keywords: Tuple[str, ...]
    tags: Tuple[str, ...]

    @property
    def is_fallback(self) -> bool:
        return self.template == "buy_and_hold" and not self.matched_keywords


def _haystack(paper: Mapping[str, Any]) -> str:
    parts: List[str] = []
    for key in ("title", "abstract", "keywords_hit", "categories"):
        v = paper.get(key)
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            parts.extend(str(x) for x in v)
        else:
            parts.append(str(v))
    return " \n ".join(parts).lower()


def classify_paper(paper: Mapping[str, Any]) -> ClassificationResult:
    """Return the first matching template + its default params.

    `paper` is treated as a free mapping (so the classifier can work directly
    on sqlite Row, dict, or PaperRecord-style dataclass — caller normalises).
    """
    text = _haystack(paper)
    for spec in TEMPLATES:
        hits: List[str] = []
        for pattern in spec.keyword_patterns:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                hits.append(m.group(0).lower())
        # buy_and_hold falls through with hits == [] -> always matches last
        if hits or not spec.keyword_patterns:
            # dedupe preserving order
            seen: Dict[str, None] = {}
            dedup_hits = tuple(
                h for h in hits if not (h in seen or seen.update({h: None}))
            )
            return ClassificationResult(
                template=spec.name,
                default_params=dict(spec.default_params),
                matched_keywords=dedup_hits,
                tags=spec.tags,
            )
    raise RuntimeError("TEMPLATES does not contain a fallback bucket")
