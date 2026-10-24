#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Opt-in AUX-DATA mount, never an automatic mount based on an untrusted label."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--partition', required=True, type=Path)
    cfg = par.parse_args()
    pth = cfg.partition.resolve(strict=True)
    if os.geteuid() != 0 or not str(pth).startswith('/dev/') or not pth.is_block_device():
        par.error('Requiere root y una partición explícita de /dev.')
    for campo, esperado in [('TYPE', 'ext4'), ('LABEL', 'AUX-DATA')]:
        rsp = subprocess.run(['blkid', '-p', '-s', campo, '-o', 'value', str(pth)],
                             check=True, capture_output=True, text=True)
        if rsp.stdout.strip() != esperado:
            par.error('La partición no es ext4 AUX-DATA; no se monta.')
    if subprocess.run(['findmnt', '--source', str(pth)], stdout=subprocess.DEVNULL).returncode == 0:
        par.error('Ya está montada; revisar findmnt.')
    dst = Path('/storage')
    if dst.is_symlink() or dst.is_mount():
        par.error('/storage no es un punto de montaje libre.')
    dst.mkdir(mode=0o700, exist_ok=True)
    if any(dst.iterdir()):
        par.error('/storage contiene archivos; no se ocultarán.')
    print('Se montará ' + str(pth) + ' en /storage. /work seguirá siendo RAM.')
    if not os.isatty(0) or input('Escribir MONTAR para continuar: ') != 'MONTAR':
        par.error('Sin autorización.')
    subprocess.run(['mount', '-t', 'ext4', '-o', 'nosuid,nodev,noexec', str(pth), '/storage'], check=True)
    dst.chmod(0o700)
    print('Almacenamiento disponible en /storage. No copiar claves ni historiales sin revisar.')


if __name__ == '__main__':
    main()
