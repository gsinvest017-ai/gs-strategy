"""Classify crawled papers/reports as STRATEGY vs FACTOR, with sub-categories.

Realises the "Strategy/Factor scraper, factor class" + "Raw strategy/factor
pool" split from architecture.drawio:

    classify_kind(paper)   -> KindResult(kind, factor_score, strategy_score)
    subcategories(paper, kind) -> ordered list of sub-category tags
    classify(paper)        -> {kind, subcats, factor_score, strategy_score}

All pure functions over a paper mapping (title/abstract/keywords_hit/
categories). Auto labels are derived on read; manual labels live in the DB
(quant_crawler.storage.labels).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

# --- kind decision vocabularies -------------------------------------------
# Phrases that lean a paper towards the FACTOR pool (cross-sectional return
# predictors / factor investing literature).
_FACTOR_PATTERNS: Tuple[str, ...] = (
    r"\bfactors?\b", r"\bcross[- ]?sectional\b", r"\banomal(y|ies)\b",
    r"\bcharacteristics?\b", r"\brisk premi", r"\bfama[- ]?french\b",
    r"\bfactor model", r"\bfactor zoo\b", r"\bsmart beta\b",
    r"\breturn predictab", r"\bexpected returns?\b",
    r"\bbetting[- ]against[- ]beta\b", r"\bstyle investing\b",
    r"\bfactor premi", r"\bfactor investing\b", r"\bfactor exposure",
)
# Phrases that lean towards the STRATEGY pool (trading systems / rules).
_STRATEGY_PATTERNS: Tuple[str, ...] = (
    r"\btrading strateg", r"\btrading rule", r"\btrading system",
    r"\bbacktest", r"\bexecution\b", r"\bmarket timing\b",
    r"\btechnical indicator", r"\btrend[- ]?follow", r"\bpairs[- ]?trad",
    r"\bmarket[- ]making\b", r"\border book\b",
    r"\bhigh[- ]frequency trad", r"\btrading signal", r"\boverlay\b",
    r"\bportfolio strateg", r"\bbuy[- ]and[- ]hold\b", r"\bentry/exit\b",
)


@dataclass(frozen=True)
class SubcatSpec:
    name: str
    patterns: Tuple[str, ...]


# FACTOR sub-category taxonomy (factor-investing style labels).
FACTOR_SUBCATS: Tuple[SubcatSpec, ...] = (
    SubcatSpec("value", (r"\bvalue (factor|premium|investing|effect|stock)",
                         r"\bbook[- ]to[- ]market\b", r"\bvaluation ratio")),
    SubcatSpec("size", (r"\bsize (factor|premium|effect)", r"\bsmall[- ]cap\b",
                        r"\bsmb\b")),
    SubcatSpec("momentum", (r"\bmomentum\b", r"\bcross[- ]sectional momentum\b",
                            r"\brelative strength\b")),
    SubcatSpec("quality", (r"\bquality (factor|premium)", r"\bprofitabilit",
                           r"\bearnings quality\b")),
    SubcatSpec("low-volatility", (r"\blow[- ]volatility\b", r"\blow[- ]vol\b",
                                  r"\bminimum variance\b", r"\bdefensive\b")),
    SubcatSpec("investment", (r"\binvestment factor\b", r"\basset growth\b",
                              r"\bcapex\b")),
    SubcatSpec("liquidity", (r"\bliquidity (factor|premium|risk)",
                             r"\billiquidit")),
    SubcatSpec("carry", (r"\bcarry (factor|trade)", r"\bterm[- ]structure\b",
                         r"\broll yield\b")),
    SubcatSpec("dividend", (r"\bdividend (yield|factor)", r"\bpayout\b")),
    SubcatSpec("reversal", (r"\breversal\b", r"\bshort[- ]term reversal\b",
                            r"\blong[- ]term reversal\b")),
    SubcatSpec("sentiment", (r"\bsentiment\b", r"\binvestor attention\b")),
    SubcatSpec("macro", (r"\bmacro(economic)? factor", r"\binflation\b",
                         r"\bbusiness cycle\b")),
    SubcatSpec("esg", (r"\besg\b", r"\bsustainab", r"\bgreen\b",
                       r"\bclimate (risk|factor)", r"\bbiodiversity\b")),
    SubcatSpec("betting-against-beta", (r"\bbetting[- ]against[- ]beta\b",
                                        r"\bbab\b", r"\blow[- ]beta\b")),
)

# STRATEGY sub-category taxonomy (trading-system style labels).
STRATEGY_SUBCATS: Tuple[SubcatSpec, ...] = (
    SubcatSpec("trend-following", (r"\btrend[- ]?follow", r"\bcta\b",
                                   r"\bmanaged futures\b")),
    SubcatSpec("time-series-momentum", (r"\btime[- ]?series momentum\b",
                                        r"\btsmom\b")),
    SubcatSpec("cross-sectional-momentum", (r"\bcross[- ]?sectional momentum\b",
                                            r"\bxsmom\b")),
    SubcatSpec("mean-reversion", (r"\bmean[- ]?reversion\b", r"\bmean[- ]?revert",
                                  r"\bcontrarian\b", r"\bover[- ]?bought\b",
                                  r"\bover[- ]?sold\b")),
    SubcatSpec("breakout", (r"\bbreakout\b", r"\bdonchian\b",
                            r"\bchannel breakout\b")),
    SubcatSpec("pairs-trading", (r"\bpairs?[- ]trad",)),
    SubcatSpec("statistical-arbitrage", (r"\bstatistical[- ]arbitrage\b",
                                         r"\bstat[- ]?arb\b", r"\bcointegrat")),
    SubcatSpec("market-making", (r"\bmarket[- ]making\b",
                                 r"\bliquidity provision\b",
                                 r"\bbid[- ]ask spread\b")),
    SubcatSpec("event-driven", (r"\bevent[- ]driven\b", r"\bearnings (drift|surprise)",
                                r"\bmerger\b", r"\bm&a\b", r"\bannouncement\b")),
    SubcatSpec("volatility", (r"\bvolatility (target|trading)", r"\bvix\b",
                              r"\bvariance (risk|premium|swap)", r"\bgarch\b")),
    SubcatSpec("options", (r"\boptions?\b", r"\bimplied volatility\b",
                           r"\bcall option\b", r"\bput option\b")),
    SubcatSpec("technical", (r"\btechnical (analysis|indicator|trading)",
                             r"\brsi\b", r"\bmacd\b", r"\bmoving average",
                             r"\bvisibility graph\b", r"\badx\b")),
    SubcatSpec("machine-learning", (r"\bmachine learning\b", r"\bdeep learning\b",
                                    r"\bneural network", r"\breinforcement learning\b",
                                    r"\blstm\b")),
    SubcatSpec("high-frequency", (r"\bhigh[- ]frequency\b", r"\bhft\b",
                                  r"\border flow\b", r"\bmicrostructure\b")),
    SubcatSpec("arbitrage", (r"\barbitrage\b",)),
)

# Pre-compile.
_FACTOR_RES = tuple(re.compile(p, re.IGNORECASE) for p in _FACTOR_PATTERNS)
_STRATEGY_RES = tuple(re.compile(p, re.IGNORECASE) for p in _STRATEGY_PATTERNS)
_FACTOR_SUBCAT_RES = tuple(
    (s.name, tuple(re.compile(p, re.IGNORECASE) for p in s.patterns))
    for s in FACTOR_SUBCATS
)
_STRATEGY_SUBCAT_RES = tuple(
    (s.name, tuple(re.compile(p, re.IGNORECASE) for p in s.patterns))
    for s in STRATEGY_SUBCATS
)

FACTOR_SUBCAT_NAMES = tuple(s.name for s in FACTOR_SUBCATS)
STRATEGY_SUBCAT_NAMES = tuple(s.name for s in STRATEGY_SUBCATS)
KINDS = ("strategy", "factor")


@dataclass(frozen=True)
class KindResult:
    kind: str
    factor_score: int
    strategy_score: int


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
    return " \n ".join(parts)


def classify_kind(paper: Mapping[str, Any]) -> KindResult:
    """Binary kind decision. Ties / no-signal default to 'strategy'."""
    text = _haystack(paper)
    fscore = sum(1 for r in _FACTOR_RES if r.search(text))
    sscore = sum(1 for r in _STRATEGY_RES if r.search(text))
    kind = "factor" if fscore > sscore else "strategy"
    return KindResult(kind=kind, factor_score=fscore, strategy_score=sscore)


def subcategories(paper: Mapping[str, Any], kind: str) -> List[str]:
    """Auto sub-category tags for the given kind (multi-label, ordered)."""
    text = _haystack(paper)
    res = _FACTOR_SUBCAT_RES if kind == "factor" else _STRATEGY_SUBCAT_RES
    out: List[str] = []
    for name, patterns in res:
        if any(p.search(text) for p in patterns):
            out.append(name)
    return out


def classify(paper: Mapping[str, Any]) -> Dict[str, Any]:
    """One-shot: kind + auto sub-categories + scores."""
    kr = classify_kind(paper)
    return {
        "kind": kr.kind,
        "subcats": subcategories(paper, kr.kind),
        "factor_score": kr.factor_score,
        "strategy_score": kr.strategy_score,
    }


def subcat_vocabulary(kind: str) -> Tuple[str, ...]:
    return FACTOR_SUBCAT_NAMES if kind == "factor" else STRATEGY_SUBCAT_NAMES
