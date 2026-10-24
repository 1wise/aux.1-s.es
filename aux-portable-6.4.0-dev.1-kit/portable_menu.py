#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Render one USB boot menu for a compressed Live base and persistent changes."""
import json
import re
import uuid

VERSION = '6.4.0-dev.1'
SCHEMA = 'aux-portable-v1'
ARG_COMUN = 'rd.live.image rd.live.overlay.overlayfs=1 aux.assist aux.ai.available=1 rd.luks=0 rd.lvm=0 rd.md=0'


def identidad(txt):
    return str(uuid.UUID(txt))


def parametros(uid, persistente):
    uid = identidad(uid)
    base = f'root=live:UUID={uid} {ARG_COMUN} aux.usb={uid}'
    if persistente:
        return base + f' rd.live.dir=/LiveOS/base rd.live.overlay=UUID={uid}:/AUX/persist/upper aux.persist=1 rw'
    # The clean directory has no automatic overlay; dracut creates its RAM overlay.
    return base + ' rd.live.dir=/LiveOS/clean aux.persist=0'


def entrada(titulo, nom, ker, ini, args):
    for pth in (ker, ini):
        if not re.fullmatch(r'/[A-Za-z0-9_./+-]+', pth) or '..' in pth.split('/'):
            raise ValueError('Ruta de arranque no válida.')
    return f"menuentry '{titulo}' --id {nom} {{\n    linux {ker} {args}\n    initrd {ini}\n}}\n"


def menu(uid):
    uid = identidad(uid)
    per, ram = parametros(uid, True), parametros(uid, False)
    txt = f'''# Timestamp: 2026-10-24 | Version: {VERSION}
# Author & Credits: https://www.alawise.es/1-s
search --no-floppy --fs-uuid --set=root {uid}
set default=aux-persistent
set timeout=5
set timeout_style=menu
set color_normal=green/black
set menu_color_normal=green/black
set menu_color_highlight=blue/black
if [ -f /AUX/boot/entries.cfg ]; then
    source /AUX/boot/entries.cfg
else
'''
    txt += entrada('AUX Assist / local personalizable', 'aux-persistent',
                   '/AUX/base/vmlinuz', '/AUX/base/initrd.img', per)
    txt += 'fi\n'
    txt += entrada('AUX Assist / local limpio en RAM', 'aux-clean',
                   '/AUX/base/vmlinuz', '/AUX/base/initrd.img', ram)
    txt += '''menuentry 'WAN Arsenal / iPXE network boot' --id aux-network {
    if [ "$grub_platform" = "efi" ]; then
        chainloader /AUX/ipxe/ipxe.efi
    else
        linux16 /AUX/ipxe/ipxe.lkrn
    fi
}
if [ "$grub_platform" = "efi" ]; then
    menuentry 'Configuracion del firmware UEFI' { fwsetup; }
fi
menuentry 'Reiniciar' { reboot; }
menuentry 'Apagar' { halt; }
'''
    return txt


def kernels(uid, actual, anterior=None):
    args = parametros(uid, True)
    est = {'current': actual, 'previous': anterior}
    txt = '# AUXSTATE ' + json.dumps(est, separators=(',', ':')) + '\n'
    for dat, titulo, nom in ((actual, 'AUX Assist / local personalizable', 'aux-persistent'),
                             (anterior, 'AUX Assist / kernel anterior', 'aux-previous')):
        if not dat:
            continue
        if not re.fullmatch(r'[A-Za-z0-9_.+-]{1,160}', dat['version']):
            raise ValueError('Versión de kernel no válida.')
        txt += entrada(titulo + ' / ' + dat['version'], nom,
                       dat['path'] + '/vmlinuz', dat['path'] + '/initrd.img', args)
    return txt


def stub(uid):
    return f'search --no-floppy --fs-uuid --set=root {identidad(uid)}\nconfigfile /AUX/menu.cfg\n'
