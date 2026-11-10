# Timestamp: 2026-11-09 | Version: 7.0.0-dev.3
# Author & Credits: https://www.alawise.es/1-s
"""Inspect detected devices or enter one explicitly selected Linux root."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid
import copy

from .common import ejecuta


def detecta():
    res = subprocess.run(['lsblk', '--json', '--paths', '--output', 'NAME,TYPE,FSTYPE,LABEL,UUID,SIZE,MOUNTPOINTS'], text=True, capture_output=True, check=True)
    return json.loads(res.stdout)['blockdevices']


def opciones(fmt, escritura):
    if fmt not in ('ext2', 'ext3', 'ext4', 'xfs', 'btrfs'):
        raise ValueError('Formato raíz no admitido: ' + fmt)
    if escritura:
        return 'rw'
    return {'ext2':'ro', 'ext3':'ro,noload', 'ext4':'ro,noload',
            'xfs':'ro,norecovery', 'btrfs':'ro,nologreplay'}[fmt]


def monta(cmd, montajes, destino):
    ejecuta(cmd, True)
    montajes.append(destino)


def limpia(montajes):
    fallos = []
    for dst in reversed(montajes):
        # Never use lazy unmount: it would hide live references during cleanup.
        res = subprocess.run(['umount', str(dst)], check=False)
        if res.returncode:
            fallos.append(str(dst))
            break
    if fallos:
        raise RuntimeError('Montaje ocupado; se conserva el directorio de trabajo: ' + ', '.join(fallos))


def entra(cfg):
    dev = cfg.device.resolve()
    if not dev.is_block_device():
        raise ValueError('Seleccionar un dispositivo de bloques existente, normalmente /dev/mapper/... para LUKS/LVM.')
    dat = subprocess.run(['blkid', '-o', 'value', '-s', 'TYPE', str(dev)], text=True, capture_output=True, check=True).stdout.strip()
    if dat == 'crypto_LUKS':
        if not cfg.unlock:
            raise ValueError('Raíz LUKS: añadir --unlock para abrir un mapeo temporal con contraseña local.')
        print('Desbloqueo LUKS temporal de', dev, '; la contraseña se solicita en la terminal local.')
        if not cfg.apply:
            return
        if os.geteuid() != 0:
            raise ValueError('--apply requiere root.')
        nom = 'aux-' + uuid.uuid4().hex[:16]
        cmd = ['cryptsetup', 'open'] + ([] if cfg.repair else ['--readonly']) + [str(dev), nom]
        ejecuta(cmd, True)
        try:
            sig = copy.copy(cfg)
            sig.device = Path('/dev/mapper') / nom
            sig.unlock = False
            entra(sig)
        finally:
            ejecuta(['cryptsetup', 'close', nom], True)
        return
    opt = opciones(dat, cfg.repair)
    if cfg.subvolume:
        if dat != 'btrfs' or any(val in cfg.subvolume for val in ('..', ',', '\n', '\x00')) or not cfg.subvolume.startswith('@'):
            raise ValueError('Subvolumen Btrfs inválido; ejemplo: @ o @rootfs.')
        opt += ',subvol=' + cfg.subvolume
    print('Destino:', dev, '| formato:', dat, '| opciones:', opt)
    if not cfg.repair:
        print('Inspección de solo lectura del sistema de archivos; no se declara adquisición forense.')
    if cfg.apply and os.geteuid() != 0:
        raise ValueError('--apply requiere root.')
    if cfg.repair and not cfg.apply:
        print('El plan de reparación requiere --apply y confirmación local del dispositivo.')
    if not cfg.apply:
        return
    if cfg.repair and not (cfg.namespace and cfg.confirmed_device == str(dev)) and input('Escribir REPARAR ' + str(dev) + ': ').strip() != 'REPARAR ' + str(dev):
        raise ValueError('Reparación no autorizada.')
    # A private mount namespace prevents propagation into unrelated host mounts.
    if not cfg.namespace:
        import sys
        cmd = ['unshare', '--mount', '--propagation', 'private', sys.executable,
               str(Path(__file__).resolve().parent.parent / 'aux-enter'),
               '--device', str(dev), '--apply', '--namespace']
        if cfg.repair:
            cmd += ['--repair', '--confirmed-device', str(dev)]
        if cfg.subvolume:
            cmd += ['--subvolume', cfg.subvolume]
        ejecuta(cmd, True)
        return
    pth = Path(tempfile.mkdtemp(prefix='aux-enter-', dir='/run'))
    pth.chmod(0o700)
    montajes = []
    try:
        monta(['mount', '-t', dat, '-o', opt, str(dev), str(pth)], montajes, pth)
        osr = pth / 'etc/os-release'
        if not osr.resolve().is_relative_to(pth) or not osr.is_file():
            raise ValueError('La raíz elegida no contiene etc/os-release regular dentro del destino.')
        print(osr.read_text()[:4096])
        if not cfg.repair:
            print('Raíz montada en', pth, '. La inspección termina con exit.')
            subprocess.run(['/bin/bash', '--noprofile', '--norc'], cwd=pth,
                           env=os.environ | {'PS1':'AUX inspection \\w $ '}, check=True)
            return
        for nom in ('bin/sh', 'usr/bin/env'):
            dst = pth / nom
            if not dst.exists():
                raise ValueError('Raíz incompleta o arquitectura no compatible: ' + nom)
        # Compare ELF machine identifiers without running target binaries first.
        def maquina(arc):
            with arc.open('rb') as stream:
                byt = stream.read(20)
            if byt[:4] != b'\x7fELF':
                raise ValueError('Ejecutable ELF requerido.')
            return byt[4:6], byt[18:20]
        dst_env = pth / 'usr/bin/env'
        if not dst_env.resolve().is_relative_to(pth) or maquina(dst_env) != maquina(Path('/usr/bin/env')):
            raise ValueError('Arquitectura del destino incompatible con el entorno de rescate.')
        for nom in ('dev', 'dev/pts', 'proc', 'sys'):
            dst = pth / nom
            if dst.is_symlink() or (dst.exists() and not dst.is_dir()):
                raise ValueError('Punto de montaje de destino inválido: ' + nom)
            dst.mkdir(exist_ok=True)
            monta(['mount', '--bind', '/' + nom, str(dst)], montajes, dst)
        ejecuta(['chroot', str(pth), '/usr/bin/env', '-i', 'HOME=/root', 'PATH=/usr/sbin:/usr/bin:/sbin:/bin',
                 'TERM=' + os.environ.get('TERM', 'linux'), 'PS1=AUX repair \\w # ', '/bin/sh', '-i'], True)
    finally:
        limpia(montajes)
        pth.rmdir()


def main(argv=None):
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--list', action='store_true')
    par.add_argument('--device', type=Path)
    par.add_argument('--subvolume')
    par.add_argument('--unlock', action='store_true')
    par.add_argument('--repair', action='store_true')
    par.add_argument('--apply', action='store_true')
    par.add_argument('--namespace', action='store_true', help=argparse.SUPPRESS)
    par.add_argument('--confirmed-device', help=argparse.SUPPRESS)
    par.add_argument('--interactive',action='store_true')
    cfg = par.parse_args(argv)
    if cfg.interactive:
        from .interactive import elige
        lst=[]
        def visita(ents):
            for ent in ents:
                if ent.get('fstype') in ('ext2','ext3','ext4','xfs','btrfs','crypto_LUKS') and '/' not in (ent.get('mountpoints') or []):
                    lst.append(ent)
                visita(ent.get('children',[]))
        visita(detecta())
        if not lst:
            print('No hay raíces candidatas. Para LVM, activar y seleccionar el volumen lógico.')
            return
        ent=elige('Elegir el sistema de destino',[(val['name']+' | '+str(val.get('label') or '')+' | '+str(val.get('fstype'))+' | '+str(val.get('size')),val) for val in lst])
        cfg.device=Path(ent['name']);cfg.unlock=ent['fstype']=='crypto_LUKS'
        cfg.repair=elige('Modo de entrada',[('Inspeccion de solo lectura',False),('Reparacion mediante chroot',True)])
        if ent['fstype']=='btrfs':
            cfg.subvolume=input('Subvolumen Btrfs [Enter: raiz superior]: ').strip() or None
        entra(cfg)
        if input('Escribir ABRIR para continuar [Enter vuelve]: ').strip()!='ABRIR':
            return
        cfg.apply=True
        entra(cfg)
        return
    if cfg.list or not cfg.device:
        print(json.dumps(detecta(), ensure_ascii=False, indent=2))
        return
    entra(cfg)
