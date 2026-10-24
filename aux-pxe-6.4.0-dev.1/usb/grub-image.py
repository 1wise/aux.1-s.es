#!/usr/bin/env python3
# Timestamp: 2026-10-12 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Package existing iPXE binaries behind GRUB; never open a block device."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    arg = argparse.ArgumentParser(description=__doc__)
    for nom in ('mkrescue', 'bios', 'efi', 'config', 'output'):
        arg.add_argument('--' + nom, required=True)
    cfg = arg.parse_args()
    pth_out = Path(cfg.output).absolute()
    if pth_out.exists() and not pth_out.is_file():
        arg.error('Output must be a regular image file')
    # GRUB hybrid output includes ISO9660, BIOS boot code and an EFI System Partition.
    # A single-platform host installation must not silently produce half a USB client.
    mod_root = Path('/usr/lib/grub')
    for arch in ('i386-pc', 'x86_64-efi'):
        if not (mod_root / arch / 'modinfo.sh').is_file():
            arg.error('Missing GRUB modules: ' + str(mod_root / arch))
    with tempfile.TemporaryDirectory(prefix='aux-grub-') as tmp:
        pth = Path(tmp)
        (pth / 'boot/grub').mkdir(parents=True)
        (pth / 'ipxe').mkdir()
        for src, rel in ((cfg.bios, 'ipxe/ipxe.lkrn'), (cfg.efi, 'ipxe/ipxe.efi'),
                         (cfg.config, 'boot/grub/grub.cfg')):
            arc = Path(src)
            if not arc.is_file() or not arc.stat().st_size:
                arg.error('Missing or empty source: ' + str(arc))
            shutil.copy2(arc, pth / rel)
        # Do not pass --directory: it selects only one platform in grub-mkrescue.
        subprocess.run([cfg.mkrescue, '--output=' + str(pth_out), '--themes=', '--locales=',
                        '--fonts=', str(pth)], check=True)


if __name__ == '__main__':
    main()
