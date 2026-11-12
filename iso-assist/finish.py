#!/usr/bin/env python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Finish GRUB on a new ISO; preserve the source image and its BIOS/UEFI boot layout."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auxlib import wan_boot


def capacidades(pth):
    dat=json.loads(Path(pth).read_text())
    if (dat.get('schema')!='aux-live-source-v1' or dat.get('human_terminal_count')!=2 or
        dat.get('terminal_protocol')!=2 or dat.get('fedora_release')!=45 or
        not re.fullmatch(r'[a-f0-9]{64}',dat.get('suite_sha256','')) or
        not re.fullmatch(r'[a-f0-9]{64}',dat.get('tmux_config_sha256','')) or
        not re.fullmatch(r'[0-9A-Za-z._-]{1,64}',dat.get('version',''))):
        raise ValueError('Invalid AUX Live source manifest')
    return {'schema':'aux-live-capabilities-v1','version':dat['version'],
        'fedora_release':45,'human_terminal_count':2,'terminal_protocol':2,
        'suite_sha256':dat['suite_sha256'],'applications':dat['applications'],
        'tmux_config_sha256':dat['tmux_config_sha256'],'tmux_config_verified':False,
        'source_manifest_sha256':hashlib.sha256(Path(pth).read_bytes()).hexdigest(),
        'boot_verified':False,'acceptance':'source declaration; hardware tests pending'}


def verifica_tmux_iso(pth_iso,pth_tmp,sha_cfg):
    img=pth_tmp/'rootfs.squashfs'
    res=subprocess.run(['xorriso','-osirrox','on','-indev',str(pth_iso),
        '-extract','/LiveOS/squashfs.img',str(img)],capture_output=True)
    if res.returncode or not img.is_file():
        raise RuntimeError('Cannot inspect Live rootfs /LiveOS/squashfs.img: '+res.stderr.decode(errors='replace')[-1200:])
    # Read the compressed filesystem without mounting or modifying the installer image.
    res=subprocess.run(['unsquashfs','-cat',str(img),'usr/share/aux-assist/tmux.conf'],capture_output=True)
    if res.returncode or not res.stdout:
        raise RuntimeError('The ISO rootfs has no readable /usr/share/aux-assist/tmux.conf: '+res.stderr.decode(errors='replace')[-1200:])
    if hashlib.sha256(res.stdout).hexdigest()!=sha_cfg:
        raise RuntimeError('The ISO tmux configuration differs from the prepared source manifest')


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
    txt += '\nset color_normal=green/black\nset menu_color_normal=green/black\nset menu_color_highlight=blue/black\n'
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
    par.add_argument('--source-manifest',type=Path,help='Prepared source-manifest.json; publish declared Live capabilities')
    cfg = par.parse_args()
    cap=capacidades(cfg.source_manifest) if cfg.source_manifest else None
    if not cfg.input.is_file() or cfg.output.exists() or cfg.input.resolve() == cfg.output.resolve():
        par.error('Existing input and a NEW output path are required')
    for nom in ['xorriso', 'implantisomd5', 'checkisomd5']:
        if not shutil.which(nom):
            par.error('Missing dependency: ' + nom)
    if cap and not shutil.which('unsquashfs'):
        par.error('Missing dependency: unsquashfs (squashfs-tools)')
    with tempfile.TemporaryDirectory(prefix='aux-grub-', dir=cfg.output.parent) as tmp:
        if cap:
            verifica_tmux_iso(cfg.input,Path(tmp),cap['tmux_config_sha256'])
            cap['tmux_config_verified']=True
        cambios, cola, archivos, wan = wan_boot.prepara_iso(cfg.input, Path(tmp) / 'wan', configura)
        if cap:
            cap['wan_boot'] = wan
            arc_cap=Path(tmp)/'aux-live.json'
            arc_cap.write_text(json.dumps(cap,indent=2)+'\n')
            cambios+=['-map',str(arc_cap),'/aux-live.json']
        # Read back the modified boot files before publishing a final output name.
        parcial = Path(tmp) / 'finished.iso'
        subprocess.run(['xorriso', '-abort_on', 'FAILURE', '-indev', str(cfg.input), '-outdev', str(parcial),
            *cambios, '-boot_image', 'any', 'replay', *cola, '-commit', '-end'], check=True)
        subprocess.run(['implantisomd5', '--force', str(parcial)], check=True)
        subprocess.run(['checkisomd5', '--verbose', str(parcial)], check=True)
        wan_boot.verifica_iso(parcial, archivos, Path(tmp) / 'readback')
        # A same-filesystem link publishes complete bytes without overwriting a concurrent file.
        os.link(parcial, cfg.output)
    dig = hashlib.file_digest(cfg.output.open('rb'), 'sha256').hexdigest()
    cfg.output.with_suffix(cfg.output.suffix + '.sha256').write_text(dig + '  ' + cfg.output.name + '\n')
    print('Finished ISO; BIOS/UEFI boot and Secure Boot acceptance remain separate tests.')


if __name__ == '__main__':
    main()
