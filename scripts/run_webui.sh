#!/usr/bin/env bash
# Launch the gs-strategy management web UI.
#
# Usage:
#     ./scripts/run_webui.sh                # http://127.0.0.1:5057
#     ./scripts/run_webui.sh --port 6060
#     PORT=6060 ./scripts/run_webui.sh
#
# The UI is read-only (no DB writes, no strategy mutation). It reads
# data/papers.db and the strategies/ filesystem, and checks export status
# against ~/gs-zipline-tej/strategies (override: ZIPLINE_TEJ_STRATEGIES_DIR).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

VENV_PY="${ROOT_DIR}/.venv/bin/python"
if [[ ! -x "${VENV_PY}" ]]; then
    echo "[webui] ${VENV_PY} not found; run: python3 -m venv .venv && .venv/bin/pip install -e ." >&2
    exit 1
fi

PORT="${PORT:-5057}"

# Restart-safe: stdlib http.server does not hot-reload Python, so a server
# left running from before a code change serves stale logic. Stop any existing
# webui on this port first so re-running always picks up current code.
STALE_PIDS="$(pgrep -f "quant_crawler.webui .*--port ${PORT}" 2>/dev/null || true)"
if [[ -n "${STALE_PIDS}" ]]; then
    echo "[webui] stopping stale server on port ${PORT} (pid: ${STALE_PIDS})"
    # shellcheck disable=SC2086
    kill ${STALE_PIDS} 2>/dev/null || true
    sleep 1
fi

exec "${VENV_PY}" -m quant_crawler.webui --port "${PORT}" "$@"
