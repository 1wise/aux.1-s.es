#!/usr/bin/python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Check browser registration, terminal tools and terminfo inside the new Live."""
import shutil
import subprocess
from pathlib import Path


def prepara_links():
    if shutil.which('links'):
        return
    if not shutil.which('/usr/bin/links2'):
        raise RuntimeError('Missing executable /usr/bin/links2 from the links RPM.')
    exe=shutil.which('update-alternatives')
    if not exe:
        raise RuntimeError('Missing update-alternatives required by the links RPM.')
    # Fedora's RPM post-install script registers links only if its manpage exists.
    # --excludedocs removes that manpage; register the same binary without a slave.
    subprocess.run([exe,'--install','/usr/bin/links','links','/usr/bin/links2','80'],check=True)
    if not shutil.which('links'):
        raise RuntimeError('The links alternative is still unavailable after registration.')


def prepara_terminales():
    faltan=[nom for nom in ('clear','tput','reset','infocmp') if not shutil.which(nom)]
    if faltan:
        raise RuntimeError('Missing ncurses utilities: '+', '.join(faltan))
    # tmux and the browser need matching terminal definitions, not just shared libraries.
    for sys_nom in ('linux','xterm-256color','screen-256color','tmux-256color'):
        res=subprocess.run(['infocmp','-x',sys_nom],capture_output=True,text=True)
        if res.returncode:
            raise RuntimeError('Missing terminfo entry '+sys_nom+': '+res.stderr[-1200:])


def verifica_tmux(pth_raiz=Path('/')):
    cfg=pth_raiz/'usr/share/aux-assist/tmux.conf'
    src=pth_raiz/'usr/local/lib/aux/config/tmux.conf'
    if not cfg.is_file() or cfg.is_symlink():
        raise RuntimeError('Missing regular Live tmux configuration: '+str(cfg))
    if not src.is_file() or not cfg.read_bytes() or cfg.read_bytes()!=src.read_bytes():
        raise RuntimeError('Live tmux configuration differs from the verified AUX sources')
    if cfg.stat().st_mode & 0o777 != 0o644:
        raise RuntimeError('Live tmux configuration must have mode 0644')


if __name__=='__main__':
    prepara_links()
    prepara_terminales()
    verifica_tmux()
