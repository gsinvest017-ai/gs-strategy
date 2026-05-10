"""stdlib-based logging with file + console sinks."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from quant_crawler.config import LOG_DIR, ensure_dirs

_FMT = "%(asctime)s [%(levelname)s] %(name)s :: %(message)s"
_configured = False


def get_logger(name: str = "quant_crawler") -> logging.Logger:
    global _configured
    if not _configured:
        ensure_dirs()
        root = logging.getLogger("quant_crawler")
        root.setLevel(logging.INFO)
        root.propagate = False

        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(logging.Formatter(_FMT))
        root.addHandler(console)

        fh = RotatingFileHandler(
            LOG_DIR / "crawler.log",
            maxBytes=2_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(_FMT))
        root.addHandler(fh)

        _configured = True

    if name == "quant_crawler":
        return logging.getLogger("quant_crawler")
    return logging.getLogger(f"quant_crawler.{name}")
