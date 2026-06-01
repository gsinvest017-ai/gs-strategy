#!/usr/bin/env bash
# 安裝本 repo 的 git hooks 到 .git/hooks/ (symlink)。
#
# Usage:
#   ./scripts/install_hooks.sh                  # 安裝
#   ./scripts/install_hooks.sh --uninstall      # 移除（刪 symlink）
#   ./scripts/install_hooks.sh --status         # 看目前狀態
#
# 只動 .git/hooks/ 目錄下的 symlink，不修改其他 git 設定；
# 解除安裝後 commit 行為完全回到 stock。
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GIT_HOOKS_DIR="${ROOT_DIR}/.git/hooks"
SRC_HOOKS_DIR="${ROOT_DIR}/scripts/hooks"
HOOKS=(commit-msg)

log() { printf "[install_hooks] %s\n" "$*"; }

action="${1:-install}"
case "${action}" in
    install)
        mkdir -p "${GIT_HOOKS_DIR}"
        for hook in "${HOOKS[@]}"; do
            src="${SRC_HOOKS_DIR}/${hook}"
            dst="${GIT_HOOKS_DIR}/${hook}"
            [[ ! -f "${src}" ]] && { log "略過：${src} 不存在"; continue; }
            chmod +x "${src}"
            # 已存在但不是我們的 symlink → 備份
            if [[ -e "${dst}" && ! -L "${dst}" ]]; then
                mv "${dst}" "${dst}.backup-$(date +%s)"
                log "備份既有 ${hook} → $(basename ${dst}.backup-*)"
            fi
            ln -sf "${src}" "${dst}"
            log "已安裝 ${hook} → symlink to scripts/hooks/${hook}"
        done
        log "完成。下次 git commit 會自動執行 hook（lint 模式預設不擋）。"
        log "要轉成阻擋模式：把 ${SRC_HOOKS_DIR}/commit-msg 內 STRICT=0 改 1。"
        ;;
    --uninstall|uninstall)
        for hook in "${HOOKS[@]}"; do
            dst="${GIT_HOOKS_DIR}/${hook}"
            if [[ -L "${dst}" ]]; then
                rm "${dst}"
                log "已移除 ${hook}"
            else
                log "略過：${hook} 非本 repo 安裝的 symlink"
            fi
        done
        ;;
    --status|status)
        for hook in "${HOOKS[@]}"; do
            dst="${GIT_HOOKS_DIR}/${hook}"
            if [[ -L "${dst}" ]]; then
                log "${hook}: symlink → $(readlink ${dst})"
            elif [[ -f "${dst}" ]]; then
                log "${hook}: 一般檔案（非本 repo 安裝；可能是別的工具留的）"
            else
                log "${hook}: 未安裝"
            fi
        done
        ;;
    *)
        echo "usage: $0 [install|--uninstall|--status]" >&2
        exit 2
        ;;
esac
