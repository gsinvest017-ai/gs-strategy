import os
import tempfile
from pathlib import Path

import pytest

# Auto-load .env so the bundle validator subprocess (which imports zipline,
# transitively requiring TEJAPI_KEY at module-import time via exchange_calendars)
# inherits the key. Mirrors the loader used in every scripts/*.py entry point.
# Runs at collection time -> os.environ is populated before any subprocess spawns.
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists() and not os.environ.get("TEJAPI_KEY"):
    for _line in _ENV_PATH.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _v = _line.split("=", 1)
        os.environ.setdefault(_k.strip(), _v.strip())


# Each test gets its own DB.
@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    db = tmp_path / "papers.db"
    monkeypatch.setenv("QC_DATA_DIR", str(tmp_path))
    # importlib reload so config picks up the env var
    import importlib

    from quant_crawler import config

    importlib.reload(config)
    config.ensure_dirs()
    return config.DB_PATH
