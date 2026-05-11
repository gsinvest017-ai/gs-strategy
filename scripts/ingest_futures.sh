#!/usr/bin/env bash
# Ingest the `tquant_future` bundle using TEJ API.
#
# Required env vars:
#   TEJAPI_KEY           your TEJ API key (no default)
# Optional env vars:
#   TEJAPI_BASE          default https://api.tej.com.tw
#   FUTURES_ROOTS        default "TX MTX"     (space-separated root symbols)
#   EQUITY_TICKERS       default "IR0001 IX0001"  (for joint ingest support)
#   MDATE                default "20180101 20260510"
#
# Usage: TEJAPI_KEY=xxxx ./scripts/ingest_futures.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv-bt"

# Auto-source .env if present so callers don't have to remember.
if [[ -f "${ROOT_DIR}/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${ROOT_DIR}/.env"
    set +a
fi

if [[ ! -x "${VENV_DIR}/bin/zipline" ]]; then
    echo "[ingest] ${VENV_DIR}/bin/zipline not found." >&2
    echo "[ingest] run ./scripts/setup-bt.sh first" >&2
    exit 1
fi

: "${TEJAPI_KEY:?TEJAPI_KEY must be set (via .env or exported)}"
export TEJAPI_BASE="${TEJAPI_BASE:-https://api.tej.com.tw}"

export future="${FUTURES_ROOTS:-TX MTX}"
export ticker="${EQUITY_TICKERS:-IR0001 IX0001}"
export mdate="${MDATE:-20180101 20260510}"

echo "[ingest] futures=${future}  tickers=${ticker}  mdate=${mdate}"
"${VENV_DIR}/bin/zipline" ingest -b tquant_future
