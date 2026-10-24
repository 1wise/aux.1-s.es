#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Render a standalone Kickstart; do not download, compile or deploy an ISO."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess

DIR_APP = Path(__file__).resolve().parent
VERSION = '6.3.0-dev.2'
COMANDOS = ['bash', 'links', 'tmux', 'nano', 'less', 'wget', 'curl', 'ftp', 'ssh', 'runuser',
            'sshd', 'ssh-keygen', 'rpm', 'dnf', 'ip', 'nmcli', 'nmtui', 'dig',
            'ping', 'ethtool', 'tcpdump', 'wg', 'mount', 'umount', 'chroot', 'tar',
            'gzip', 'bzip2', 'xz', 'zstd', 'rsync', 'lsblk', 'blkid', 'parted',
            'gdisk', 'e2fsck', 'fsck.fat', 'xfs_repair', 'btrfs', 'ntfsfix',
            'cryptsetup', 'lvm', 'mdadm', 'smartctl', 'nvme', 'ddrescue', 'testdisk',
            'photorec', 'efibootmgr', 'grub2-install', 'chvt', 'find', 'grep', 'sed',
            'awk', 'ps', 'free', 'pstree', 'diff', 'sha256sum', 'stat', 'wpa_supplicant']


def paquetes(pth):
    dat = []
    for lin in pth.read_text().splitlines():
        nom = lin.split('#', 1)[0].strip()
        if not nom:
            continue
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9+_.-]*', nom):
            raise ValueError(f'Invalid package name: {nom}')
        if nom not in dat:
            dat.append(nom)
    return dat


def valida_receta(txt):
    # A valid Kickstart can still contain directives that Lorax explicitly rejects.
    for lin in txt.split('%packages', 1)[0].splitlines():
        tok = shlex.split(lin, comments=True)
        if tok and tok[0] in ('text', 'cmdline', 'graphical'):
            raise ValueError('Lorax controls display mode; remove ' + tok[0] + ' from Kickstart.')


def render(pth_sal, pth_per=None, pth_cfg=None):
    if pth_sal.exists():
        raise FileExistsError('Use a new output directory; existing recipes are preserved.')
    txt = (DIR_APP / 'assist.ks.in').read_text()
    valida_receta(txt)
    dat = paquetes(DIR_APP / 'packages.txt')
    # A random, undisclosed password leaves the SSH account unlocked without
    # introducing a reusable root password. SSH password auth remains disabled.
    cla = subprocess.run(['openssl', 'passwd', '-6', '-stdin'],
                         input=secrets.token_urlsafe(48) + '\n', text=True,
                         capture_output=True, check=True).stdout.strip()
    if not cla.startswith('$6$'):
        raise RuntimeError('OpenSSL did not produce a SHA-512 password hash.')
    files = []
    for arc in sorted((DIR_APP / 'payload').iterdir()):
        if not arc.is_file() or arc.suffix not in ('.py', '.sh', '.service'):
            continue
        dst = '/etc/systemd/system/' if arc.suffix == '.service' else '/usr/share/aux-assist/'
        files.append({'path': dst + arc.name, 'mode': 0o644,
                      'data': base64.b64encode(arc.read_bytes()).decode()})
    # Public profiles only: never package WireGuard private keys in a generic ISO.
    import importlib.util
    spec = importlib.util.spec_from_file_location('aux_assist', DIR_APP / 'payload/assist.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    per = mod.valida_perfiles(json.loads(pth_per.read_text()) if pth_per else [])
    cfg_cli = json.loads((DIR_APP / 'cli.json').read_text())
    spec_ia = importlib.util.spec_from_file_location('aux_ai', DIR_APP / 'payload/ai.py')
    ia = importlib.util.module_from_spec(spec_ia)
    spec_ia.loader.exec_module(ia)
    cfg_ia = json.loads((DIR_APP / 'ai.json').read_text())
    if pth_cfg:
        # Export public endpoints only; a generic ISO must never carry server secrets.
        central = json.loads(pth_cfg.read_text())
        cfg_cli = {'nodes': {nom: {'url': ent['url']} for nom, ent in
            central['cli']['nodes'].items()}}
        cfg_ia = central.get('ai', cfg_ia)
    cfg_ia = ia.valida_cfg(cfg_ia)
    for nom, txt_dat in [('profiles.json', json.dumps(per, ensure_ascii=False)),
                     ('cli.json', json.dumps(cfg_cli)),
                     ('ai.json', json.dumps(cfg_ia)),
                     ('packages-requested.txt', '\n'.join(dat) + '\n')]:
        files.append({'path': '/usr/share/aux-assist/' + nom, 'mode': 0o644,
                      'data': base64.b64encode(txt_dat.encode()).decode()})
    payload = base64.b64encode(json.dumps(files).encode()).decode()
    for tok, val in {'@ROOT_HASH@': cla, '@PACKAGES@': '\n'.join(dat),
                     '@PAYLOAD@': payload, '@COMMANDS@': repr(COMANDOS)}.items():
        txt = txt.replace(tok, val)
    if re.search(r'@[A-Z_]+@', txt):
        raise RuntimeError('An unresolved template field remains.')
    pth_sal.mkdir(parents=True)
    (pth_sal / 'assist.ks').write_text(txt)
    (pth_sal / 'packages-requested.txt').write_text('\n'.join(dat) + '\n')
    (pth_sal / 'source-manifest.json').write_text(json.dumps({
        'version': VERSION, 'wifi': 'NetworkManager-wifi' in dat,
        'kickstart_sha256': hashlib.sha256(txt.encode()).hexdigest(),
        'sources': {arc.relative_to(DIR_APP).as_posix(): hashlib.sha256(arc.read_bytes()).hexdigest()
                    for arc in sorted(DIR_APP.rglob('*')) if arc.is_file()
                    and arc.suffix in ('.py', '.sh', '.service', '.in', '.conf', '.txt', '.json')
                    and arc.name != 'manifest.json'
                    and (len(arc.relative_to(DIR_APP).parts) == 1
                         or arc.relative_to(DIR_APP).parts[0] == 'payload')},
    }, indent=2) + '\n')
    print(f'Prepared {pth_sal / "assist.ks"}: {len(dat)} requested packages; Wi-Fi included.')


if __name__ == '__main__':
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--output', required=True, type=Path)
    # Retain the previous command-line flag; Wi-Fi is now part of packages.txt.
    par.add_argument('--wifi', action='store_true', help='Compatibility option; Wi-Fi is included by default.')
    par.add_argument('--profiles', type=Path)
    par.add_argument('--config', type=Path, help='Central fast-boot.json; public CLI URLs and AI model choices only')
    cfg = par.parse_args()
    render(cfg.output.resolve(), cfg.profiles, cfg.config)
