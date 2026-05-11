#!/usr/bin/env bash
# Ingest the `tquant_future` bundle using TEJ API.
#
# Required env vars:
#   TEJAPI_KEY           your TEJ API key (no default)
# Optional env vars:
#   TEJAPI_BASE          default https://api.tej.com.tw
#   FUTURES_ROOTS        default "TX MTX"     (space-separated root symbols)
#   EQUITY_TICKERS       default unset        (opt-in only; needed if a strategy
#                                              sets `benchmark: IR0001` or
#                                              trades single-stock futures whose
#                                              underlying equity must also be
#                                              ingested for joint analytics)
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
export mdate="${MDATE:-20180101 20260510}"

# Equity tickers are opt-in. The bundle accepts futures-only ingest, and our
# strategies have benchmark/IR0001 disabled by default so we skip equity here
# unless EQUITY_TICKERS is explicitly set.
if [[ -n "${EQUITY_TICKERS:-}" ]]; then
    export ticker="${EQUITY_TICKERS}"
    echo "[ingest] futures=${future}  tickers=${ticker}  mdate=${mdate}"
else
    unset ticker
    echo "[ingest] futures=${future}  (no equity tickers)  mdate=${mdate}"
fi

"${VENV_DIR}/bin/zipline" ingest -b tquant_future
