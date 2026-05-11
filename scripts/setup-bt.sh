#!/usr/bin/env bash
# Build the backtest virtualenv (.venv-bt) for strategies/.
#
# Kept separate from the crawler's .venv to avoid pandas/numpy version
# clashes between zipline-tej's pinned deps and the crawler's lighter stack.
#
# Usage: ./scripts/setup-bt.sh [python-binary]
#   python-binary defaults to python3.11 (zipline-tej supports 3.9-3.12).

set -euo pipefail

PY_BIN="${1:-python3.11}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-bt"

if ! command -v "${PY_BIN}" >/dev/null 2>&1; then
    echo "[setup-bt] ${PY_BIN} not found on PATH" >&2
    echo "[setup-bt] try: ./scripts/setup-bt.sh python3.12" >&2
    exit 1
fi

if [[ -d "${VENV_DIR}" ]]; then
    echo "[setup-bt] ${VENV_DIR} already exists; reusing it"
else
    echo "[setup-bt] creating venv at ${VENV_DIR} with $(${PY_BIN} --version)"
    "${PY_BIN}" -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null
"${VENV_DIR}/bin/pip" install zipline-tej pyyaml

echo "[setup-bt] done. Verify with:"
echo "  ${VENV_DIR}/bin/python -c 'import zipline; print(zipline.__version__)'"
