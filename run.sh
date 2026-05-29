#!/usr/bin/env bash
# gs-strategy one-button launcher (Linux / macOS / WSL).
#
# Usage:
#   ./run.sh              # = setup + webui
#   ./run.sh setup        # create .venv + install deps (idempotent)
#   ./run.sh webui        # start webui on http://127.0.0.1:5057
#   ./run.sh crawl        # quant-crawl run + fetch-pdfs + rag-ingest
#   ./run.sh test         # pytest tests/
#   ./run.sh help
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

VENV_DIR="${ROOT_DIR}/.venv"
VENV_PY="${VENV_DIR}/bin/python"
PY_BOOTSTRAP="${PYTHON:-python3}"

# --- helpers ---------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }
log()  { printf "[run] %s\n" "$*"; }

ensure_venv() {
    if [[ ! -x "${VENV_PY}" ]]; then
        log "creating .venv with ${PY_BOOTSTRAP}"
        if ! have "${PY_BOOTSTRAP}"; then
            echo "[run] ERROR: ${PY_BOOTSTRAP} not found (set PYTHON= override)" >&2
            exit 1
        fi
        "${PY_BOOTSTRAP}" -m venv "${VENV_DIR}"
    fi
}

ensure_deps() {
    ensure_venv
    # idempotent: pip install -e . is a no-op if already up-to-date
    log "installing crawler (editable) + RAG extras"
    "${VENV_PY}" -m pip install -q --upgrade pip
    "${VENV_PY}" -m pip install -q -e .
    if [[ -f "${ROOT_DIR}/requirements-rag.txt" ]]; then
        "${VENV_PY}" -m pip install -q -r requirements-rag.txt
    fi
}

ensure_env() {
    if [[ ! -f "${ROOT_DIR}/.env" ]]; then
        if [[ -f "${ROOT_DIR}/.env.example" ]]; then
            log "WARNING: no .env; copying .env.example (fill TEJAPI_KEY for backtest)"
            cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
        else
            log "WARNING: no .env (TEJ-dependent commands will fail)"
        fi
    fi
}

# --- subcommands -----------------------------------------------------------
cmd_setup() {
    ensure_deps
    ensure_env
    log "setup complete. Next: ./run.sh webui"
}

cmd_webui() {
    ensure_deps
    # run_webui.sh is restart-safe + handles host/port defaults
    exec "${ROOT_DIR}/scripts/run_webui.sh" "$@"
}

cmd_crawl() {
    ensure_deps
    ensure_env
    log "step 1/3: quant-crawl run --log-run"
    "${VENV_PY}" -m quant_crawler.cli run --log-run
    log "step 2/3: quant-crawl fetch-pdfs"
    "${VENV_PY}" -m quant_crawler.cli fetch-pdfs || log "fetch-pdfs warning (continuing)"
    log "step 3/3: quant-crawl rag-ingest"
    "${VENV_PY}" -m quant_crawler.cli rag-ingest || log "rag-ingest warning (continuing)"
    log "crawl pipeline done."
}

cmd_test() {
    ensure_deps
    "${VENV_PY}" -m pip install -q pytest
    "${VENV_PY}" -m pytest tests/ "$@"
}

cmd_help() {
    awk '/^# Usage:/{f=1} f{ if (/^#/) {sub(/^# ?/,""); print} else exit }' "$0"
    exit 0
}

# --- dispatch --------------------------------------------------------------
SUBCMD="${1:-webui}"
case "${SUBCMD}" in
    setup)    shift; cmd_setup  "$@" ;;
    webui)    shift || true; cmd_webui "$@" ;;
    crawl)    shift; cmd_crawl  "$@" ;;
    test)     shift; cmd_test   "$@" ;;
    help|-h|--help) cmd_help ;;
    *)
        log "unknown subcommand: ${SUBCMD}"
        cmd_help
        ;;
esac
