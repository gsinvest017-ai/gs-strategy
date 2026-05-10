import os
import tempfile

import pytest

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
