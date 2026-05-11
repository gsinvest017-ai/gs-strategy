#!/usr/bin/env bash
# Run a single strategy under .venv-bt with .env auto-sourced.
#
# Usage: ./scripts/run_strategy.sh <strategy_name> [output_pickle]
#   strategy_name  one of: vgrsi_tx | cubic_momentum_tx | tsmom_tx_mtx | xsmom_stkfut_rmt
#   output_pickle  default: /tmp/<strategy_name>_result.pkl

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <strategy_name> [output_pickle]" >&2
    exit 2
fi

STRAT="$1"
OUTPUT="${2:-/tmp/${STRAT}_result.pkl}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-bt"
STRAT_DIR="${ROOT_DIR}/strategies/${STRAT}"

if [[ ! -d "${STRAT_DIR}" ]]; then
    echo "[run] strategy not found: ${STRAT_DIR}" >&2
    exit 1
fi
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo "[run] ${VENV_DIR} missing; run ./scripts/setup-bt.sh" >&2
    exit 1
fi

if [[ -f "${ROOT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.env"
    set +a
fi
: "${TEJAPI_KEY:?TEJAPI_KEY must be set (via .env or exported)}"

cd "${ROOT_DIR}"
"${VENV_DIR}/bin/python" strategies/_common/runner.py \
    --strategy "strategies/${STRAT}/strategy.py" \
    --config   "strategies/${STRAT}/config.yaml" \
    --output   "${OUTPUT}"

echo "[run] done -> ${OUTPUT}"
