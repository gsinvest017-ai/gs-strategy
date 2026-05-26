#!/usr/bin/env bash
# Install (or uninstall) the gs-strategy daily_refresh cron job.
#
# This script DOES NOT modify your crontab by default — it only prints what
# it would do. Pass --apply to actually write to crontab, --uninstall to
# remove the existing block.
#
# Cron schedule: every day at 06:00 local. Adjust by editing the SCHEDULE
# variable below or passing --schedule "<cron expr>".
#
# Usage:
#     scripts/install_daily_refresh.sh             # dry-run, print plan
#     scripts/install_daily_refresh.sh --apply     # write to crontab
#     scripts/install_daily_refresh.sh --uninstall # remove the block
#     scripts/install_daily_refresh.sh --apply --schedule "30 5 * * *"
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REFRESH="${ROOT_DIR}/scripts/daily_refresh.sh"
LOG="${ROOT_DIR}/data/logs/daily_refresh_cron.log"
MARKER_BEGIN="# >>> gs-strategy daily_refresh <<<"
MARKER_END="# <<< gs-strategy daily_refresh >>>"

SCHEDULE="0 6 * * *"   # 06:00 every day
MODE="dry-run"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --apply)     MODE="apply" ;;
        --uninstall) MODE="uninstall" ;;
        --schedule)  shift; SCHEDULE="$1" ;;
        -h|--help)
            sed -n '2,16p' "$0"; exit 0 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
    shift
done

CRON_LINE="${SCHEDULE} ${REFRESH} >> ${LOG} 2>&1"

print_block() {
    cat <<EOF
${MARKER_BEGIN}
# Auto-installed by gs-strategy/scripts/install_daily_refresh.sh
# Daily paper-crawler + strategy_gen pipeline. Edit by re-running the
# installer (do NOT hand-edit between the markers).
# Disable: ${ROOT_DIR}/scripts/install_daily_refresh.sh --uninstall
${CRON_LINE}
${MARKER_END}
EOF
}

current_crontab() {
    # If the user has no crontab, `crontab -l` exits 1; treat as empty.
    crontab -l 2>/dev/null || true
}

strip_block() {
    awk -v b="${MARKER_BEGIN}" -v e="${MARKER_END}" '
        BEGIN { inblock = 0 }
        $0 == b { inblock = 1; next }
        $0 == e { inblock = 0; next }
        inblock == 0 { print }
    '
}

case "${MODE}" in
    dry-run)
        echo "===== dry run (no crontab changes) ====="
        echo "Schedule: ${SCHEDULE}"
        echo "Refresh : ${REFRESH}"
        echo "Log     : ${LOG}"
        echo
        echo "===== block that WOULD be appended to crontab ====="
        print_block
        echo
        echo "Run with --apply to install, --uninstall to remove."
        ;;
    apply)
        if [[ ! -x "${REFRESH}" ]]; then
            echo "ERROR: ${REFRESH} not found or not executable" >&2
            exit 1
        fi
        mkdir -p "$(dirname "${LOG}")"
        TMP="$(mktemp)"
        # Strip any pre-existing block first so re-applying just refreshes
        # the schedule.
        current_crontab | strip_block > "${TMP}"
        print_block >> "${TMP}"
        crontab "${TMP}"
        rm -f "${TMP}"
        echo "Installed cron block:"
        print_block
        ;;
    uninstall)
        TMP="$(mktemp)"
        current_crontab | strip_block > "${TMP}"
        crontab "${TMP}"
        rm -f "${TMP}"
        echo "Removed gs-strategy daily_refresh cron block."
        ;;
esac
