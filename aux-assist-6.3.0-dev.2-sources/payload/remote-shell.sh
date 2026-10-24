#!/usr/bin/bash
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# This listener grants interactive assistance, not SFTP or port forwarding.
set -eu
if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
    printf '%s\n' 'Interactive assistance only; use ssh -tt -p 4242.' >&2
    exit 1
fi
exec /usr/bin/tmux -S /run/aux-assist/tmux.sock attach-session -t assist
