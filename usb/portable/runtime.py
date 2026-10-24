#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Bind persistent workspace and publish generic Live kernels on the booted USB only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
import portable_menu as menu

LIVE = Path('/run/initramfs/live')
CMDLINE = Path('/proc/cmdline')
MODULOS = Path('/usr/lib/modules')
BOOT = Path('/boot')
API_RUN = Path('/run/aux-api-source')
PROVEEDORES = {'openai': ('GPT', 'aux-gpt.service'), 'gemini': ('Gemini', 'aux-gemini.service')}


def orden(*args, **kwargs):
    return subprocess.run(list(args), check=True, **kwargs)


def sha(pth):
    with pth.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def argumentos(txt):
    return dict(ent.split('=', 1) for ent in txt.split() if '=' in ent)


def verifica(live=None):
    live=live or LIVE
    if os.geteuid() != 0:
        raise ValueError('Requiere root dentro del Live de la llave.')
    cmd = argumentos(CMDLINE.read_text())
    uid = menu.identidad(cmd.get('aux.usb', ''))
    if cmd.get('aux.persist') != '1' or not live.is_mount():
        raise ValueError('No se ha arrancado el modo USB personalizable.')
    dat = json.loads((live / 'AUX/manifest.json').read_text())
    if dat.get('schema') != menu.SCHEMA or dat.get('filesystem_uuid') != uid:
        raise ValueError('La identidad de la llave no coincide con el arranque.')
    fs = json.loads(orden('findmnt', '--json', '--target', str(live),
                        '--output', 'UUID,FSTYPE,TARGET', capture_output=True, text=True).stdout)['filesystems'][0]
    if fs['uuid'] != uid or fs['fstype'] != 'ext4' or fs['target'] != str(live):
        raise ValueError('El medio Live no es la partición ext4 prevista.')
    opts = orden('findmnt', '--noheadings', '--output', 'OPTIONS', '/', capture_output=True, text=True).stdout.strip()
    campos = argumentos(opts.replace(',', ' '))
    upper = campos.get('upperdir')
    esperado = live / 'AUX/persist/upper'
    if not upper or not os.path.samefile(upper, esperado):
        raise ValueError('La raíz no usa la persistencia prevista; detenerse y revisar el arranque.')
    return uid


def atomic(pth, byt):
    fd, nom = tempfile.mkstemp(prefix='.aux-', dir=pth.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(byt);stream.flush();os.fsync(stream.fileno())
        os.chmod(nom, 0o600)
        os.replace(nom, pth)
        fd_dir = os.open(pth.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:os.fsync(fd_dir)
        finally:os.close(fd_dir)
    finally:Path(nom).unlink(missing_ok=True)


def directorio_privado(pth, crear=False):
    if crear:
        pth.mkdir(mode=0o700, exist_ok=True)
    st = pth.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077:
        raise ValueError('El directorio de claves requiere propietario root y permisos 0700.')


def fuentes_api(crear=False):
    aux = LIVE / 'AUX'
    st = aux.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o022:
        raise ValueError('Directorio AUX no válido para credenciales privadas.')
    for pth in (aux / 'private', aux / 'private/api'):
        if not pth.exists() and not pth.is_symlink() and not crear:
            return None
        directorio_privado(pth, crear)
    return aux / 'private/api'


def lee_api(pth):
    fd = os.open(pth, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or st.st_mode & 0o077 or st.st_nlink != 1:
            raise ValueError('Archivo de clave no privado; requiere root y permisos 0600.')
        dat = os.read(fd, 515)
    finally:
        os.close(fd)
    if not dat:
        return b''
    # Bound reads and an exact printable token keep shell syntax and extra lines out.
    dat = dat.removesuffix(b'\n').removesuffix(b'\r')
    if not re.fullmatch(rb'[\x21-\x7e]{8,512}', dat):
        raise ValueError('Formato de clave preparada inválido.')
    return dat


def prepara_api(prov):
    if prov not in PROVEEDORES:
        raise ValueError('Proveedor API inválido.')
    verifica()
    directorio_privado(API_RUN, True)
    # Remove a previous staging copy before checking this insertion's source.
    atomic(API_RUN / (prov + '.key'), b'')
    src = fuentes_api()
    dat = b''
    if src:
        try:
            dat = lee_api(src / (prov + '.key'))
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            print('Clave preparada rechazada; G/M mantienen disponible la entrada manual.')
    atomic(API_RUN / (prov + '.key'), dat)
    print(PROVEEDORES[prov][0] + ': ' + ('clave preparada.' if dat else 'entrada manual disponible.'))


def limpia_api():
    if os.geteuid() != 0:
        raise ValueError('Requiere control local root.')
    if API_RUN.exists() or API_RUN.is_symlink():
        directorio_privado(API_RUN)
        for prov in PROVEEDORES:
            (API_RUN / (prov + '.key')).unlink(missing_ok=True)


def gestiona_api():
    verifica()
    orden('mount', '-o', 'remount,rw', str(LIVE))
    src = fuentes_api(True)
    while True:
        for prov, (nom, _) in PROVEEDORES.items():
            try:
                estado = 'preparada' if lee_api(src / (prov + '.key')) else 'vacía'
            except FileNotFoundError:
                estado = 'vacía'
            except (OSError, ValueError):
                estado = 'archivo no utilizable'
            print(nom + ': ' + estado)
        opt = input('G GPT / M Gemini / Enter volver: ').strip().lower()
        if not opt:
            return
        if opt not in ('g', 'm'):
            continue
        prov = 'openai' if opt == 'g' else 'gemini'
        opt = input('S guardar o sustituir / B borrar / Enter cancelar: ').strip().lower()
        if opt not in ('s', 'b'):
            continue
        dat = None
        if opt == 's':
            import ai
            dat = ai.pide_clave().encode('ascii')
        # Stop the old process before changing the persistent or in-memory credential.
        orden('systemctl', 'stop', PROVEEDORES[prov][1])
        directorio_privado(API_RUN, True)
        (API_RUN / (prov + '.key')).unlink(missing_ok=True)
        if dat is None:
            (src / (prov + '.key')).unlink(missing_ok=True)
            fd = os.open(src, os.O_RDONLY | os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        else:
            atomic(src / (prov + '.key'), dat + b'\n')
        os.sync()
        print('Clave ' + ('borrada.' if dat is None else 'guardada.'))


def workspace():
    verifica()
    # The kernel command line explicitly selected write access to this boot medium.
    orden('mount', '-o', 'remount,rw', str(LIVE))
    for nom in ('work', 'storage'):
        src, dst = LIVE / 'AUX/data' / nom, Path('/' + nom)
        src.mkdir(mode=0o700, parents=True, exist_ok=True)
        if dst.is_symlink() or dst.is_mount():
            raise ValueError(str(dst) + ' no es un punto de montaje libre.')
        dst.mkdir(mode=0o700, exist_ok=True)
        if any(dst.iterdir()):
            raise ValueError(str(dst) + ' contiene archivos; no se ocultarán.')
        orden('mount', '--bind', str(src), str(dst))
        orden('mount', '-o', 'remount,bind,nosuid,nodev' + (',noexec' if nom == 'storage' else ''), str(dst))
    arc=Path('/usr/share/aux-assist/assist.py')
    antes="SSH cerrado. /work y cambios del live se pierden al reiniciar."
    texto=arc.read_text()
    if antes in texto:
        # Overlay copy-up keeps the existing file's ownership and SELinux attributes.
        arc.write_text(texto.replace(antes,'SSH cerrado. USB persistente: sistema, /work y /storage se conservan.'))
    print('USB personalizable: sistema, /work y /storage se conservan en la llave.')


def version_instalada():
    txt = orden('rpm', '-q', '--qf', '%{INSTALLTIME}\t%{VERSION}-%{RELEASE}.%{ARCH}\n',
                'kernel-core', capture_output=True, text=True).stdout
    candidatos = []
    for lin in txt.splitlines():
        tms, ver = lin.split('\t')
        if re.fullmatch(r'[A-Za-z0-9_.+-]{1,160}', ver) and (MODULOS / ver).is_dir():
            candidatos.append((int(tms), ver))
    if not candidatos:raise ValueError('No se encuentra un kernel-core instalado con sus módulos.')
    recientes = [v for t,v in candidatos if t == max(t for t,_ in candidatos)]
    return orden('sort', '-V', input='\n'.join(recientes)+'\n', capture_output=True, text=True).stdout.splitlines()[-1]


def publica(ver):
    uid = verifica()
    if not re.fullmatch(r'[A-Za-z0-9_.+-]{1,160}', ver):raise ValueError('Versión de kernel no válida.')
    if not (MODULOS / ver).is_dir():raise ValueError('Faltan módulos del kernel solicitado.')
    ker = next((p for p in (MODULOS/ver/'vmlinuz', BOOT/('vmlinuz-'+ver)) if p.is_file()), None)
    if not ker:raise ValueError('No se encuentra vmlinuz para esa versión.')
    orden('mount', '-o', 'remount,rw', str(LIVE))
    boot = LIVE / 'AUX/boot'
    boot.mkdir(mode=0o700, exist_ok=True)
    previo = None
    cfg = boot / 'entries.cfg'
    if cfg.exists():
        cab = cfg.read_text().splitlines()[0]
        if not cab.startswith('# AUXSTATE '):raise ValueError('Estado de arranque no reconocido; no se reemplaza.')
        previo = json.loads(cab[len('# AUXSTATE '):])['current']
        if not (MODULOS/previo['version']).is_dir():previo=None
    nombre = ver + '-' + uuid.uuid4().hex[:8]
    tmp = boot / ('.' + nombre)
    dst = boot / nombre
    tmp.mkdir(mode=0o700)
    try:
        shutil.copy2(ker, tmp/'vmlinuz')
        # Generic Live initramfs is essential when moving the key between machines.
        orden('dracut', '--force', '--no-hostonly', '--no-hostonly-cmdline',
              '--add', 'dmsquash-live livenet network-manager', '--kver', ver, str(tmp/'initrd.img'))
        mods = orden('lsinitrd', '-m', str(tmp/'initrd.img'), capture_output=True, text=True).stdout
        if 'dmsquash-live' not in mods:raise ValueError('El initramfs no incluye dmsquash-live.')
        for pth in (tmp/'vmlinuz',tmp/'initrd.img'):
            if pth.stat().st_size < 1024:raise ValueError('Artefacto de arranque vacío o incompleto.')
            with pth.open('rb') as stream:os.fsync(stream.fileno())
        tmp.rename(dst)
        actual={'version':ver,'path':'/AUX/boot/'+nombre,
                'kernel_sha256':sha(dst/'vmlinuz'),'initrd_sha256':sha(dst/'initrd.img')}
        # One atomic GRUB file contains both the menu and its machine-readable state.
        atomic(cfg, menu.kernels(uid, actual, previo).encode())
        os.sync()
        print('Kernel publicado:', ver, '· reiniciar manualmente y comprobar uname -r.')
    finally:
        if tmp.exists():shutil.rmtree(tmp)


def main():
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('action',choices=('work','status','sync-kernel','update','api-stage','api-clear','api-keys'))
    par.add_argument('--provider', choices=PROVEEDORES)
    par.add_argument('--kver')
    par.add_argument('--apply',action='store_true')
    cfg=par.parse_args()
    try:
        if cfg.action=='work':workspace();return 0
        if cfg.action=='api-stage':prepara_api(cfg.provider);return 0
        if cfg.action=='api-clear':limpia_api();return 0
        if cfg.action=='api-keys':gestiona_api();return 0
        uid=verifica()
        print('USB persistente verificado:', uid)
        if cfg.action=='status':return 0
        if not cfg.apply:
            print('Plan: '+('dnf upgrade --refresh; ' if cfg.action=='update' else '')+
                  'generar initramfs Live genérico, conservar arranque previo y publicar el kernel. Usar --apply.')
            return 0
        if cfg.action=='update':orden('dnf', 'upgrade', '--refresh')
        publica(cfg.kver or version_instalada())
        return 0
    except (ValueError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print('Operación detenida:',exc)
        return 1


if __name__=='__main__':raise SystemExit(main())
