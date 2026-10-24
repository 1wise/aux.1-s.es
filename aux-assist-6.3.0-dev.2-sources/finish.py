#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Finish GRUB on a new ISO; preserve the source image and its BIOS/UEFI boot layout."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def configura(txt):
    # Only images declaring the new payload may advertise AI boot selections.
    if 'aux.ai.available=1' in txt and "--id aux-ai-openai" not in txt:
        bloques = re.finditer(r'(?m)^menuentry[^\n]*\{[ \t]*\n(?P<body>[\s\S]*?)^\}[ \t]*$', txt)
        cuerpo = next((ent['body'] for ent in bloques if
                       re.search(r'(?m)^\s*linux(?:efi|16)?\s+[^\n]*aux\.ai\.available=1', ent['body'])), None)
        if cuerpo is None:
            raise ValueError('AI marker found but no supported GRUB Linux entry; review the source configuration.')
        for prov, titulo in [('openai', 'GPT Assist'), ('gemini', 'Gemini Assist')]:
            nuevo = re.sub(r'(?m)^(\s*linux(?:efi|16)?\s+[^\n]*)$',
                lambda ent: re.sub(r'\s+aux\.ai=(?:openai|gemini)\b', '', ent[1]) + ' aux.ai=' + prov, cuerpo)
            txt += f"\nmenuentry '{titulo} / API (optional)' --id aux-ai-{prov} {{\n" + nuevo + '}\n'
    txt = re.sub(r'(?m)^\s*set default=.*$', 'set default=0', txt)
    txt = re.sub(r'(?m)^\s*set timeout=.*$', 'set timeout=5', txt)
    txt += '\nset default=0\nset timeout=5\nset color_normal=green/black\nset menu_color_normal=green/black\nset menu_color_highlight=blue/black\n'
    if 'fwsetup' not in txt:
        txt += '''if [ "$grub_platform" = "efi" ]; then
menuentry 'UEFI firmware settings' { fwsetup; }
fi
'''
    return txt


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--input', required=True, type=Path)
    par.add_argument('--output', required=True, type=Path)
    cfg = par.parse_args()
    if not cfg.input.is_file() or cfg.output.exists() or cfg.input.resolve() == cfg.output.resolve():
        par.error('Existing input and a NEW output path are required')
    for nom in ['xorriso', 'implantisomd5', 'checkisomd5']:
        if not shutil.which(nom):
            par.error('Missing dependency: ' + nom)
    with tempfile.TemporaryDirectory(prefix='aux-grub-') as tmp:
        cambios = []
        for idx, rel in enumerate(['/boot/grub2/grub.cfg', '/EFI/BOOT/grub.cfg']):
            arc = Path(tmp) / ('grub-' + str(idx) + '.cfg')
            rsp = subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(cfg.input),
                '-extract', rel, str(arc)], capture_output=True)
            if rsp.returncode == 0 and arc.is_file():
                arc.write_text(configura(arc.read_text()))
                cambios += ['-map', str(arc), rel]
        if not cambios:
            raise RuntimeError('No supported Fedora GRUB configuration found')
        # Replay after mapping preserves recognizable hybrid/El Torito boot structures.
        subprocess.run(['xorriso', '-indev', str(cfg.input), '-outdev', str(cfg.output),
            *cambios, '-boot_image', 'any', 'replay', '-commit', '-end'], check=True)
    subprocess.run(['implantisomd5', '--force', str(cfg.output)], check=True)
    subprocess.run(['checkisomd5', '--verbose', str(cfg.output)], check=True)
    dig = hashlib.file_digest(cfg.output.open('rb'), 'sha256').hexdigest()
    cfg.output.with_suffix(cfg.output.suffix + '.sha256').write_text(dig + '  ' + cfg.output.name + '\n')
    print('Finished ISO; BIOS/UEFI boot and Secure Boot acceptance remain separate tests.')


if __name__ == '__main__':
    main()
