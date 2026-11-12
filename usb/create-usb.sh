#!/usr/bin/env bash
# Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# Keep device validation in one reviewable implementation; default is read-only planning.
set -Eeuo pipefail
pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${pth_app}/create-usb.py" "$@"
