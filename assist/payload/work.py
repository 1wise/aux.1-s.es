#!/usr/bin/python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Bound tmpfs to available memory; never use a client disk or swap."""
from pathlib import Path
import subprocess


def limite_ram(txt):
    mem = {lin.split(':', 1)[0]: int(lin.split()[1]) * 1024
           for lin in txt.splitlines() if lin.startswith(('MemTotal:', 'MemAvailable:'))}
    # A cap is not a reservation: root overlay and /work still consume the same RAM.
    lim = min(mem['MemTotal'] // 4, mem['MemAvailable'] // 3, 2 * 1024 ** 3)
    if lim < 64 * 1024 ** 2:
        raise RuntimeError('Insufficient available RAM for /work; inspect free -h.')
    return lim


def main():
    lim = limite_ram(Path('/proc/meminfo').read_text())
    pth = Path('/work')
    pth.mkdir(mode=0o700, exist_ok=True)
    if pth.is_mount():
        raise RuntimeError('/work is already mounted; refusing to hide existing data.')
    subprocess.run(['mount', '-t', 'tmpfs', '-o',
                    f'mode=0700,nosuid,nodev,size={lim}', 'tmpfs', str(pth)], check=True)
    # Execution is allowed for unpacked utilities and a manually prepared chroot.
    print(f'/work: tmpfs limit {lim // (1024 ** 2)} MiB; RAM only.')


if __name__ == '__main__':
    main()
