"""Central configuration. Tunable via env vars; sensible defaults for sandbox use."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("QC_DATA_DIR", PROJECT_ROOT / "data"))
PDF_DIR = DATA_DIR / "pdfs"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "papers.db"
LOG_DIR = PROJECT_ROOT / "logs"
EXPERIMENT_LOG = PROJECT_ROOT / "docs" / "EXPERIMENT_LOG.md"


# Polite-crawling defaults. Per-source classes can override.
DEFAULT_USER_AGENT = (
    "yolo-claude-quant-crawler/0.1 (+research; contact gsinvest017@gsinvest.com.tw)"
)
DEFAULT_REQUEST_TIMEOUT = 30  # seconds
DEFAULT_MIN_DELAY = 2.0  # seconds between requests to same host
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 2.0


# Keywords that mark a paper as relevant to futures / managed-futures / commodity quant.
# Pattern is intentionally generous — false positives get filtered downstream by user.
RELEVANCE_PATTERNS = [
    r"\bfutures?\b",
    r"\bcommodit(y|ies)\b",
    r"\bderivativ",
    r"\bmanaged[\s-]+futures?\b",
    r"\bCTA\b",
    r"\btrend[\s-]+follow",
    r"\bmomentum\b",
    r"\bcarry\b",
    r"\bterm[\s-]+structure\b",
    r"\bbasis\b",
    r"\bcontango|backwardation\b",
    r"\bhedg(e|ing)\b",
    r"\bmean[\s-]+revers",
    r"\bstatistical[\s-]+arbitrage|stat[\s-]?arb\b",
    r"\bpairs[\s-]+trading\b",
    r"\bvolatility[\s-]+(risk|premium|arbitrage)",
    r"\bquant(itative)?[\s-]+(strateg|trad|invest)",
    r"\bfactor[\s-]+(invest|model|premia)",
    r"\brisk[\s-]+parity\b",
    r"\bcommodity[\s-]+pool\b",
    r"\bRoll[\s-]+yield\b",
]
RELEVANCE_REGEX = re.compile("|".join(RELEVANCE_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class SourceConfig:
    name: str
    enabled: bool = True
    min_delay: float = DEFAULT_MIN_DELAY
    max_items_per_run: int = 100
    download_pdfs: bool = False  # default: metadata only (lighter, more polite)
    extras: dict = field(default_factory=dict)


# Per-source config. Adjust by editing here or via CLI flags.
SOURCES: dict[str, SourceConfig] = {
    "arxiv": SourceConfig(
        name="arxiv",
        min_delay=3.0,  # arXiv asks for >=3s
        max_items_per_run=50,
        extras={
            "categories": ["q-fin.TR", "q-fin.PM", "q-fin.ST", "q-fin.CP", "q-fin.RM"],
        },
    ),
    "nber": SourceConfig(
        name="nber",
        min_delay=2.0,
        max_items_per_run=50,
    ),
    "ssrn": SourceConfig(
        name="ssrn",
        min_delay=4.0,  # SSRN is sensitive
        max_items_per_run=30,
        extras={
            # SSRN journal IDs (FEN main journals on derivatives / futures)
            "journal_ids": ["203978", "203956"],
        },
    ),
    "cme": SourceConfig(
        name="cme",
        min_delay=2.0,
        max_items_per_run=20,
    ),
    "fed_feds": SourceConfig(
        name="fed_feds",
        min_delay=2.0,
        max_items_per_run=30,
    ),
    "aqr": SourceConfig(
        name="aqr",
        min_delay=3.0,
        max_items_per_run=20,
    ),
    "man_ahl": SourceConfig(
        name="man_ahl",
        min_delay=3.0,
        max_items_per_run=20,
    ),
}


def ensure_dirs() -> None:
    """Make sure runtime directories exist."""
    for d in (DATA_DIR, PDF_DIR, RAW_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
