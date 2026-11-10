#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Write a verified GPT ISO and allocate the remainder to AUX-DATA. Dry-run default."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import zlib

MIB = 1024**2


def estructura(pth):
    # Never repair or convert an unknown hybrid table on the user's USB.
    with Path(pth).open('rb') as arc:
        mbr = arc.read(512)
        if len(mbr) != 512 or mbr[510:512] != b'\x55\xaa':
            raise ValueError('La ISO no contiene una tabla de arranque reconocida.')
        tipos = [mbr[446 + i*16 + 4] for i in range(4)]
        if any(t not in (0, 0xee) for t in tipos) or tipos.count(0xee) != 1:
            raise ValueError('ISO MBR/híbrida no admitida en dev.1. No se tocará el USB; no convertir con fdisk.')
        cab = arc.read(512)
        if cab[:8] != b'EFI PART':
            raise ValueError('Esta herramienta exige GPT nativa con MBR protector.')
        tam = struct.unpack_from('<I', cab, 12)[0]
        if not 92 <= tam <= 512:
            raise ValueError('Cabecera GPT inválida.')
        crc = struct.unpack_from('<I', cab, 16)[0]
        normal = bytearray(cab[:tam]);normal[16:20] = b'\0'*4
        if zlib.crc32(normal) & 0xffffffff != crc:
            raise ValueError('CRC de cabecera GPT inválido.')
        inicio, num, ent_tam, ent_crc = struct.unpack_from('<QIII', cab, 72)
        if not 1 <= num <= 128 or ent_tam != 128 or inicio > 64:
            raise ValueError('Tabla GPT no admitida.')
        arc.seek(inicio*512)
        tabla = arc.read(num*ent_tam)
        if len(tabla) != num*ent_tam or zlib.crc32(tabla) & 0xffffffff != ent_crc:
            raise ValueError('CRC de entradas GPT inválido.')
        usados = [i+1 for i in range(num) if tabla[i*128:i*128+16] != b'\0'*16]
        libres = [i+1 for i in range(num) if i+1 not in usados]
        if not usados or not libres:
            raise ValueError('No hay una entrada GPT libre.')
        for i in usados:
            ini, fin = struct.unpack_from('<QQ', tabla, (i-1)*128+32)
            if ini > fin or (fin+1)*512 > Path(pth).stat().st_size:
                raise ValueError('Partición fuera de la ISO; abortar.')
    return libres[0]


def info_dispositivo(pth):
    pth = Path(pth).resolve(strict=True)
    if not str(pth).startswith('/dev/') or not stat.S_ISBLK(pth.stat().st_mode):
        raise ValueError('Elegir un dispositivo de bloques completo, nunca un archivo.')
    rsp = subprocess.run(['lsblk', '--bytes', '--json', '--output',
        'PATH,TYPE,SIZE,MODEL,SERIAL,TRAN,RM,RO,MOUNTPOINTS,LOG-SEC', str(pth)],
        capture_output=True, text=True, check=True)
    dat = json.loads(rsp.stdout)['blockdevices'][0]
    if dat['type'] != 'disk' or dat['ro'] or (dat['tran'] != 'usb' and not dat['rm']):
        raise ValueError('Solo disco USB/removible, completo y escribible; sin override de discos internos.')
    if int(dat['log-sec']) != 512:
        raise ValueError('Solo dispositivos de sector lógico de 512 bytes en dev.1.')
    def valida(ent):
        if any(ent.get('mountpoints') or []):
            raise ValueError('Disco o partición montada/en swap: desmontar manualmente y revisar.')
        if any((Path('/sys/class/block') / Path(ent['path']).name / 'holders').iterdir()):
            raise ValueError('Dispositivo usado por LVM/RAID/mapper; no se toca.')
        for hijo in ent.get('children', []):
            valida(hijo)
    valida(dat)
    return pth, dat, pth.stat().st_rdev


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--iso', type=Path, required=True)
    par.add_argument('--sha256', required=True, help='Expected digest obtained from a trusted release')
    par.add_argument('--device', type=Path, required=True)
    par.add_argument('--apply', action='store_true')
    cfg = par.parse_args()
    try:
        pth_iso = cfg.iso.resolve(strict=True)
        if not pth_iso.is_file() or not re.fullmatch(r'[a-fA-F0-9]{64}', cfg.sha256):
            raise ValueError('ISO o SHA-256 inválido.')
        with pth_iso.open('rb') as arc:
            if hashlib.file_digest(arc, 'sha256').hexdigest() != cfg.sha256.lower():
                raise ValueError('SHA-256 no coincide; no se toca el dispositivo.')
        num = estructura(pth_iso)
        pth_dev, dat, rdev = info_dispositivo(cfg.device)
        inicio = ((pth_iso.stat().st_size + MIB-1)//MIB + 1)*2048
        if int(dat['size']) < inicio*512 + 256*MIB:
            raise ValueError('No quedan al menos 256 MiB para AUX-DATA.')
        print(json.dumps({'device': str(pth_dev), 'model': dat['model'], 'serial': dat['serial'],
            'capacity_bytes': dat['size'], 'iso': str(pth_iso), 'partition': num,
            'data_start_sector': inicio, 'data_label': 'AUX-DATA', 'apply': cfg.apply}, indent=2))
        print('BORRA TODO EL USB. Conserva el arranque de la ISO; NO hace persistente el kernel live.')
        if not cfg.apply:
            return 0
        if os.geteuid() != 0 or not sys.stdin.isatty():
            raise ValueError('--apply exige root y confirmación en terminal interactiva.')
        for cmd in ('sgdisk', 'partprobe', 'udevadm', 'mkfs.ext4'):
            if shutil.which(cmd) is None:
                raise ValueError('Falta dependencia: ' + cmd)
        frase = 'BORRAR ' + str(pth_dev) + ' ' + str(dat['size'])
        if input('Escribir exactamente ' + frase + ': ') != frase:
            raise ValueError('Sin confirmación; no se escribió nada.')
        _, nuevo, _ = info_dispositivo(pth_dev)
        if nuevo != dat or pth_dev.stat().st_rdev != rdev:
            raise ValueError('Cambió el dispositivo después de revisar el plan.')
        # Verify the target descriptor before the first destructive byte.
        fd = os.open(pth_dev, os.O_WRONLY | os.O_EXCL | os.O_NOFOLLOW)
        with os.fdopen(fd, 'wb', buffering=0) as dst, pth_iso.open('rb') as src:
            if os.fstat(dst.fileno()).st_rdev != rdev:
                raise ValueError('Dispositivo sustituido; operación cancelada.')
            shutil.copyfileobj(src, dst, 4*MIB)
            os.fsync(dst.fileno())
        dig = hashlib.sha256()
        restante = pth_iso.stat().st_size
        with pth_dev.open('rb', buffering=0) as arc:
            while restante:
                buf = arc.read(min(restante, 4*MIB))
                if not buf:
                    raise ValueError('Lectura incompleta al verificar el USB.')
                dig.update(buf)
                restante -= len(buf)
        if dig.hexdigest() != cfg.sha256.lower():
            raise ValueError('La grabación no coincide con la ISO; no se particiona ni formatea.')
        subprocess.run(['sgdisk', '-e', str(pth_dev)], check=True)
        subprocess.run(['sgdisk', '-n', f'{num}:{inicio}:0', '-t', f'{num}:8300',
                        '-c', f'{num}:AUX-DATA', str(pth_dev)], check=True)
        subprocess.run(['partprobe', str(pth_dev)], check=True)
        subprocess.run(['udevadm', 'settle', '--timeout=15'], check=True)
        pth_par = Path(str(pth_dev) + ('p' if pth_dev.name[-1].isdigit() else '') + str(num))
        if not pth_par.is_block_device():
            raise ValueError('La partición nueva no aparece; detenerse y revisar lsblk, sin formatear otra ruta.')
        rsp = subprocess.run(['lsblk', '--json', '--output', 'PKNAME,TYPE,START,MOUNTPOINTS', str(pth_par)],
                             capture_output=True, text=True, check=True)
        ent = json.loads(rsp.stdout)['blockdevices'][0]
        if ent['pkname'] != pth_dev.name or ent['type'] != 'part' or int(ent['start']) != inicio or any(ent['mountpoints'] or []):
            raise ValueError('La partición no coincide con el plan o está montada; no se formatea.')
        if any((Path('/sys/class/block') / pth_par.name / 'holders').iterdir()):
            raise ValueError('La partición se ha activado en un mapper; no se formatea.')
        subprocess.run(['mkfs.ext4', '-m', '0', '-L', 'AUX-DATA', str(pth_par)], check=True)
        print('USB creado. El espacio restante está en AUX-DATA. Montaje explícito desde la ISO; no se cambia /work.')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as exc:
        print(str(exc) + '\nOperación detenida. Si comenzó la grabación, el USB puede estar incompleto.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
