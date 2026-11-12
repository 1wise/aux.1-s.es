# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Share the verified, embedded iPXE bootstrap across generated boot media."""
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import uuid

DIR_APP = Path(__file__).resolve().parents[1]
MENU_URL = 'http://pxe.1-s.es/menu.ipxe'
TITULO = 'W.A.N Arsenal iPXE - Excalibur'
INICIO = '# AUX WAN BEGIN'
FIN = '# AUX WAN END'
RUTAS_GRUB = ('/boot/grub2/grub.cfg', '/boot/grub/grub.cfg', '/EFI/BOOT/grub.cfg')


def suma(pth):
    with Path(pth).open('rb') as arc:
        return hashlib.file_digest(arc, 'sha256').hexdigest()


def informacion(pth_img=None, sha_img=None):
    pth_img = Path(pth_img) if pth_img else DIR_APP / 'usb/aux-ipxe-usb.img'
    if pth_img.is_symlink() or not pth_img.is_file():
        raise ValueError('Falta la imagen iPXE regular: ' + str(pth_img))
    pth_info = pth_img.parent / 'build-info.json'
    dat = json.loads(pth_info.read_text())
    if (not re.fullmatch(r'[a-f0-9]{64}', dat.get('sha256', '')) or
            suma(pth_img) != dat['sha256'] or
            pth_img.stat().st_size != dat.get('size') or
            sha_img is not None and dat['sha256'] != sha_img.lower()):
        raise ValueError('La imagen iPXE no coincide con su SHA-256 y build-info.json.')
    for nom in ('bios_sha256', 'uefi_sha256', 'bootstrap_sha256'):
        if not re.fullmatch(r'[a-f0-9]{64}', dat.get(nom, '')):
            raise ValueError('Falta una suma del arranque iPXE: ' + nom)
    # The script is embedded in both binaries, so GRUB needs no network drivers.
    url = dat.get('menu_url', '')
    if not re.fullmatch(r'https?://[A-Za-z0-9._:/%+?=~-]+', url):
        raise ValueError('URL de menú iPXE no válida.')
    pth_boot = pth_img.parent / 'bootstrap.ipxe'
    if suma(pth_boot) != dat['bootstrap_sha256'] or ('chain --autofree ' + url) not in pth_boot.read_text():
        raise ValueError('El bootstrap iPXE no coincide con el destino declarado.')
    return pth_img, dat


def extrae(pth_iso, rel, dst, obligatorio=True):
    res = subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(pth_iso),
                          '-extract', rel, str(dst)], capture_output=True)
    if res.returncode == 0 and dst.is_file():
        dst.chmod(0o644)
        return True
    if obligatorio:
        raise ValueError('No se puede extraer ' + rel + ': ' + res.stderr.decode(errors='replace')[-1000:])
    return False


def prepara_payload(dst, pth_img=None, sha_img=None):
    pth_img, dat = informacion(pth_img, sha_img)
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=False)
    for nom, clave in (('ipxe.lkrn', 'bios_sha256'), ('ipxe.efi', 'uefi_sha256')):
        pth = dst / nom
        extrae(pth_img, '/ipxe/' + nom, pth)
        if suma(pth) != dat[clave]:
            raise ValueError('El ejecutable iPXE no coincide con su SHA-256: ' + nom)
        pth.chmod(0o644)
    cap = {'schema': 'aux-wan-boot-v1', 'title': TITULO, 'menu_url': dat['menu_url'],
           'ipxe_image_sha256': dat['sha256'], 'bios_sha256': dat['bios_sha256'],
           'uefi_sha256': dat['uefi_sha256'], 'firmware': ['BIOS', 'UEFI x86_64'],
           'uefi_signed': False, 'boot_verified': False}
    (dst / 'wan.json').write_text(json.dumps(cap, indent=2) + '\n')
    return cap


def entrada(ruta='/aux/wan', nom='aux-wan-arsenal'):
    if not re.fullmatch(r'/[A-Za-z0-9_/-]+', ruta) or not re.fullmatch(r'[a-z0-9-]+', nom):
        raise ValueError('Ruta o identificador GRUB no válido.')
    return f'''{INICIO}
menuentry '{TITULO}' --id {nom} {{
    if [ "$grub_platform" = "efi" ]; then
        if [ "$grub_cpu" = "x86_64" ]; then
            insmod chain
            chainloader {ruta}/ipxe.efi
        else
            echo 'This iPXE payload requires x86_64 UEFI.'
            sleep 5
        fi
    elif [ "$grub_platform" = "pc" ]; then
        insmod linux16
        linux16 {ruta}/ipxe.lkrn
    else
        echo 'This iPXE payload requires x86 BIOS or x86_64 UEFI.'
        sleep 5
    fi
}}
{FIN}
'''


def agrega_grub(txt):
    # Re-finishing a medium replaces our own block without changing its defaults.
    if INICIO in txt:
        patron = re.escape(INICIO) + r'[\s\S]*?' + re.escape(FIN) + r'\n?'
        if len(re.findall(patron, txt)) != 1:
            raise ValueError('Bloque W.A.N incompleto o duplicado en GRUB.')
        return re.sub(patron, lambda _: entrada(), txt)
    if '--id aux-wan-arsenal' in txt:
        raise ValueError('La entrada W.A.N existente no tiene delimitadores AUX.')
    return txt.rstrip() + '\n\n' + entrada()


def agrega_isolinux(txt):
    nuevo = f'''{INICIO}
label aux-wan-arsenal
    menu label {TITULO}
    kernel /aux/wan/ipxe.lkrn
{FIN}
'''
    if INICIO in txt:
        patron = re.escape(INICIO) + r'[\s\S]*?' + re.escape(FIN) + r'\n?'
        if len(re.findall(patron, txt)) != 1:
            raise ValueError('Bloque W.A.N incompleto o duplicado en ISOLINUX.')
        return re.sub(patron, lambda _: nuevo, txt)
    return txt.rstrip() + '\n\n' + nuevo


def prepara_iso(pth_iso, pth_tmp, transforma=None):
    pth_tmp = Path(pth_tmp)
    pth_tmp.mkdir(parents=True, exist_ok=True)
    cap = prepara_payload(pth_tmp / 'payload')
    marca = 'media-' + uuid.uuid4().hex
    (pth_tmp / 'payload' / marca).write_text('AUX WAN boot medium\n')
    mapas = ['-map', str(pth_tmp / 'payload'), '/aux/wan']
    archivos = {'/aux/wan/' + p.name: suma(p) for p in (pth_tmp / 'payload').iterdir()}
    configs = []
    for idx, rel in enumerate(RUTAS_GRUB):
        pth = pth_tmp / ('grub-' + str(idx) + '.cfg')
        if not extrae(pth_iso, rel, pth, False):
            continue
        txt = pth.read_text()
        # EFI stubs delegate to another config; adding a menu after configfile is ineffective.
        if not re.search(r'(?m)^\s*(?:menuentry|submenu)\s', txt):
            continue
        if transforma:
            txt = transforma(txt)
        pth.write_text(agrega_grub(txt))
        mapas += ['-map', str(pth), rel]
        archivos[rel] = suma(pth)
        configs.append(rel)
    if not configs:
        raise ValueError('No hay un menú GRUB compatible; no se publica una entrada W.A.N inaccesible.')
    # Debian installer BIOS media use ISOLINUX; their UEFI menu remains GRUB.
    for idx, rel in enumerate(('/isolinux/menu.cfg', '/isolinux/isolinux.cfg')):
        pth = pth_tmp / ('isolinux-' + str(idx) + '.cfg')
        if extrae(pth_iso, rel, pth, False):
            pth.write_text(agrega_isolinux(pth.read_text()))
            mapas += ['-map', str(pth), rel]
            archivos[rel] = suma(pth)
            configs.append(rel)
            break
    cap['configs'] = configs
    cfg_menu = '/EFI/BOOT/grub.cfg' if '/EFI/BOOT/grub.cfg' in configs else configs[0]
    cola = prepara_efi(pth_iso, pth_tmp / 'efi', mapas, archivos, cfg_menu, marca)
    return mapas, cola, archivos, cap


def prepara_efi(pth_iso, pth_tmp, mapas, archivos, cfg_menu, marca):
    res = subprocess.run(['xorriso', '-indev', str(pth_iso), '-report_el_torito', 'plain'],
                         capture_output=True, text=True, check=True)
    reporte = res.stdout + res.stderr
    indices = re.findall(r'El Torito boot img\s*:\s*(\d+)\s+UEFI\s', reporte)
    if not indices:
        return []
    if len(indices) != 1:
        raise ValueError('Revisar el medio: contiene varias imágenes de arranque EFI.')
    for nom in ('mcopy', 'mdir'):
        if not shutil.which(nom):
            raise ValueError('Falta ' + nom + ' (mtools) para revisar el GRUB de la partición EFI.')
    subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(pth_iso),
                    '-extract_boot_images', str(pth_tmp)], check=True, capture_output=True)
    imagenes = list(pth_tmp.glob('eltorito_img' + indices[0] + '_uefi.img'))
    if len(imagenes) != 1:
        raise ValueError('No se puede identificar la imagen de arranque EFI.')
    img = imagenes[0]
    img.chmod(0o644)
    cfg = pth_tmp / 'grub.cfg'
    listado = subprocess.run(['mdir', '-i', str(img), '::/EFI/BOOT'], capture_output=True)
    if listado.returncode:
        raise ValueError('La partición EFI no contiene un directorio EFI/BOOT legible.')
    # Standalone GRUB embeds its config; Fedora also carries a config in the FAT image.
    res = subprocess.run(['mcopy', '-i', str(img), '::/EFI/BOOT/grub.cfg', str(cfg)], capture_output=True)
    if res.returncode:
        if re.search(rb'grub\s+cfg\b', listado.stdout, re.IGNORECASE):
            raise ValueError('No se puede leer el GRUB de la partición EFI.')
        return []
    # Point the FAT copy at this exact medium, rather than a similarly labeled USB.
    cfg.chmod(0o644)
    cfg.write_text(f'''# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
search --no-floppy --file --set=aux_wan_media /aux/wan/{marca}
if [ -n "$aux_wan_media" ]; then
    set root=$aux_wan_media
    configfile {cfg_menu}
else
    echo 'AUX boot medium was not found.'
    sleep 5
fi
''')
    subprocess.run(['mcopy', '-o', '-i', str(img), str(cfg), '::/EFI/BOOT/grub.cfg'],
                   capture_output=True, check=True)
    archivos['@efi'] = suma(img)
    ruta = re.search(r'El Torito img path\s*:\s*' + indices[0] + r'\s+(/[^\n]+)', reporte)
    if ruta:
        mapas += ['-map', str(img), ruta[1].strip()]
        return []
    # Appended EFI partitions are outside the ISO tree; override them after replay.
    res = subprocess.run(['xorriso', '-indev', str(pth_iso), '-report_el_torito', 'as_mkisofs'],
                         capture_output=True, text=True, check=True)
    args = shlex.split(res.stdout)
    for idx, tok in enumerate(args):
        if tok == '-append_partition' and idx + 3 < len(args):
            num, tipo = args[idx + 1:idx + 3]
            if (re.fullmatch(r'[1-9]', num) and re.fullmatch(r'(?:0x[0-9a-fA-F]+|[0-9a-fA-F]{32})', tipo)
                    and any(re.search(r'appended_partition_' + num + r'(?:_start_\d+s_size_\d+d)?:all::', a) for a in args)):
                return ['-append_partition', num, tipo, str(img)]
    raise ValueError('No se reconoce el enlace de la partición EFI; se conserva la ISO original.')


def verifica_iso(pth_iso, archivos, pth_tmp):
    """Read the finished medium back before publishing it under its final name."""
    pth_tmp = Path(pth_tmp)
    pth_tmp.mkdir(parents=True, exist_ok=False)
    for idx, (rel, sha) in enumerate(archivos.items()):
        pth = pth_tmp / str(idx)
        if rel == '@efi':
            subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(pth_iso),
                            '-extract_boot_images', str(pth)], check=True, capture_output=True)
            imgs = list(pth.glob('eltorito_img*_uefi.img'))
            if len(imgs) != 1:
                raise ValueError('La ISO final no contiene una partición EFI verificable.')
            pth = imgs[0]
        else:
            extrae(pth_iso, rel, pth)
        if suma(pth) != sha:
            raise ValueError('La ISO final no contiene el arranque W.A.N esperado: ' + rel)
