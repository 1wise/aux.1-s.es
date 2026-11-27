# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Render optional local-media recipes for catalogued Microsoft and Apple origins."""

from . import VERSION

# Only known profiles can select commands or supply an iPXE label.
WINDOWS = {
    'win11-26h2-x64': ('Windows 11 26H2 x64', ('x86_64',)),
    'win11-26h2-arm64': ('Windows 11 26H2 ARM64', ('arm64',)),
    'win11-24h2-ltsc': ('Windows 11 LTSC 2024', ('x86_64', 'arm64')),
    'win10-21h2-iot-ltsc': ('Windows 10 LTSC 2021', ('x86_64',)),
    'winserv-2025': ('Windows Server 2025', ('x86_64',)),
    'winpe-11-adk': ('Windows PE / ADK', ('x86_64', 'arm64')),
}
MAC = {
    'opencore-1.0.8': ('OpenCore / Intel EFI', 'chain', 'opencore-1.0.8/EFI/OC/OpenCore.efi'),
    'macos-26-tahoe': ('Tahoe Recovery / Intel EFI', 'sanboot', 'macos-26-tahoe/tahoe-recovery-oc108.img'),
    'macos-15-sequoia': ('Sequoia Recovery / Intel EFI', 'sanboot', 'macos-15-sequoia/sequoia-recovery-oc108.img'),
    'macos-27-goldengate': ('Apple Silicon / Recovery information', 'info', ''),
}


def plantilla(ent):
    clave = ent['id'].removeprefix('origin-')
    if ent['id'] == clave:
        return None
    if clave in WINDOWS:
        return 'sub_win.ipxe'
    if clave in MAC and MAC[clave][1] != 'info':
        return 'sub_mac.ipxe'
    return None


def seleccion(cat, perfiles):
    ids = {e['id'] for e in cat['entries']}
    return {k: v for k, v in perfiles.items() if 'origin-' + k in ids}


def cabecera(titulo):
    return ['#!ipxe', '# Timestamp: 2026-11-28 | Version: ' + VERSION,
            '# Author & Credits: https://www.alawise.es/1-s', ':start', 'menu ' + titulo]


def elige():
    return ['item back Return', 'choose --default back choice || goto back', 'goto ${choice}']


def cierre():
    return [':error', 'imgfree', 'echo Check local media paths and firmware compatibility.',
            'prompt Press a key to return...', 'goto start', ':back', 'exit 0', '']


def windows(perfiles):
    lin = cabecera('AUX / Windows / local WinPE media')
    lin += ['set aux_win_arch ${buildarch}',
            'iseq ${platform} pcbios && cpuid --ext 29 && set aux_win_arch x86_64 ||']
    for k, (nombre, arqs) in perfiles.items():
        for arq in arqs:
            lin.append('iseq ${buildarch} ' + arq + ' && iseq ${platform} efi && item ' + k + ' ' + nombre + ' ||')
        if k in ('winpe-11-adk', 'win10-21h2-iot-ltsc'):
            lin.append('iseq ${aux_win_arch} x86_64 && iseq ${platform} pcbios && item ' + k + ' ' + nombre + ' ||')
    lin += elige()
    for k in perfiles:
        lin += [':' + k, 'set aux_win_id ' + k, 'goto win_boot']
    lin += [':win_boot', 'isset ${aux_win_root} || set aux_win_root media/windows',
            'set aux_win_dir ${aux_win_root}/${aux_win_id}/${aux_win_arch}',
            'set aux_loader wimboot', 'iseq ${buildarch} arm64 && set aux_loader wimboot.arm64 ||',
            'imgfree', 'iseq ${aux_win_id} winpe-11-adk && goto winpe ||',
            'kernel ${aux_win_root}/bin/${aux_loader} index=2 || goto error',
            'initrd ${aux_win_dir}/pxe/winpeshl.ini winpeshl.ini || goto error',
            'initrd ${aux_win_dir}/pxe/install.bat install.bat || goto error',
            'goto load_wim', ':winpe', 'kernel ${aux_win_root}/bin/${aux_loader} index=1 || goto error',
            ':load_wim', 'initrd ${aux_win_dir}/sources/boot.wim boot.wim || goto error',
            'boot || goto error', 'goto start']
    return '\n'.join(lin + cierre())


def mac(perfiles):
    lin = cabecera('AUX / macOS / recovery')
    for k, (nombre, metodo, _) in perfiles.items():
        item = 'item ' + k + ' ' + nombre
        if metodo != 'info':
            item = 'iseq ${buildarch} x86_64 && iseq ${platform} efi && ' + item + ' ||'
        lin.append(item)
    lin += elige()
    for k, (_, metodo, ruta) in perfiles.items():
        lin.append(':' + k)
        if metodo == 'info':
            lin += ['echo Apple Silicon: start in macOS Recovery using startup options.',
                    'echo https://support.apple.com/en-us/102655', 'prompt Press a key to return...']
        else:
            cmd = 'chain --autofree' if metodo == 'chain' else 'sanboot --no-describe --drive 0x80'
            lin += ['isset ${aux_mac_root} || set aux_mac_root media/macos', 'imgfree',
                    cmd + ' ${aux_mac_root}/' + ruta + ' || goto error']
        lin.append('goto start')
    return '\n'.join(lin + cierre())


def menus(cat):
    salida = {}
    for nom, perfiles, genera in [('sub_win', WINDOWS, windows), ('sub_mac', MAC, mac)]:
        activos = seleccion(cat, perfiles)
        if activos:
            salida[nom] = genera(activos)
    return salida
