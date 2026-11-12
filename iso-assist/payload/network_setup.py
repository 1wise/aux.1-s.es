#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 1.0.0
# Author and Credits: https://www.alawise.es/1-s
"""Prepare networking inside the disposable Live image, never on a running USB."""
from pathlib import Path


def prepara_red(sys_rad):
    """Discard builder-specific network state before publishing a generic image."""
    sys_rad = Path(sys_rad)
    sys_cfg = sys_rad / 'etc/NetworkManager/conf.d/90-aux-live.conf'
    sys_cfg.parent.mkdir(parents=True, exist_ok=True)
    # Let the Live manage DHCP and DNS without relying on an optional DNS daemon.
    sys_cfg.write_text(
        '# Timestamp: 2026-10-24 | Version: 1.0.0\n'
        '# Author and Credits: https://www.alawise.es/1-s\n'
        '[main]\ndhcp=internal\ndns=default\nrc-manager=symlink\nno-auto-default=\n'
    )

    # These are the installer's profiles, not a user's persistent Wi-Fi settings.
    for sys_arc in (sys_rad / 'etc/NetworkManager/system-connections').glob('*'):
        if sys_arc.is_file() or sys_arc.is_symlink():
            sys_arc.unlink()
    for sys_nom in ('NetworkManager.state', 'NetworkManager-intern.conf', 'no-auto-default.state'):
        (sys_rad / 'var/lib/NetworkManager' / sys_nom).unlink(missing_ok=True)

    sys_res = sys_rad / 'etc/resolv.conf'
    # Unlink first: writing through a stale installer symlink can alter its target.
    sys_res.unlink(missing_ok=True)
    sys_res.symlink_to('/run/NetworkManager/resolv.conf')
    # /run is recreated at every boot; never embed the builder's DNS addresses.
