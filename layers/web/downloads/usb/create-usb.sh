#!/usr/bin/env bash
# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
# Keep device validation in one reviewable implementation; default is read-only planning.
set -Eeuo pipefail
pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${pth_app}/create-usb.py" "$@"
