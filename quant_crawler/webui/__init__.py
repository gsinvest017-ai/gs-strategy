"""Local web management UI for the gs-strategy crawler + strategy pipeline.

`stats.py` is the data layer (pure functions over papers.db + the strategies/
filesystem). `server.py` is a stdlib http.server that serves a single-page
dashboard plus a small JSON API. Launch with::

    python -m quant_crawler.webui            # serves on http://127.0.0.1:5057
"""
