#!/usr/bin/bash
# Timestamp: 2026-10-12 | Version: 5.0.1-dev.5
# Author & Credits: https://www.alawise.es/1-s
# This listener grants interactive assistance, not SFTP or port forwarding.
set -eu
if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
    printf '%s\n' 'Interactive assistance only; use ssh -tt -p 2222.' >&2
    exit 1
fi
exec /usr/bin/tmux -S /run/aux-assist/tmux.sock attach-session -t assist
