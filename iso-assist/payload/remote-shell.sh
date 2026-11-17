#!/usr/bin/bash
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# This listener grants interactive assistance, not SFTP or port forwarding.
set -eu
# Accept fixed PTY selectors only; never evaluate a supplied SSH command.
case "${SSH_ORIGINAL_COMMAND:-}" in
    ''|aux-terminal-1) sys_nom=assist ;;
    aux-terminal-2) sys_nom=assist-2 ;;
    *)
        printf '%s\n' 'Interactive assistance only; use ssh -tt -p 4242.' >&2
        exit 1
        ;;
esac
exec /usr/bin/tmux -S /run/aux-assist/tmux.sock attach-session -t "$sys_nom"
