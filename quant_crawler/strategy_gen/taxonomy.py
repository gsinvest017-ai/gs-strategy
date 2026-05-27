"""Multi-dimensional strategy-category taxonomy.

A flat tag string list is what the gs-zipline-tej dashboard searches over
(``dashboard/static/main.js`` builds a haystack that includes ``manifest.tags``
and does multi-token fuzzy substring matching). To make those tags consistent
and high-recall, we classify a paper along several orthogonal *dimensions* and
emit every matching tag (multi-label), drawing from a curated vocabulary.

Public API
----------
    extract_tags(paper, dimensions=None) -> dict[str, list[str]]
        Per-dimension matched tags. `dimensions` filters which to scan.

    flat_tags(paper, dimensions=DEFAULT_BUNDLE_DIMENSIONS) -> list[str]
        Flattened, de-duped, dimension-then-declaration-ordered tag list —
        the form that goes straight into manifest.tags.

    TAG_VOCABULARY -> frozenset[str]
        Every tag the taxonomy can emit (for validation / listing / docs).

Design notes
------------
* Patterns are deliberately conservative — false positives pollute fuzzy
  search. Generic English words ("value", "graph", "us") are only matched in
  qualified phrases ("value premium", "visibility graph").
* A dimension is multi-label: a single paper can be both "momentum" and
  "trend-following".
* The paper's own market/region/asset (could be US equities) is intentionally
  NOT a default bundle dimension — generated bundles always execute on Taiwan
  futures, so emitting "us" would mislead search. Region/asset live in the
  manifest's ``source.paper`` provenance instead.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Mapping, Tuple

# Each dimension maps to an ORDERED list of (tag, [regex patterns]).
# Order within a dimension controls emission order in flat_tags().
_RAW_DIMENSIONS: Dict[str, Tuple[Tuple[str, Tuple[str, ...]], ...]] = {
    "family": (
        ("momentum", (r"\bmomentum\b", r"\btsmom\b", r"\bxsmom\b",
                      r"\brelative strength\b")),
        ("trend-following", (r"\btrend[- ]?following\b", r"\btrend[- ]?follow",
                             r"\bcta\b", r"\bmanaged futures\b")),
        ("mean-reversion", (r"\bmean[- ]?reversion\b", r"\bmean[- ]?revert",
                            r"\breversal\b", r"\bcontrarian\b",
                            r"\bover[- ]?bought\b", r"\bover[- ]?sold\b")),
        ("breakout", (r"\bbreakout\b", r"\bdonchian\b", r"\bchannel breakout\b")),
        ("pairs-trading", (r"\bpairs?[- ]trad", r"\bpair[- ]trad")),
        ("statistical-arbitrage", (r"\bstatistical[- ]arbitrage\b",
                                   r"\bstat[- ]?arb\b", r"\bcointegrat")),
        ("carry", (r"\bcarry\b", r"\bterm[- ]structure\b", r"\broll yield\b",
                   r"\bbasis trad")),
        ("value", (r"\bvalue (factor|premium|investing|strateg|effect)",
                   r"\bbook[- ]to[- ]market\b", r"\bvaluation ratio")),
        ("factor", (r"\bfactor (model|investing|premi|portfolio|zoo)",
                    r"\bmulti[- ]?factor\b", r"\bsmart beta\b",
                    r"\bsize factor\b", r"\bquality factor\b",
                    r"\brisk factor")),
        ("volatility", (r"\bvolatility\b", r"\bvariance\b", r"\bvix\b",
                        r"\bgarch\b", r"\bvol[- ]target",
                        r"\bvolatility targeting\b")),
        ("event-driven", (r"\bevent[- ]driven\b", r"\bearnings (drift|surprise|announce)",
                          r"\bpost[- ]earnings\b", r"\bmerger\b", r"\bm&a\b",
                          r"\bannouncement\b")),
        ("market-making", (r"\bmarket[- ]making\b", r"\bliquidity provision\b",
                           r"\bbid[- ]ask spread\b")),
        ("arbitrage", (r"\barbitrage\b",)),
    ),
    "signal": (
        ("technical", (r"\btechnical (analysis|indicator|trading)",
                       r"\brsi\b", r"\bmacd\b", r"\bmoving average",
                       r"\boscillator\b", r"\bbollinger\b", r"\badx\b")),
        ("fundamental", (r"\bfundamental(s| analysis| signal| data)",
                         r"\bbalance sheet\b", r"\bcash flow\b",
                         r"\baccounting\b")),
        ("cross-sectional", (r"\bcross[- ]?sectional\b",)),
        ("time-series", (r"\btime[- ]?series\b",)),
        ("regime-aware", (r"\bregime\b", r"\bmarkov\b",
                          r"\bhidden markov\b", r"\brandom matrix\b",
                          r"\brmt\b", r"\bregime[- ]switch")),
        ("machine-learning", (r"\bmachine learning\b", r"\bdeep learning\b",
                              r"\bneural network", r"\brandom forest\b",
                              r"\bxgboost\b", r"\bgradient boost",
                              r"\breinforcement learning\b", r"\blstm\b",
                              r"\btransformer\b")),
        ("sentiment", (r"\bsentiment\b", r"\bnews[- ]based\b",
                       r"\btext mining\b", r"\bnlp\b",
                       r"\bnatural language\b")),
        ("microstructure", (r"\bmicrostructure\b", r"\border book\b",
                            r"\border flow\b", r"\blimit order\b",
                            r"\bhigh[- ]frequency trad")),
        ("graph-based", (r"\bvisibility graph\b", r"\bgraph theor",
                         r"\bcomplex network\b", r"\bnetwork analysis\b")),
    ),
    "direction": (
        ("long-short", (r"\blong[- ]short\b", r"\blong/short\b")),
        ("market-neutral", (r"\bmarket[- ]neutral\b", r"\bbeta[- ]neutral\b",
                            r"\bdollar[- ]neutral\b")),
        ("long-only", (r"\blong[- ]only\b",)),
    ),
    # `instrument` is rarely inferable from the paper text; the generator
    # injects it from the bundle's root symbol instead. Kept here so the
    # vocabulary is complete and validators can recognise the tags.
    "instrument": (
        ("index-future", (r"\bindex futures?\b", r"\bstock index futures?\b")),
        ("stock-future", (r"\bsingle[- ]stock futures?\b",
                          r"\bstock futures?\b")),
        ("single-stock", (r"\bsingle[- ]stock\b",)),
    ),
    # Paper-domain region/asset — NOT emitted into bundle tags by default
    # (see module docstring), but available for callers that want them.
    "region": (
        ("taiwan", (r"\btaiwan\b", r"\btwse\b", r"\btaiex\b", r"\btwii\b")),
        ("us", (r"\bunited states\b", r"\bu\.s\.\b", r"\bus equit",
                r"\bs&p\s?500\b", r"\bnasdaq\b", r"\bnyse\b", r"\bdow jones\b")),
        ("china", (r"\bchina\b", r"\bchinese\b", r"\ba[- ]shares?\b",
                   r"\bshanghai\b", r"\bshenzhen\b", r"\bcsi\s?300\b")),
        ("japan", (r"\bjapan\b", r"\bnikkei\b", r"\btopix\b")),
        ("europe", (r"\beuropean?\b", r"\beuro[- ]?stoxx\b", r"\bftse\b",
                    r"\bdax\b")),
        ("global", (r"\bglobal\b", r"\binternational market",
                    r"\bcross[- ]countr", r"\bg5\b", r"\bg7\b")),
        ("emerging-markets", (r"\bemerging market",)),
    ),
    "asset_class": (
        ("equity", (r"\bequit", r"\bstock market\b", r"\bstocks?\b",
                    r"\bshares?\b")),
        ("futures", (r"\bfutures?\b",)),
        ("options", (r"\boptions?\b", r"\bimplied volatility\b",
                     r"\bcall option\b", r"\bput option\b")),
        ("fx", (r"\bforeign exchange\b", r"\bcurrenc", r"\bfx market\b")),
        ("fixed-income", (r"\bbonds?\b", r"\btreasur", r"\byield curve\b",
                          r"\bfixed[- ]income\b")),
        ("crypto", (r"\bcrypto", r"\bbitcoin\b", r"\bethereum\b")),
        ("commodity", (r"\bcommodit", r"\bcrude oil\b", r"\bgold\b")),
    ),
}

# Pre-compile every pattern once.
_COMPILED: Dict[str, Tuple[Tuple[str, Tuple[re.Pattern, ...]], ...]] = {
    dim: tuple(
        (tag, tuple(re.compile(p, re.IGNORECASE) for p in patterns))
        for tag, patterns in entries
    )
    for dim, entries in _RAW_DIMENSIONS.items()
}

# Dimensions whose tags describe the *strategy* (transferable to a Taiwan-
# futures skeleton). These flatten into manifest.tags by default.
DEFAULT_BUNDLE_DIMENSIONS: Tuple[str, ...] = (
    "family", "signal", "direction",
)

ALL_DIMENSIONS: Tuple[str, ...] = tuple(_RAW_DIMENSIONS.keys())

TAG_VOCABULARY = frozenset(
    tag for entries in _RAW_DIMENSIONS.values() for tag, _ in entries
)


def _haystack(paper: Mapping[str, object]) -> str:
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


def extract_tags(
    paper: Mapping[str, object],
    dimensions: Iterable[str] | None = None,
) -> Dict[str, List[str]]:
    """Return matched tags per dimension (multi-label within each)."""
    dims = tuple(dimensions) if dimensions is not None else ALL_DIMENSIONS
    text = _haystack(paper)
    out: Dict[str, List[str]] = {}
    for dim in dims:
        compiled = _COMPILED.get(dim)
        if not compiled:
            continue
        hits: List[str] = []
        for tag, patterns in compiled:
            if any(p.search(text) for p in patterns):
                hits.append(tag)
        if hits:
            out[dim] = hits
    return out


def flat_tags(
    paper: Mapping[str, object],
    dimensions: Iterable[str] = DEFAULT_BUNDLE_DIMENSIONS,
) -> List[str]:
    """Flatten extract_tags into an ordered, de-duped tag list."""
    per_dim = extract_tags(paper, dimensions=dimensions)
    seen: Dict[str, None] = {}
    flat: List[str] = []
    for dim in dimensions:
        for tag in per_dim.get(dim, []):
            if tag not in seen:
                seen[tag] = None
                flat.append(tag)
    return flat
