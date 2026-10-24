#!/usr/bin/env bash
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# Read-only checks, with no service changes and no configuration/secret dumps.
set -uo pipefail
err_ct=0
for uni_nom in aux-cli nginx; do
    if ! systemctl is-active "${uni_nom}.service"; then
        printf 'PENDING: %s.service is not active.\n' "${uni_nom}" >&2
        err_ct=$((err_ct + 1))
    fi
done
if ! curl --noproxy '*' --fail --silent --show-error --max-time 8 http://127.0.0.1:8096/health; then
    printf '\nPENDING: local CLI health check failed.\n' >&2
    err_ct=$((err_ct + 1))
fi
if ! curl --fail --silent --show-error --max-time 12 https://cli.1-s.es/health; then
    printf '\nPENDING: public DNS/TLS/HTTPS health check failed.\n' >&2
    err_ct=$((err_ct + 1))
fi
printf '\nAI units aux-gpt, aux-gemini and aux-exec belong in the ISO, not Excalibur.\n'
printf 'Pending checks: %d. These checks do not prove WSS, consent, API calls or external GSM access.\n' "${err_ct}"
exit "$((err_ct > 0))"
