#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Check Fedora's actual EFI media inputs before Lorax packages the Live image."""
from pathlib import Path
import shutil

ARCHIVOS_EFI = ('boot/efi/EFI/fedora/gcdx64.efi',
                'boot/efi/EFI/fedora/shimx64.efi',
                'boot/efi/EFI/fedora/mmx64.efi',
                'usr/share/grub/unicode.pf2')


def prepara_efi(pth_root=Path('/')):
    # Fedora 44 stores versioned RPM payloads under /usr; Lorax still reads /boot.
    for nom in ARCHIVOS_EFI[:3]:
        dst = pth_root / nom
        if dst.is_file() and dst.stat().st_size:
            continue
        pkg = 'grub2' if dst.name == 'gcdx64.efi' else 'shim'
        fuentes = [pth for pth in (pth_root / 'usr/lib/efi' / pkg).glob('*/EFI/fedora/' + dst.name)
                   if pth.is_file() and pth.stat().st_size
                   and pth.resolve().is_relative_to(pth_root.resolve())]
        if len(fuentes) != 1:
            raise RuntimeError('Expected one installed RPM payload for ' + dst.name +
                               f'; found {len(fuentes)}. Check grub2-efi-x64-cdboot and shim-x64.')
        if not dst.resolve().is_relative_to(pth_root.resolve()):
            raise RuntimeError('EFI destination escapes image root: ' + str(dst))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fuentes[0], dst)
    return valida_efi(pth_root)


def valida_efi(pth_root=Path('/')):
    aus = [nom for nom in ARCHIVOS_EFI
           if not (pth_root / nom).is_file() or (pth_root / nom).stat().st_size == 0]
    if aus:
        raise RuntimeError('Missing EFI media inputs: ' + ', '.join(aus) +
                           '. Check grub2-efi-x64-cdboot, shim-x64 and grub2-tools inside the image.')
    # Presence is a packaging prerequisite; firmware and signature checks still need boot tests.
    return list(ARCHIVOS_EFI)


if __name__ == '__main__':
    for nom in valida_efi():
        print('EFI input verified: /' + nom)
