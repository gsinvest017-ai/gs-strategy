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


# Whether a TEJ API key is available. Importing zipline is not free: at
# module-import time ``exchange_calendars`` resolves the TEJ trading calendar
# via a live ``tejapi`` request, so anything that shells out to the bundle
# validator needs a real key *and* network access to TEJ. CI runners have
# neither, and marking those tests skipped is honest where letting them fail
# is not.
HAS_TEJ_KEY = bool(os.environ.get("TEJAPI_KEY"))

requires_tej = pytest.mark.skipif(
    not HAS_TEJ_KEY,
    reason="needs TEJAPI_KEY: the bundle validator imports zipline, which "
           "resolves the TEJ calendar over the network at import time",
)


@pytest.fixture(scope="session", autouse=True)
def _ensure_db_schema():
    """Create papers.db's tables once per session, before any test runs.

    Several tests read the crawler DB directly (the webui routes, the RAG MCP
    dispatch). On a fresh checkout that file does not exist, and they failed
    with opaque ``no such table`` / HTTP 500 errors. Worse, the failures were
    order-dependent: a previous run leaving ``data/papers.db`` behind made
    them pass, so the suite looked green on a developer machine and red on a
    clean one.

    ``CREATE TABLE IF NOT EXISTS`` makes this a no-op against a populated
    developer DB.
    """
    from quant_crawler.storage.db import Storage

    Storage()
    yield


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
