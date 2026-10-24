#!/usr/bin/env bash
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# The task body lives here so the command can be reviewed and run on its own.
set -Eeuo pipefail
pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "${pth_app}" "$@" <<'AUXPY'
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Generate only: crawl deployed units and render indexes, supported boot recipes and sitemaps."""
import sys
from pathlib import Path

pth_app = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else Path(__file__).resolve().parent
sys.path.insert(0, str(pth_app / 'src'))
from common import *

USB_FILES = {}
ISO_SOURCE_FILES = ['README.md', 'assist.ks.in', 'dracut.conf', 'packages.txt', 'prepare.py', 'test_sources.py',
                    'payload/assist.py', 'payload/aux-assist.service', 'payload/aux-observer@.service',
                    'payload/boot_check.py', 'payload/remote-shell.sh', 'payload/tech-work.service', 'payload/work.py']


def es_unidad(pth):
    return any((pth / nom).is_dir() for nom in (
        'live', 'casper', 'images/pxeboot', 'arch/boot', 'debian-installer',
        'install.amd', 'install.a64', 'boot/x86_64/loader', 'boot/aarch64/loader'))


def descubre(rec_all, cfg):
    """Walk public unit directories and RAM links, pruning image internals and cycles."""
    fuentes = lee_fuentes(cfg)
    fuentes.update({rec['filename']: rec['url'] for rec in rec_all})
    archivos, unidades, vistos, preparados = [], [], set(), set()
    for raiz, dirs, noms in os.walk(cfg.output, followlinks=True):
        pth = Path(raiz)
        try:
            stat = pth.stat()
        except OSError:
            dirs[:] = []
            continue
        key = (stat.st_dev, stat.st_ino)
        if key in vistos:
            dirs[:] = []
            continue
        vistos.add(key)
        dirs[:] = sorted(nom for nom in dirs if not nom.startswith('.') and nom not in ('assets', 'downloads', 'files', 'contents'))
        if pth != cfg.output and (pth in preparados or es_unidad(pth)):
            unidades.append(pth)
            dirs[:] = []
            continue
        locales = [pth / nom for nom in sorted(noms) if es_payload(nom) and (pth / nom).is_file()]
        archivos += locales
        # Even unsupported boot media own their contents tree; internal BIN/EFI/ISO
        # files belong in Browse contents, never in the top-level download catalog.
        for arc in locales:
            if arc.name.lower().endswith(('.iso', '.zip', '.tar.gz')):
                rec = obt_meta(fuentes.get(arc.name, cfg.pxe_url + '/' + quote(arc.name, safe='')))
                preparados.add(pth / rec['tree'])
    descubiertos = []
    for arc in archivos:
        rel = arc.relative_to(cfg.output).as_posix()
        rec = obt_meta(fuentes.get(arc.name, cfg.pxe_url + '/' + quote(rel, safe='/')))
        rec['path'] = rel
        rec['tree'] = (arc.parent.relative_to(cfg.output) / rec['tree']).as_posix()
        rec['id'] = 'r_' + hashlib.sha256(rel.encode()).hexdigest()[:12]
        descubiertos.append(rec)
    trees = {rec['tree'] for rec in descubiertos}
    for pth in unidades:
        rel = pth.relative_to(cfg.output).as_posix()
        if rel in trees:
            continue
        nom = re.sub(r'[^A-Za-z0-9._+-]', '_', pth.name)
        rec = obt_meta(cfg.pxe_url + '/' + quote(nom, safe=''))
        if rec['family'] == 'other':
            fam = 'fedora' if ((pth / 'images/pxeboot').is_dir() or
                ((pth / 'LiveOS').is_dir() and any((pth / nom).is_dir() for nom in
                 ['boot/x86_64/loader', 'boot/aarch64/loader']))) else ('debian' if (pth / 'debian-installer').is_dir() else None)
            if fam:
                rec = obt_meta(cfg.pxe_url + '/' + fam + '-' + quote(nom, safe=''))
        rec.update(id='r_' + hashlib.sha256(rel.encode()).hexdigest()[:12], filename=pth.name,
                   path=rel, tree=rel, format='TREE', name=rec['name'] + ' (tree)')
        if (pth / 'boot/aarch64/loader').is_dir():
            rec['arch'] = 'arm64'
        if (pth / '.treeinfo').is_file():
            inf = configparser.ConfigParser()
            try:
                inf.read(pth / '.treeinfo')
                arq = inf.get('general', 'arch', fallback='')
                rec['arch'] = 'arm64' if arq == 'aarch64' else arq or rec['arch']
            except configparser.Error:
                pass
        descubiertos.append(rec)
    return [rec for rec in descubiertos if not cfg.only or
            cfg.only.lower() in (rec['family'] + ' ' + rec['path']).lower()]


def rastrea(rec_all, cfg, sumas):
    """Validate actual deployed bytes; cached records alone never create public links."""
    for rec in rec_all:
        try:
            arc = cfg.output / rec.get('path', rec['filename'])
            rec.update(published=False, contents_ready=False)
            if rec['format'] == 'TREE':
                rec.update(published=arc.is_dir(), contents_ready=arc.is_dir(), status='ready')
                msg_descarga(cfg, rec, 'CRAWL', 'Public boot tree: ' + rec['tree'])
                continue
            if not arc_valido(arc, rec['filename']):
                rec.update(status='invalid-payload', error='Deployed file is not a valid payload')
                msg_descarga(cfg, rec, 'ERROR', rec['error'], forzar=True)
                continue
            rec.update(size=arc.stat().st_size, sha256=obt_sha(arc))
            esperado = sumas.get(rec.get('path', rec['filename']), sumas.get(rec['filename']))
            if esperado and rec['sha256'] != esperado:
                rec.update(status='checksum-failed', error=f'Deployed payload differs from trusted checksum: expected {esperado}, obtained {rec["sha256"]}')
                continue
            rec.update(published=True, status='ready')
            tree = cfg.output / rec['tree']
            est = lee_estado(cfg, 'tree-state', rec)
            if est and est.get('sha256') != rec['sha256']:
                rec['tree_error'] = 'Prepared tree belongs to an older image; rerun deploy'
            elif tree.is_dir() and any(tree.iterdir()):
                rec['contents_ready'] = True
            msg_descarga(cfg, rec, 'CRAWL', f'{rec["size"]:,} bytes | {rec.get("path", rec["filename"])}' +
                         (' | contents available' if rec['contents_ready'] else ''))
        except (ValueError, OSError) as exc:
            rec.update(status='failed', error=describe_error(exc), error_stage='crawl', published=False, contents_ready=False)
    return rec_all


def obt_live_url(cfg):
    if cfg.live_url:
        return cfg.live_url
    part = urlsplit(cfg.pxe_url)
    if part.scheme != 'http':
        return None
    try:
        ip = socket.gethostbyname(part.hostname)
    except OSError:
        return None
    host = ip + (':' + str(part.port) if part.port else '')
    return urlunsplit(('http', host, part.path, '', ''))



def obt_par(pth_tree, pares):
    if not pth_tree.is_dir():
        return None
    for pat_ker, pat_ini in pares:
        ker_all = sorted(pth_tree.glob(pat_ker))
        ini_all = sorted(pth_tree.glob(pat_ini))
        for ker in ker_all:
            for ini in ini_all:
                if ker.is_file() and ini.is_file() and ker.parent == ini.parent and ker.stat().st_size and ini.stat().st_size and ker.resolve().is_relative_to(pth_tree.resolve()) and ini.resolve().is_relative_to(pth_tree.resolve()):
                    return ker, ini
    return None


def arc_unidad(pth_tree, nom):
    """Resolve original media paths without permitting escapes from the public unit."""
    pth = pth_tree / nom
    return pth if nom and not Path(nom).is_absolute() and pth.resolve().is_relative_to(pth_tree.resolve()) and arc_presente(pth) else None


def obt_cfg_boot(pth_tree):
    # Read bootloader configuration as data; never execute GRUB or Syslinux commands.
    for nom in ['boot/grub2/grub.cfg', 'EFI/BOOT/grub.cfg', 'boot/grub/grub.cfg', 'isolinux/isolinux.cfg']:
        arc = arc_unidad(pth_tree, nom)
        if not arc or arc.stat().st_size > 1024 * 1024:
            continue
        ker, args = None, []
        for lin in arc.read_text(errors='replace').splitlines():
            try:
                tok = shlex.split(lin, comments=True)
            except ValueError:
                continue
            if len(tok) < 2:
                continue
            # GRUB's ($root) selects this same mounted media, not another public directory.
            rel = re.sub(r'^\((?:\$root|\$\{root\}|cd0)\)', '', tok[1]).lstrip('/')
            if tok[0] in ('linux', 'linuxefi', 'linux16', 'kernel'):
                ker = arc_unidad(pth_tree, rel)
                args = tok[2:]
            elif tok[0] in ('initrd', 'initrdefi', 'initrd16') and ker:
                ini = arc_unidad(pth_tree, rel)
                if ini:
                    return {'par': (ker, ini), 'args': args, 'path': nom}
    return {}


def gen_carga(ker, ini, args, group, cfg):
    # A named initrd supports EFI kernels that use their boot filesystem.
    url_ker = cfg.pxe_url + '/' + quote(ker.relative_to(cfg.output).as_posix(), safe='/')
    url_ini = cfg.pxe_url + '/' + quote(ini.relative_to(cfg.output).as_posix(), safe='/')
    return {'commands': [f'kernel {url_ker} initrd=initrd {args} || goto error',
                         f'initrd --name initrd {url_ini} || goto error', 'boot || goto error'],
            'firmware': None, 'group': group}


def gen_fedora(rec, cfg, pth_tree):
    """Use Fedora's own metadata/configuration, preserving every relative media path."""
    inf = configparser.ConfigParser(interpolation=None)
    meta = arc_unidad(pth_tree, '.treeinfo')
    if meta:
        try:
            inf.read(meta)
        except configparser.Error:
            rec['boot_error'] = 'Fedora .treeinfo could not be parsed'
            return None
    conf = obt_cfg_boot(pth_tree)
    arq = 'aarch64' if rec['arch'] == 'arm64' else rec['arch']
    nom_ker = inf.get('images-' + arq, 'kernel', fallback='')
    nom_ini = inf.get('images-' + arq, 'initrd', fallback='')
    ker = arc_unidad(pth_tree, nom_ker)
    ini = arc_unidad(pth_tree, nom_ini)
    if (nom_ker or nom_ini) and not (ker and ini):
        rec['boot_error'] = 'Fedora kernel/initrd declared in .treeinfo is missing or outside the unit'
        return None
    par = (ker, ini) if ker and ini else conf.get('par') or obt_par(pth_tree, [
        ('images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img'),
        ('boot/' + arq + '/loader/linux', 'boot/' + arq + '/loader/initrd'),
        ('isolinux/vmlinuz', 'isolinux/initrd.img')])
    if not par:
        rec['boot_error'] = 'Fedora kernel/initrd missing at the original media paths'
        return None
    args_src = conf.get('args', [])
    asistencia = 'aux.assist' in args_src
    asistencia_live = asistencia and 'rd.live.image' in args_src
    if asistencia:
        # The source media must explicitly opt in; a filename is not a boot recipe.
        rec.update(category='assistance', kind='tool',
                   name='AUX Rescue / Remote assistance' if rec['filename'].lower().startswith('aux-rescue') else 'Fedora / Remote assistance',
                   assistance=True, assistance_boot=True)
    elif rec.get('assistance'):
        rec['boot_error'] = 'Assistance source media does not declare aux.assist'
        return None
    rec['source_boot_config'] = conf.get('path')
    rec['boot_files'] = {'kernel': par[0].relative_to(pth_tree).as_posix(),
                         'initrd': par[1].relative_to(pth_tree).as_posix()}
    inst = ('netinst' in rec['filename'].lower() or any(arg.startswith('inst.stage2=') for arg in args_src))
    if asistencia_live and inst:
        rec['boot_error'] = 'Assistance media mixes Live and Anaconda boot instructions'
        return None
    img_stage = inf.get('stage2', 'mainimage', fallback='')
    # Anaconda itself falls back to images/install.img when a boot ISO lacks .treeinfo.
    if not img_stage and arc_unidad(pth_tree, 'images/install.img'):
        img_stage = 'images/install.img'
    if not img_stage and inst and arc_unidad(pth_tree, 'LiveOS/squashfs.img'):
        img_stage = 'LiveOS/squashfs.img'
    if img_stage and not asistencia_live:
        if not arc_unidad(pth_tree, img_stage):
            rec['boot_error'] = 'Fedora stage2 missing or outside the unit: ' + img_stage
            return None
        rec['boot_files']['stage2'] = img_stage
        args = 'ip=dhcp rd.neednet=1 inst.stage2=' + cfg.pxe_url + '/' + quote(rec['tree'], safe='/') + '/'
        if asistencia:
            # Fetch this unit's modified runtime, retaining the assistance systemd selector.
            # Never copy the source hd:LABEL stage2 address into a network boot command.
            args += ' aux.assist inst.rescue'
            return gen_carga(*par, args, 'tools', cfg)
        # Keep the origin mirror, release, edition and architecture for package installation.
        repo = next((arg for arg in args_src if re.match(r'^inst.repo=https?://[^\s$;|&<>\\"\']+$', arg)), None)
        part = urlsplit(rec['url'])
        repo_pth = re.sub(r'/iso/[^/]+$', '/os/', part.path)
        if repo:
            args += ' ' + repo
        elif part.scheme in ('http', 'https') and repo_pth != part.path:
            args += ' inst.repo=' + urlunsplit((part.scheme, part.netloc, repo_pth, '', ''))
        return gen_carga(*par, args, 'netboot', cfg)
    if inst or (asistencia and 'rd.live.image' not in args_src):
        rec['boot_error'] = 'Fedora installer runtime missing: images/install.img or the original .treeinfo path'
        return None
    # Dracut defaults are used only when the original boot configuration does not override them.
    args_live = [arg for arg in args_src if arg.startswith(('rd.live.dir=', 'rd.live.squashimg='))]
    if any(re.search(r'[\s$;|&<>\\"\']', arg) for arg in args_live):
        rec['boot_error'] = 'Fedora Live path settings contain unsupported command characters'
        return None
    dir_live = next((arg.split('=', 1)[1] for arg in args_live if arg.startswith('rd.live.dir=')), 'LiveOS').lstrip('/')
    nom_live = next((arg.split('=', 1)[1] for arg in args_live if arg.startswith('rd.live.squashimg=')), 'squashfs.img')
    img_live = (Path(dir_live) / nom_live).as_posix()
    if not arc_unidad(pth_tree, img_live):
        rec['boot_error'] = 'Fedora Live filesystem missing or outside the unit: ' + img_live
        return None
    rec['boot_files']['live'] = img_live
    args = 'ip=dhcp rd.neednet=1 rd.live.image ro root=live:' + cfg.pxe_url + '/' + quote(rec['tree'] + '/' + img_live, safe='/')
    if args_live:
        args += ' ' + ' '.join(args_live)
    if asistencia:
        # Live rescue needs a RAM overlay, not Anaconda's installer stage2 flags.
        args += ' aux.assist rd.live.overlay.overlayfs=1 rd.luks=0 rd.lvm=0 rd.md=0'
        rec['ai_assist'] = 'aux.ai.available=1' in args_src
        if rec['ai_assist']:
            args += ' aux.ai.available=1'
    return gen_carga(*par, args, 'tools' if asistencia else 'live', cfg)



def gen_boot(rec, cfg, url_live=None):
    if (not rec['published'] or rec.get('tree_error') or
            rec['status'] in ('checksum-failed', 'prepare-failed')):
        return None
    pth_tree = cfg.output / rec['tree']
    rel_arc = rec.get('path', rec['filename'])
    url_arc = cfg.pxe_url + '/' + quote(rel_arc, safe='/')
    fam = rec['family']
    if rec['format'] != 'TREE' and not (cfg.output / rel_arc).is_file():
        return None
    if rec['filename'].endswith(('.efi', '.kpxe', '.pxe', '.lkrn')):
        return {'commands': [f'chain --autofree {url_arc} || goto error'],
                'firmware': 'efi' if rec['filename'].endswith('.efi') else 'pcbios',
                'group': 'tools' if 'memtest' in rec['filename'].lower() else 'netboot'}
    if rec['filename'].endswith('.bin') and 'memtest' in rec['filename'].lower():
        return {'commands': [f'kernel {url_arc} || goto error', 'boot || goto error'],
                'firmware': 'pcbios', 'group': 'tools'}
    if rec['format'] == 'QCOW2':
        return None
    if fam == 'alpine':
        # Reject boot dependencies outside this media tree or from another release.
        kernels = [arc_unidad(pth_tree, arc.relative_to(pth_tree).as_posix())
                   for arc in pth_tree.rglob('vmlinuz-lts')] if pth_tree.is_dir() else []
        kernels = [arc for arc in kernels if arc]
        if len(kernels) != 1:
            rec['boot_error'] = 'Alpine requires exactly one local vmlinuz-lts'
            return None
        ker = kernels[0]
        rel_dir = ker.parent.relative_to(pth_tree)
        ini = arc_unidad(pth_tree, (rel_dir / 'initramfs-lts').as_posix())
        mod = arc_unidad(pth_tree, (rel_dir / 'modloop-lts').as_posix())
        rel = re.fullmatch(r'(\d+\.\d+)\.\d+', rec['release'])
        if not (ini and mod and rel):
            rec['boot_error'] = 'Alpine requires same-unit initramfs/modloop and a known release'
            return None
        repo = 'https://dl-cdn.alpinelinux.org/alpine/v' + rel.group(1) + '/main'
        args = 'ip=dhcp modules=loop,squashfs,sd-mod,usb-storage alpine_repo=' + repo + ' modloop=' + cfg.pxe_url + '/' + quote(mod.relative_to(cfg.output).as_posix(), safe='/')
        rec['boot_files'] = {'kernel': ker.relative_to(pth_tree).as_posix(), 'initrd': ini.relative_to(pth_tree).as_posix(), 'modloop': mod.relative_to(pth_tree).as_posix()}
        return gen_carga(ker, ini, args, 'netboot', cfg)
    if fam == 'fedora':
        return gen_fedora(rec, cfg, pth_tree)
    # A CD-ROM installer initrd cannot be advertised as a network installer.
    pares = [
        ('debian-installer/i386/linux', 'debian-installer/i386/initrd.gz'),
        ('debian-installer/amd64/linux', 'debian-installer/amd64/initrd.gz'),
        ('debian-installer/arm64/linux', 'debian-installer/arm64/initrd.gz'),
        ('amd64/linux', 'amd64/initrd'), ('linux', 'initrd.gz'),
        ('images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img'),
        ('casper/vmlinuz*', 'casper/initrd*'), ('live/vmlinuz*', 'live/initrd*'),
        ('arch/boot/x86_64/vmlinuz-linux', 'arch/boot/x86_64/initramfs-linux.img')]
    par = obt_par(pth_tree, pares)
    if not par:
        return None
    ker, ini = par
    args, group = None, 'netboot'
    if fam in ('debian', 'kali') and ker.name == 'linux' and ini.name == 'initrd.gz':
        args = 'ip=dhcp ---'
        rec['arch'] = 'arm64' if 'arm64' in ker.parts else rec['arch']
    elif fam in ('debian', 'clonezilla', 'gparted', 'kali') and arc_presente(pth_tree / 'live/filesystem.squashfs') and url_live:
        # Omit ip=dhcp here: Debian live-boot's interface syntax differs from dracut.
        args = 'boot=live components fetch=' + url_live + '/' + quote(rec['tree'], safe='/') + '/live/filesystem.squashfs'
        group = 'live'
    elif fam in ('ubuntu', 'bootrepair'):
        iso = rec if rec['format'] == 'ISO' else next((item for item in getattr(cfg, 'resources', [])
            if item['family'] == 'ubuntu' and item['format'] == 'ISO' and item['published']
            and item['arch'] == rec['arch'] and item['release'].split()[0] == rec['release'].split()[0]
            and 'live-server' in item['filename']), None)
        if iso and ((ker.parent.name == 'casper' and any(arc_presente(arc) for arc in pth_tree.glob('casper/*.squashfs'))) or ker.name == 'linux'):
            args = 'boot=casper ip=dhcp url=' + obt_local_url(iso, cfg)
            group = 'netboot' if 'live-server' in iso['filename'] else 'live'
    elif fam == 'arch' and any(arc_presente(pth_tree / 'arch/x86_64' / nom) for nom in ['airootfs.sfs', 'airootfs.erofs']):
        args = 'ip=dhcp archisobasedir=arch archiso_http_srv=' + cfg.pxe_url + '/' + quote(rec['tree'], safe='/') + '/'
        group = 'live'
    if args is None:
        return None
    return gen_carga(ker, ini, args, group, cfg)


FAMILIES = {
    'assistance': [('fedora', 'Fedora'), ('debian', 'Debian'), ('other', 'Other assistance')],
    'distribution': [('alpine', 'Alpine Linux'), ('centos', 'CentOS Stream'), ('fedora', 'Fedora'), ('debian', 'Debian'), ('ubuntu', 'Ubuntu'),
                     ('gentoo', 'Gentoo'), ('arch', 'Arch Linux'), ('kali', 'Kali Linux'), ('proxmox', 'Proxmox VE')],
    'tools': [('systemrescue', 'SystemRescue'), ('rescatux', 'Rescatux'), ('redo', 'Redo Rescue'), ('clonezilla', 'Clonezilla'), ('gparted', 'GParted'), ('memtest', 'Memtest86+'),
              ('netboot', 'netboot.xyz'), ('bootrepair', 'Boot Repair'), ('dban', 'DBAN'),
              ('supergrub', 'Super GRUB2 Disk'), ('other', 'Other tools')],
}


def orden_asistencia(rec):
    """Order release components numerically; a final release precedes its dev builds."""
    nom = rec['filename'].lower()
    rel = re.search(r'(\d+)\.(\d+)\.(\d+)(?:-dev\.(\d+))?', nom)
    return tuple(map(int, rel.group(1, 2, 3))) + (rel.group(4) is None, int(rel.group(4) or 0), nom) if rel else (0, 0, 0, False, 0, nom)


def obt_rama(rec):
    """A catalog branch describes the media, independently of PXE readiness."""
    if rec['family'] == 'gentoo':
        return 'chroot'
    low = rec['filename'].lower()
    if rec['format'] == 'QCOW2':
        return 'cloud'
    if any(nom in low for nom in ('netinst', 'netboot')) or low.endswith(('.efi', '.kpxe', '.pxe', '.lkrn')):
        return 'netinstall'
    if any(nom in low for nom in ('live-server', 'installer', 'minimal')):
        return 'install'
    group = (rec.get('_boot') or {}).get('group', rec.get('boot_group'))
    return 'live' if rec.get('kind') == 'live' or group == 'live' else 'install'


def gen_arbol(rec_all):
    """One hierarchy feeds both HTML catalogs, browser filters and iPXE submenus."""
    arbol = []
    for cat, label, num in [('assistance', 'Remote assistance', '0'),
                            ('distribution', 'Distros', '1'), ('tools', 'Tools', '2')]:
        raiz = {'id': 'nav_' + cat, 'label': label, 'number': num, 'category': cat,
                'children': [], 'resources': []}
        if cat == 'assistance':
            raiz['resources'] = [rec['id'] for rec in sorted(rec_all, key=orden_asistencia, reverse=True)
                                  if rec['category'] == cat]
            arbol.append(raiz)
            continue
        for idx, (fam, nom) in enumerate(FAMILIES[cat], 1):
            recursos = [rec for rec in rec_all if rec['category'] == cat and rec['family'] == fam]
            if not recursos:
                continue
            nodo = {'id': raiz['id'] + '_' + fam, 'label': nom, 'number': num + '.' + str(idx),
                    'category': cat, 'children': [], 'resources': []}
            if cat == 'distribution':
                ramas = [('chroot', 'Chroot environment')] if fam == 'gentoo' else [
                    ('netinstall', 'Netinstall'), ('install', 'Install'), ('live', 'Live'), ('cloud', 'Cloud / virtual disk')]
                for pos, (rama, titulo) in enumerate(ramas, 1):
                    ids = [rec['id'] for rec in recursos if obt_rama(rec) == rama]
                    if ids:
                        nodo['children'].append({'id': nodo['id'] + '_' + rama, 'label': titulo,
                            'number': nodo['number'] + '.' + str(pos), 'category': cat,
                            'children': [], 'resources': ids})
            else:
                nodo['resources'] = [rec['id'] for rec in recursos]
            raiz['children'].append(nodo)
        arbol.append(raiz)
    return arbol


def recorre_arbol(arbol, nivel=0):
    for nodo in arbol:
        yield nodo, nivel
        yield from recorre_arbol(nodo['children'], nivel + 1)


def obt_ids(nodo):
    return nodo['resources'] + [rid for hijo in nodo['children'] for rid in obt_ids(hijo)]


def gen_catalog_nav(arbol):
    def enlaces(nodos):
        return '<ul>' + ''.join('<li class="chapter-' + nodo['category'] + '"><a data-tree-node="' + nodo['id'] + '" href="#' + nodo['id'] + '">' +
            html.escape(nodo['number'] + '. ' + nodo['label']) + '</a>' +
            (enlaces(nodo['children']) if nodo['children'] else '') + '</li>' for nodo in nodos) + '</ul>'
    return '<nav class="catalog-tree" aria-label="Distribution and tool hierarchy">' + enlaces(arbol) + '</nav>'


def gen_ipxe(rec_all, cfg):
    def puerta(rec):
        boot = rec['_boot']
        gate = 'iseq ${cpu_arch} ' + rec['arch']
        if rec['arch'] == 'i386':
            gate = 'iseq ${buildarch} i386'
        if boot['firmware']:
            gate += ' && iseq ${platform} ' + boot['firmware']
            if boot['firmware'] == 'efi':
                gate += ' && iseq ${buildarch} ' + rec['arch']
        return gate
    def filtro(rec):
        return 'iseq ${menu_arch} ' + rec['arch'] + ' && ' + puerta(rec)
    lin = ['#!ipxe', f'# Timestamp: {dt.date.today()} | Version: {VERSION}', f'# Author & Credits: {CREDITS}',
           '# iPXE commands: https://ipxe.org', '# Required local files checked; hardware boot tests are separate.',
           'cpair --foreground 2 --background 0 0 || goto colour_missing',
           '# Firmware text consoles require basic ANSI; RGB parameters reset some BIOS/EFI attributes.',
           'colour --basic 0 0 ||', 'colour --basic 1 1 ||',
           'colour --basic 2 2 ||', 'colour --basic 4 4 ||', 'colour --basic 6 6 ||',
           'cpair --foreground 2 --background 0 0 ||',
           'cpair --foreground 4 --background 0 1 ||',
           'cpair --foreground 4 --background 0 2 ||',
           'cpair --foreground 4 --background 0 3 ||',
           'cpair --foreground 4 --background 0 4 ||',
           'cpair --foreground 1 --background 0 5 ||',
           'cpair --foreground 1 --background 0 6 ||',
           'cpair --foreground 4 --background 0 7 ||',
           'cpair --foreground 2 --background 0 0 && console --keep || goto colour_missing',
           'goto colour_ready', ':colour_missing',
           'echo Colour support unavailable. Rebuild the USB with CONSOLE_CMD enabled.',
           ':colour_ready',
           'set menu_back start', 'set cpu_arch ${buildarch}',
           'iseq ${buildarch} i386 && cpuid --ext 29 && set cpu_arch x86_64 ||',
           'set menu_arch ${cpu_arch}',
           'set auto_timeout 0', 'set auto_target nav_assistance',
           'isset ${ip} || dhcp || goto error']
    # Override oldest with newest only when the inspected media has a complete matching recipe.
    asistencia = sorted((rec for rec in rec_all if rec.get('assistance_boot') and rec.get('_boot')),
                         key=orden_asistencia)
    for rec in asistencia:
        gate = puerta(rec)
        lin.extend([gate + ' && set auto_target ' + rec['id'] + ' ||',
                    gate + ' && set auto_timeout ' + str(getattr(cfg, 'boot', {}).get('assist_timeout_seconds', 60) * 1000) + ' ||',
                    gate + ' && set auto_label ' + rec['family'].title() + ' ' + rec['release'] + ' ||'])
    lin.extend([':start', 'set menu_back start', 'cpair --foreground 2 --background 0 0 ||',
                f'menu WAN Arsenal / iPXE / {urlsplit(cfg.pxe_url).netloc} / ${{menu_arch}}'])
    arbol = gen_arbol(rec_all)
    # The default remains ordinary assistance. AI is an explicit manual selection.
    ia_all = [rec for rec in asistencia if rec.get('ai_assist')]
    if not getattr(cfg, 'ai', {}).get('enabled', True):
        ia_all = []
    por_id = {rec['id']: rec for rec in rec_all}
    for nodo in arbol:
        lin.append(f'item --key {nodo["number"]} {nodo["id"]} {nodo["number"]}. {nodo["label"]}')
        if nodo['category'] == 'assistance':
            lin.append('isset ${auto_label} && item ${auto_target} 0.0. Start assistance / ${auto_label} ||')
            if ia_all:
                lin.append('item ai_menu 0.A. GPT Assist / Gemini Assist (API)')
    lin += ['item --gap --', 'item arch_menu Architecture: ${menu_arch} / firmware: ${platform}',
            'item boards ARM boards / U-Boot', 'item cloud_info Cloud images / VM', 'item shell Open iPXE shell', 'item reboot Reboot', 'item exit Boot local disk',
            'choose --default ${auto_target} --timeout ${auto_timeout} --retimeout 0 target || goto cancelled',
            'set auto_timeout 0', 'goto ${target}', ':cancelled', 'set auto_timeout 0', 'goto start']
    def submenu(nodo, padre, ruta):
        titulo = ruta + [nodo['label']]
        lin.extend(['', ':' + nodo['id'], 'set menu_back ' + nodo['id'], 'menu ' + ' / '.join(titulo)])
        for hijo in nodo['children']:
            lin.append(f'item {hijo["id"]} {hijo["number"]}. {hijo["label"]}')
        entries = [por_id[rid] for rid in nodo['resources'] if por_id[rid].get('_boot')]
        lin.append('set menu_items 0')
        for rec in entries:
            boot = rec['_boot']
            gate = filtro(rec)
            lin.append(f'{gate} && item {rec["id"]} {rec["name"]} [{rec["release"]}, {rec["arch"]}] ||')
            lin.append(gate + ' && set menu_items 1 ||')
        if not nodo['children']:
            lin.extend(['iseq ${menu_items} 0 && item --gap -- No compatible complete boot recipe in this branch. ||',
                        'item --gap -- Downloads and image files: ' + cfg.base_url + '/'])
            if nodo['id'].endswith('_chroot'):
                lin.append('item --gap -- Chroot is entered from a running Linux environment.')
        lin.extend(['item --gap --', 'item ' + padre + ' Back'])
        if padre != 'start':
            lin.append('item start Main menu')
        lin.extend(['item shell Open iPXE shell',
                    'choose target && goto ${target} || goto ' + padre])
        for hijo in nodo['children']:
            submenu(hijo, nodo['id'], titulo)
    for nodo in arbol:
        submenu(nodo, 'start', [])
    if ia_all:
        lin += ['', ':ai_menu', 'set auto_timeout 0', 'set menu_back ai_menu',
                'menu Optional API terminals / choose after boot; temporary API key required']
        for rec in ia_all:
            for prov, titulo in [('openai', 'GPT Assist'), ('gemini', 'Gemini Assist')]:
                lin.append(filtro(rec) + ' && item ai_' + prov + '_' + rec['id'] + ' ' + titulo +
                           ' / ' + rec['filename'] + ' ||')
        lin += ['item start Back', 'choose target && goto ${target} || goto start']
        for rec in ia_all:
            for prov in ('openai', 'gemini'):
                lin += ['', ':ai_' + prov + '_' + rec['id'], puerta(rec) + ' || goto incompatible', 'imgfree']
                lin += [cmd.replace(' || goto error', ' aux.ai=' + prov + ' || goto error', 1)
                        if cmd.startswith('kernel ') else cmd for cmd in rec['_boot']['commands']]
                lin += ['goto ai_menu']
    for rec in rec_all:
        boot = rec.get('_boot')
        if boot:
            lin += ['', ':' + rec['id'], 'set auto_timeout 0', 'cpair --foreground 1 --background 0 0 ||',
                    puerta(rec) + ' || goto incompatible', 'echo Starting ' + rec['filename'], 'imgfree'] + boot['commands'] + ['goto ${menu_back}']
    lin += ['', ':arch_menu', 'set auto_timeout 0', 'menu Architecture / compatible boot targets',
            'item arch_auto Auto / ${cpu_arch}',
            'iseq ${buildarch} i386 && item arch_i386 i386 / 32-bit PC ||',
            'iseq ${cpu_arch} x86_64 && item arch_x86_64 x86_64 / 64-bit PC ||',
            'iseq ${cpu_arch} arm64 && item arch_arm64 ARM64 / AArch64 ||',
            'item start Back', 'choose target && goto ${target} || goto start',
            ':arch_auto', 'set menu_arch ${cpu_arch}', 'goto start',
            ':arch_i386', 'set menu_arch i386', 'goto start',
            ':arch_x86_64', 'set menu_arch x86_64', 'goto start',
            ':arch_arm64', 'set menu_arch arm64', 'goto start',
            ':boards', 'set auto_timeout 0', 'echo U-Boot is board-specific firmware, not a universal ISO.',
            'echo Guide: ' + cfg.base_url + '/architectures.html#uboot', 'prompt Press any key...', 'goto start',
            ':cloud_info', 'set auto_timeout 0', 'echo Debian and Fedora: netinstall for installation; QCOW2 for VM import.',
            'echo Downloads: ' + cfg.base_url + '/architectures.html#cloud', 'prompt Press any key...', 'goto start',
            ':incompatible', 'set auto_timeout 0', 'echo Incompatible CPU or firmware.', 'prompt Press any key...', 'goto start']
    lin += ['', ':shell', 'shell', 'goto ${menu_back}', ':reboot', 'reboot', ':exit', 'exit', ':error',
            'set auto_timeout 0', 'cpair --foreground 1 --background 0 0 ||',
            'echo Boot failed. Check the HTTP paths, payload files and client firmware.',
            'prompt Press any key to return...', 'cpair --foreground 2 --background 0 0 ||',
            'goto ${menu_back}', '']
    return '\n'.join(lin)



def gen_sitemap(rec_all, cfg, host='aux'):
    ns = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', ns)
    root = ET.Element('{' + ns + '}urlset')
    base = cfg.pxe_url if host == 'pxe' else cfg.base_url
    visibles = [rec for rec in rec_all if rec['status'] not in ('checksum-failed', 'invalid-payload')]
    loc_all = [base + '/', base + '/contents.html', base + '/operations.html', base + '/chroot.html',
               base + '/iso-guide.html', base + '/tec-502.html', base + '/configuration.html', base + '/next-key.html', base + '/alpine-guide.html', base + '/architectures.html', base + '/usb-guide.html', base + '/debian-deploy.html',
               base + '/chroot-all.html', base + '/work.html', base + '/release-6.html'] + [base + '/files/' + rec['id'] + '.html' for rec in visibles]
    loc_all += [base + '/' + nom for rec in visibles for nom in rec.get('_content_pages', [])]
    if USB_FILES:
        loc_all += [base + '/downloads/usb/aux-ipxe-usb.img']
    if host == 'pxe':
        loc_all += [base + '/menu.ipxe']
        loc_all += [obt_local_url(rec, cfg) for rec in visibles if rec['published']]
        loc_all += [obt_contents_url(rec, cfg) for rec in visibles if obt_contents_url(rec, cfg)]
    for loc in dict.fromkeys(loc_all):
        url = ET.SubElement(root, '{' + ns + '}url')
        ET.SubElement(url, '{' + ns + '}loc').text = loc
        ET.SubElement(url, '{' + ns + '}lastmod').text = dt.date.today().isoformat()
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)



def obt_local_url(rec, cfg):
    """Boot recipes and individual image files always stay on Excalibur."""
    return cfg.pxe_url + '/' + quote(rec.get('path', rec['filename']), safe='/') + ('/' if rec['format'] == 'TREE' else '')


def obt_downloads(rec, cfg):
    if rec['format'] == 'TREE':
        return {}
    if rec['status'] in ('checksum-failed', 'invalid-payload'):
        return {'source': rec['url']}
    urls = {'bastion': getattr(cfg, 'download_url', 'https://b.1-s.es') + '/' + quote(rec.get('path', rec['filename']), safe='/')}
    if rec['published'] or rec['status'] == 'source':
        if getattr(cfg, 'target', None) == 'bastion':
            base_exc = getattr(cfg, 'targets', {}).get('excalibur', {}).get('pxe_url', cfg.pxe_url)
            urls['excalibur'] = base_exc.rstrip('/') + '/' + quote(rec.get('path', rec['filename']), safe='/')
        else:
            urls['excalibur'] = obt_local_url(rec, cfg)
    urls['source'] = rec['url']
    return urls


def obt_preferred_url(rec, cfg):
    """Complete media defaults to Bastion; a tree is never a Bastion download."""
    if rec['format'] == 'TREE':
        return obt_contents_url(rec, cfg) or obt_local_url(rec, cfg)
    return next(iter(obt_downloads(rec, cfg).values()))



def obt_contents_path(rec):
    if rec.get('contents_ready') and rec['published'] and rec['status'] != 'checksum-failed':
        return 'contents/' + rec['id'] + '/index.html'
    return None


def obt_contents_url(rec, cfg):
    pth = obt_contents_path(rec)
    return cfg.pxe_url + '/' + pth if pth else None


SERVER_LABELS = {'bastion': 'Bastion · France', 'excalibur': 'Excalibur · Canada', 'source': 'Original URL'}


def gen_server_links(rec, cfg):
    return ' | '.join('<a href="' + html.escape(url, quote=True) + '">' +
                      SERVER_LABELS[key] + '</a>' for key, url in obt_downloads(rec, cfg).items())


def gen_rows(rec_all, cfg):
    """The first HTTP response contains every resource and download link."""
    symbols = {'debian': '◉', 'fedora': 'f', 'ubuntu': '◌', 'arch': 'A', 'gentoo': 'g',
               'kali': 'K', 'proxmox': '×', 'clonezilla': 'C', 'gparted': '▥',
               'memtest': '▤', 'netboot': '↗', 'dban': 'D', 'supergrub': 'S', 'bootrepair': '↻'}
    rows = []
    por_id = {rec['id']: rec for rec in rec_all}
    for nodo, nivel in recorre_arbol(gen_arbol(rec_all)):
        if not obt_ids(nodo) and nodo['category'] != 'assistance':
            continue
        label = html.escape(nodo['number'] + '. ' + nodo['label'])
        rows.append(f'<tr id="{nodo["id"]}" class="category-heading tree-level-{nivel}"><th colspan="5" scope="colgroup">{label}</th></tr>')
        if nodo['category'] == 'assistance' and not nodo['resources']:
            rows.append('<tr><td colspan="5">No assistance ISO deployed yet. '
                        f'<a href="{html.escape(obt_tec_url(cfg), quote=True)}/">Choose a technician</a></td></tr>')
        for rid in nodo['resources']:
            rec = por_id[rid]
            val = {key: html.escape(str(value), quote=True) for key, value in rec.items()}
            detail = 'files/' + val['id'] + '.html'
            url = html.escape(obt_preferred_url(rec, cfg), quote=True)
            arch = 'ARM64' if rec['arch'] == 'arm64' else val['arch']
            url_tree = obt_contents_path(rec)
            if rec['format'] == 'TREE' and url_tree:
                url = html.escape(url_tree, quote=True)
            nav_tree = ('<a class="contents-link" href="' + html.escape(url_tree, quote=True) + '">Browse files · Excalibur</a>') if url_tree else ''
            kind = html.escape(rec.get('kind', 'tool').title())
            servers = gen_server_links(rec, cfg)
            action = 'Browse files' if rec['format'] == 'TREE' else 'Download'
            rows.append(f'''<tr>
    <td><div class="resource-cell"><span class="distro-icon {val['family']}" aria-hidden="true">{symbols.get(rec['family'], '↗')}</span><div><a class="resource-name" href="{detail}">{val['name']}</a><span class="resource-filename" title="{val['filename']}">{val['filename']}</span>{nav_tree}</div></div></td>
    <td><span class="release">{val['release']}</span></td><td><span class="arch-badge">{arch}</span></td><td><span class="format-badge">{val['format']}</span><small class="media-kind">{kind}</small></td>
    <td><div class="row-actions"><a class="download-link" href="{url}" aria-label="{action} {val['filename']}">{action} <span aria-hidden="true">↓</span></a><a class="details-button" href="{detail}" aria-label="Details for {val['name']}">⋯</a></div><div class="server-links">{servers}</div></td>
    </tr>''')
    return '\n'.join(rows)



def gen_plain_page(title, body, asset_base='assets/', language='en'):
    """Small standalone terminal-style HTML for Links/Lynx: no assets or scripts."""
    return f'''<!doctype html>
<!-- Timestamp: {dt.date.today()} | Version: {VERSION} | Author & Credits: {CREDITS} -->
<html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} | PXE_</title>
<style>
@font-face {{ font-family: "PXE Bits"; src: url("{asset_base}pxe-bits.ttf") format("truetype"); font-display: swap; unicode-range: U+0045,U+0050,U+0058,U+005F; }}
body {{ color: #f8fafc; background: #0f172a; max-width: 100ch; margin: 2rem auto; padding: 0 1rem; font: 15px/1.5 ui-monospace, SFMono-Regular, Consolas, monospace; }}
a {{ color: #34d399; text-decoration: underline; }}
a:hover {{ color: #6ee7b7; background: #1e293b; }}
h1, h2, h3, h4 {{ color: #38bdf8; font-weight: 600; }}
h1 {{ border-bottom: 2px solid #38bdf8; padding-bottom: .6rem; }}
p {{ color: #cbd5e1; }}
li {{ padding: .35rem 0; overflow-wrap: anywhere; }}
pre {{ color: #f8fafc; background: #1e293b; border: 1px solid #475569; padding: 1rem; white-space: pre-wrap; overflow-wrap: anywhere; }}
hr {{ border: 0; border-top: 1px solid #334155; }}
details {{ margin: .65rem 0; }}
summary {{ color: #38bdf8; cursor: pointer; padding: .35rem 0; font-weight: 600; overflow-wrap: anywhere; }}
summary:hover {{ color: #7dd3fc; text-decoration: underline; }}
summary h2, summary h3, summary h4 {{ display: inline; font-size: 1em; }}
.menu-branch {{ border-left: 1px dashed #475569; margin: .35rem 0 .8rem .5rem; padding-left: 1.2rem; }}
.menu-branch ul {{ padding-left: 1.3rem; }}
.mirror-panel {{ border: 1px dashed #fbbf24; background: #1e293b; padding: 1rem; margin: 1.5rem 0; }}
.mirror-panel > strong {{ color: #fbbf24; }}
.iso-link {{ color: #fbbf24; font-weight: 600; }}
.dir-link {{ color: #c4b5fd; font-weight: 600; }}
.bin-link {{ color: #f9a8d4; }}
.badge {{ color: #94a3b8; font-size: .9em; }}
.pxe-wordmark {{ color: #57f578; background: #06120a; font-family: "PXE Bits", ui-monospace, monospace; font-weight: normal; letter-spacing: .02em; padding: .12em .2em; white-space: nowrap; }}
.tec-wordmark {{ color: #a5b4fc; font-family: ui-monospace, "Liberation Mono", Consolas, monospace; font-weight: 600; letter-spacing: -.04em; }}
.pxe-cursor {{ animation: pxe-blink 1.2s steps(1, end) infinite; }}
@keyframes pxe-blink {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}
@media (prefers-reduced-motion: reduce) {{ .pxe-cursor {{ animation: none; }} }}
h1 .pxe-wordmark {{ display: block; width: fit-content; font-size: 2.5rem; line-height: 1.2; margin-bottom: .35rem; }}
table {{ width: 100%; border-collapse: collapse; text-align: left; margin: 1rem 0; }}
th, td {{ padding: .65rem; border-bottom: 1px solid #334155; vertical-align: top; overflow-wrap: anywhere; }}
th {{ color: #7dd3fc; }}
.view-nav {{ display: flex; flex-wrap: wrap; align-items: center; gap: .6rem 1.2rem; margin: 1rem 0; }}
.view-nav a {{ display: inline-block; }}
.catalog-tree {{ border-top: 1px solid #334155; border-bottom: 1px solid #334155; margin: 1.5rem 0; padding: .5rem 0; }}
.catalog-tree ul {{ list-style: none; padding-left: 1.5rem; }}
.catalog-tree > ul {{ padding-left: 0; }}
.catalog-tree li {{ padding: .15rem 0; }}
.view-nav .aux-switch {{ color: #f8fafc; }}
.aux-wordmark {{ font: 800 1.8rem/1.2 "Helvetica Neue", Arial, sans-serif; letter-spacing: -.08em; }}
.aux-wordmark span, .aux-wordmark i {{ color: #f18a5b; }}
.aux-wordmark i {{ font-style: normal; font-weight: 400; margin-left: .25em; }}
a:focus-visible, summary:focus-visible {{ outline: 2px solid #38bdf8; outline-offset: 4px; }}
</style></head>
<body>
{body}
<hr>{pie_licencia()}
</body></html>
'''



def gen_view_nav(cfg, pth=''):
    """Plain text links also switch portals in browsers without CSS or JavaScript."""
    aux = html.escape(cfg.base_url + '/' + pth, quote=True)
    pxe = html.escape(cfg.pxe_url + '/' + pth, quote=True)
    return f'<nav class="view-nav" aria-label="Portal selection"><a class="aux-switch" href="{aux}"><span class="aux-wordmark">aux<span>.</span><i>/</i></span> Visual catalog</a><a href="{pxe}"><span class="pxe-wordmark">PXE&gt;<span class="pxe-cursor">_</span></span> Terminal / Links</a><a href="{html.escape(obt_tec_url(cfg), quote=True)}/"><span class="tec-wordmark">tec.*</span> Técnicos / asistencia</a></nav>'


def gen_cli_page(rec_all, cfg, expanded=False):
    aux = html.escape(cfg.base_url, quote=True)
    nom_local = 'Bastion' if getattr(cfg, 'target', None) in ('bastion', 'contingency') else 'Excalibur'
    body = [f'''<h1><span class="pxe-wordmark">PXE&gt;<span class="pxe-cursor">_</span></span>Downloads &amp; network boot</h1>
<nav class="view-nav" aria-label="Main navigation"><a class="aux-switch" href="{aux}/"><span class="aux-wordmark">aux<span>.</span><i>/</i></span> Visual catalog</a><a href="{html.escape(cfg.pxe_url, quote=True)}/"><span class="pxe-wordmark">PXE&gt;<span class="pxe-cursor">_</span></span> Terminal / Links</a><a href="{html.escape(obt_tec_url(cfg), quote=True)}/?view=pxe"><span class="tec-wordmark">tec.*</span> Técnicos / asistencia</a><a href="contents.html">Browse ISO files</a><a href="#nav_distribution">Distros</a><a href="#nav_tools">Tools</a><a href="#network">iPXE</a></nav>
<section class="mirror-panel" aria-label="Download routing"><strong>[ DOWNLOAD ROUTER ]</strong>
<p>Complete downloads default to <strong>Bastion · France</strong>. Choose Excalibur · Canada or the upstream beside any file. PXE and individual files inside deployed images use <strong>{nom_local}</strong>.</p>
<p>Open "commands" for resumable wget/curl commands for each server, file size and SHA-256. All links work in Links/Lynx without JavaScript.</p>
<p><a href="cli.html">[ Compact menus ]</a> | <a href="cli-all.html">[ All expanded ]</a> | <a href="downloads/isos.tsv">[ ISO list / TSV ]</a></p></section>''']
    def entries(records):
        lines = ['<ul>']
        for rec in records:
            url = html.escape(obt_preferred_url(rec, cfg), quote=True)
            source = nom_local + ' tree' if rec['format'] == 'TREE' else 'Bastion default' if 'bastion' in obt_downloads(rec, cfg) else 'upstream'
            url_tree = obt_contents_path(rec)
            if rec['format'] == 'TREE' and url_tree:
                url = html.escape(url_tree, quote=True)
            nav_tree = (' | <a class="dir-link" href="' + html.escape(url_tree, quote=True) + '">[DIR] browse contents / individual files · ' + nom_local + '</a>') if url_tree else ''
            cls = 'dir-link' if rec['format'] == 'TREE' else 'iso-link' if rec['format'] in ('ISO', 'TAR.GZ', 'ISO.ZIP', 'IMG.XZ') else 'bin-link'
            lines.append(f'<li><a class="{cls}" href="{url}">[{html.escape(rec["format"])}] {html.escape(rec["filename"])}</a> '
                         f'<span class="badge">[{html.escape(rec["arch"])}; {source}]</span> '
                         f'<a href="files/{rec["id"]}.html">commands</a>{nav_tree}<br>'
                         f'{gen_server_links(rec, cfg)}</li>')
        return '\n'.join(lines + ['</ul>']) if records else '<p>No files in this group.</p>'
    arbol = gen_arbol(rec_all)
    por_id = {rec['id']: rec for rec in rec_all}
    def menu(nodo, nivel=0):
        tag = 'h' + str(nivel + 2)
        title = html.escape(nodo['number'] + '. ' + nodo['label'])
        # Native disclosure controls need no JavaScript; the expanded page is a text-browser fallback.
        opened = ' open' if expanded or nodo['id'] in ('nav_assistance', 'nav_distribution') else ''
        lines = [f'<details{opened}><summary><{tag} id="{nodo["id"]}">{title}</{tag}></summary><div class="menu-branch">']
        if nodo['category'] == 'assistance':
            lines.append('<p>The latest complete compatible assistance image starts after 60 seconds in iPXE. '
                         'Any key stops the timer; remote access still requires consent inside the ISO. '
                         f'<a href="{html.escape(obt_tec_url(cfg), quote=True)}/?view=pxe">[ Choose a technician ]</a></p>')
            if not nodo['resources']:
                lines.append('<p>No assistance ISO deployed yet.</p>')
        if nodo['id'].endswith('_chroot'):
            lines.append('<p>Gentoo media for entering a Linux environment and preparing a chroot. A chroot session starts inside a running system.</p>')
        for child in nodo['children']:
            lines.append(menu(child, nivel + 1))
        if nodo['resources']:
            lines.append(entries([por_id[rid] for rid in nodo['resources']]))
        return '\n'.join(lines + ['</div></details>'])
    body.extend(menu(nodo) for nodo in arbol)
    body += ['<h2>Guías operativas</h2><p><a href="work.html">[ /work RAM ]</a> | <a href="release-6.html">[ 6.0 CLI ]</a> | <a href="operations.html">[ FTP y permisos ]</a> | '
             '<a href="chroot.html">[ Chroot por distribución ]</a> | '
             '<a href="chroot-all.html">[ Chroot: todo abierto / Links ]</a> | '
             '<a href="iso-guide.html">[ Crear una ISO / manifiesto AUX Rescue ]</a> | <a href="usb-guide.html">[ Llave USB ]</a> | <a href="architectures.html">[ IoT / U-Boot / Cloud ]</a> | <a href="debian-deploy.html">[ Servidor Debian ]</a> | '
             '<a href="tec-502.html">[ TEC: diagnosticar 502 ]</a></p>']
    body.append(TEMPLATES.get('operations.html', ''))
    body.append(TEMPLATES.get('chroot.html', ''))
    body += ['<h2><a id="network" name="network"></a>Network boot · Excalibur</h2>',
             '<p>At the iPXE prompt, after preparing the mirror:</p><pre>' + html.escape('dhcp\nchain ' + cfg.pxe_url + '/menu.ipxe') + '</pre>',
             '<h2>Project files</h2><p><a href="downloads/aux-fast-boot.zip">Command bundle</a> | <a href="downloads/DEPLOYMENT.md">Deployment notes</a> | <a href="downloads/light-url.txt">light-url.txt / RAM</a> | <a href="downloads/heavy-url.txt">heavy-url.txt / disk</a> | <a href="downloads/url.txt">url.txt / all</a> | <a href="menu.ipxe">menu.ipxe</a> | <a href="sitemaps-pxe.xml">PXE sitemap</a></p>',
             '<p>Remote availability has not been checked. Resume depends on the download server. Verify images using the distribution\'s published checksums/signatures.</p>']
    if USB_FILES:
        usb_links = ['<a href="downloads/usb/aux-ipxe-usb.img">aux-ipxe-usb.img</a>']
        for nom, label in [('SHA256SUMS', 'SHA256SUMS'), ('README.md', 'USB instructions')]:
            if 'usb/' + nom in SOURCE_FILES:
                usb_links.append(f'<a href="downloads/usb/{nom}">{label}</a>')
        body += ['<h2>USB boot client</h2><p>' + ' | '.join(usb_links) + '</p>'
                 '<p>BIOS and x86_64 UEFI. DHCP and menu loading are automatic. '
                 'The custom UEFI executable is unsigned.</p>']
    txt_body = '\n'.join(body)
    if expanded:
        txt_body = re.sub(r'<details(?![^>]*\bopen\b)([^>]*)>', r'<details open\1>', txt_body)
    return gen_plain_page('Downloads & network boot', txt_body)



def gen_resource_page(rec, cfg):
    url_pxe = getattr(cfg, 'pxe_url', cfg.base_url)
    url = obt_preferred_url(rec, cfg)
    name = rec['filename']
    cmd_wget = 'wget -c -O ' + shlex.quote(name) + ' -- ' + shlex.quote(url)
    cmd_curl = 'curl -fL -C - -o ' + shlex.quote(name) + ' -- ' + shlex.quote(url)
    local = rec['published'] and rec['status'] != 'checksum-failed'
    size = str(rec['size']) + ' bytes' if rec['size'] is not None else 'Recorded after sync'
    body = f'''<p><a href="{html.escape(url_pxe, quote=True)}/">All downloads (text)</a> | <a href="{html.escape(cfg.base_url, quote=True)}/">Visual catalog</a></p>
<h1>{html.escape(name)}</h1>
<p>{html.escape(rec['name'])} / {html.escape(rec['arch'])} / {html.escape(rec['format'])}</p>
<p><a href="{html.escape(url, quote=True)}">Download {html.escape(name)}</a></p>
<p>Download server: {'Bastion · France (default)' if 'bastion' in obt_downloads(rec, cfg) else 'Upstream'}. Size on Excalibur: {html.escape(size)}.</p>
<p>Choose a server: {gen_server_links(rec, cfg)}</p>
<p>Bastion availability is not inferred from Excalibur. Both mirrors must contain the same file/version.</p>
<h2>Download over SSH</h2>
<p>Run either command in the destination directory. Rerun the same command to resume if the server supports HTTP Range requests. Both commands keep the full filename, including for SourceForge redirects.</p>
<h3>wget</h3><pre>{html.escape(cmd_wget)}</pre>
<h3>curl</h3><pre>{html.escape(cmd_curl)}</pre>
<h2>SHA-256</h2>'''
    if local and rec['sha256']:
        cmd_hash = "printf '%s\\n' " + shlex.quote(rec['sha256'] + '  ' + name) + ' | sha256sum -c -'
        body += '<pre>' + html.escape(cmd_hash) + '</pre><p>This hash checks against the local mirror copy. Authenticate the image separately with the distribution\'s signed checksums.</p>'
    else:
        body += '<p>No local checksum recorded. Obtain the checksum/signature from the distribution.</p>'
    for key, alt_url in obt_downloads(rec, cfg).items():
        if alt_url == url:
            continue
        cmd = 'wget -c -O ' + shlex.quote(name) + ' -- ' + shlex.quote(alt_url)
        cmd_alt = 'curl -fL -C - -o ' + shlex.quote(name) + ' -- ' + shlex.quote(alt_url)
        body += '<h2>' + SERVER_LABELS[key] + '</h2><pre>' + html.escape(cmd) + '</pre><pre>' + html.escape(cmd_alt) + '</pre>'
    url_tree = '../' + obt_contents_path(rec) if obt_contents_path(rec) else None
    if url_tree:
        body += '<h2>Image contents · Excalibur</h2><p><a href="' + html.escape(url_tree, quote=True) + '">Browse the mounted or extracted files</a></p>'
        for label, rel in rec.get('boot_files', {}).items():
            url_file = cfg.pxe_url + '/' + quote(rec['tree'] + '/' + rel, safe='/')
            body += '<p>' + html.escape(label) + ': <a href="' + html.escape(url_file, quote=True) + '">' + html.escape(rel) + '</a></p>'
    elif rec.get('tree_error'):
        body += '<p>' + html.escape(rec['tree_error']) + '</p>'
    body += '<p>Resume only the same file/version. After a server-side replacement, download a fresh copy and verify it.</p>'
    body += '<p><a href="' + html.escape(rec['url'], quote=True) + '">Configured upstream</a></p>'
    if rec['format'] == 'TREE':
        url = url_tree or url
        body = f'<p><a href="{html.escape(url_pxe, quote=True)}/">All downloads (text)</a></p><h1>{html.escape(name)}</h1><p>Public boot tree.</p><p><a href="{html.escape(url, quote=True)}">Browse files</a></p>'
    if rec.get('_boot'):
        body += '<h2>iPXE recipe</h2><pre>' + html.escape('\n'.join(rec['_boot']['commands'])) + '</pre>'
    return gen_plain_page(name, body, '../assets/')



def gen_contents(rec_all, cfg):
    """Index original trees outside their read-only mounts; preserve every file URL."""
    artifacts, groups = {}, {}
    esc = lambda value: html.escape(str(value), quote=True)
    for rec in rec_all:
        rec['_content_pages'] = []
        if not obt_contents_url(rec, cfg):
            continue
        root = (cfg.output / rec['tree']).resolve()
        if not root.is_dir():
            rec['contents_ready'] = False
            continue
        pages, stack, file_rows = {}, [('', frozenset())], []
        def page_name(rel):
            return 'contents/' + rec['id'] + '/' + ('index' if not rel else hashlib.sha256(rel.encode()).hexdigest()[:24]) + '.html'
        while stack:
            rel, ancestors = stack.pop()
            directory = root / rel
            try:
                resolved = directory.resolve()
                if resolved in ancestors or not resolved.is_relative_to(root):
                    continue
                children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))
            except (OSError, RuntimeError):
                continue
            ancestors = ancestors | {resolved}
            entries = []
            for child in children:
                # Only installer metadata is public among dotfiles; never expose host configuration.
                if child.name.startswith('.') and child.name not in ('.treeinfo', '.discinfo'):
                    continue
                try:
                    target = child.resolve()
                    if not target.is_relative_to(root) or target in ancestors:
                        continue
                    sub = child.relative_to(root).as_posix()
                    if child.is_dir():
                        stack.append((sub, ancestors))
                        entries.append((child.name + '/', sub, None))
                    elif child.is_file():
                        size = child.stat().st_size
                        entries.append((child.name, sub, size))
                        url = cfg.pxe_url + '/' + quote(rec['tree'] + '/' + sub, safe='/')
                        file_rows.append((quote(sub, safe='/'), str(size), url))
                except (OSError, RuntimeError):
                    continue
            pages[rel] = entries
        rec['contents_files'] = len(file_rows)
        rec['contents_dirs'] = max(0, len(pages) - 1)
        for rel, entries in pages.items():
            nav = gen_view_nav(cfg, page_name(rel)) + f'<p><a href="../../contents.html">All deployed images</a> | <a href="../../files/{rec["id"]}.html">Image &amp; commands</a></p>'
            body = nav + '<h1>' + esc(rec['tree'] + '/' + rel) + '/</h1>'
            body += '<p>Excalibur · Canada / original image paths. Select a file for a direct download.</p>'
            if rel:
                parent = Path(rel).parent.as_posix()
                body += '<p><a href="' + esc(Path(page_name('' if parent == '.' else parent)).name) + '">../ Parent directory</a></p>'
            body += '<ul>'
            for name, sub, size in entries:
                if size is None:
                    if sub not in pages:
                        continue
                    url = Path(page_name(sub)).name
                    label = 'directory'
                else:
                    url = cfg.pxe_url + '/' + quote(rec['tree'] + '/' + sub, safe='/')
                    label = f'{size:,} bytes'
                body += '<li><a href="' + esc(url) + '">' + esc(name) + '</a> — ' + label + '</li>'
            body += '</ul><p><a href="files.tsv">All file URLs (TSV)</a></p>'
            artifacts[page_name(rel)] = gen_plain_page(rec['filename'] + ' / ' + rel, body, '../../assets/')
        rec['_content_pages'] = [page_name(rel) for rel in pages]
        artifacts['contents/' + rec['id'] + '/files.tsv'] = 'path\tbytes\turl\n' + ''.join('\t'.join(row) + '\n' for row in sorted(file_rows))
        groups[rec['id']] = ('<li><a href="' + esc(obt_contents_path(rec)) + '">' + esc(rec['filename']) + '</a> — ' + str(rec['contents_files']) + ' files, ' + str(rec['contents_dirs']) + ' directories</li>')
    body = gen_view_nav(cfg) + '<h1>Browse ISO files / Excalibur</h1><p>Browse individual files inside mounted or extracted images from either AUX or PXE. Complete image downloads use Bastion by default; these files and PXE use Excalibur.</p>'
    presentes = [rec for rec in rec_all if rec['id'] in groups]
    arbol = gen_arbol(presentes)
    body += gen_catalog_nav(arbol)
    for nodo, nivel in recorre_arbol(arbol):
        tag = 'h' + str(nivel + 2)
        body += f'<{tag} id="{nodo["id"]}">' + esc(nodo['number'] + '. ' + nodo['label']) + f'</{tag}>'
        if nodo['resources']:
            body += '<ul>' + ''.join(groups[rid] for rid in nodo['resources']) + '</ul>'
        elif not nodo['children']:
            body += '<p>No deployed contents found in this group. Run deploy, then generate on Excalibur.</p>'
    artifacts['contents.html'] = gen_plain_page('Deployed image files', body)
    return artifacts


def configura_ejemplo(nom, txt, cfg):
    """Render deployment examples from central settings; never include credentials."""
    if nom.endswith(('nginx.conf.example', 'aux-pxe-tec.conf.example', 'php-fpm.conf.example', 'tec-pool.conf.example', 'aux-pool.conf.example')):
        tec = getattr(cfg, 'tec', {})
        tls = getattr(cfg, 'tls', {})
        txt = txt.replace('https://tec.1-s.es', obt_tec_url(cfg))
        txt = txt.replace('/var/www/aux.1-s.es/html', str(cfg.output))
        txt = txt.replace('/var/www/aux.1-s.es/web', tec.get('web_dir', '/var/www/aux.1-s.es/web'))
        txt = txt.replace('/etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem', tls.get('certificate', '/etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem'))
        txt = txt.replace('/etc/letsencrypt/live/ntp1.1-s.eu/privkey.pem', tls.get('key', '/etc/letsencrypt/live/ntp1.1-s.eu/privkey.pem'))
        for role in ['aux', 'pxe', 'tec']:
            hosts = getattr(cfg, 'hosts', {}).get(role)
            if hosts:
                txt = txt.replace('server_name ' + role + '.1-s.es ' + role + '.1-s.eu;', 'server_name ' + ' '.join(hosts) + ';')
        platform = 'debian' if nom.startswith('debian/') else getattr(cfg, 'platform', 'fedora')
        profile = getattr(cfg, 'php_profiles', {}).get(platform, {})
        for old in ['/run/php-fpm/www.sock', '/run/php/aux.sock']:
            txt = txt.replace(old, profile.get('aux_socket', old))
        for old in ['/run/php-fpm/tec.sock', '/run/php/tec.sock']:
            txt = txt.replace(old, profile.get('tec_socket', old))
        if nom.endswith(('php-fpm.conf.example', 'tec-pool.conf.example')):
            # Existing AUX_ASSIST_* environment overrides remain supported by PHP.
            txt = re.sub(r'^env\[AUX_ASSIST_(MAIL_FROM|PUBLIC_URL|DATA_DIR)\].*\n', '', txt, flags=re.M)
            txt = txt.replace('[tec]\n', '[tec]\nenv[AUX_ASSIST_CONFIG] = ' + tec.get('config_file', '/var/www/aux.1-s.es/fast-boot.json') + '\n')
            txt = txt.replace('tec@1wise.es', tec.get('mail_from', 'tec@1wise.es'))
            txt = txt.replace('/var/lib/php/tec-session', tec.get('session_dir', '/var/lib/php/tec-session'))
            usr = profile.get('web_user', 'www-data' if platform == 'debian' else 'nginx')
            txt = re.sub(r'^listen\.(owner|group) = .*$', lambda m: 'listen.' + m.group(1) + ' = ' + usr, txt, flags=re.M)
    return txt


def gen_pages(rec_all, cfg, state='synced'):
    crea_dir_publico(cfg.output)
    content_artifacts = gen_contents(rec_all, cfg)
    for rec in rec_all:
        rec['download_urls'] = obt_downloads(rec, cfg)
        rec['contents_url'] = obt_contents_url(rec, cfg)
        rec['contents_path'] = obt_contents_path(rec)
    datos = {'version': VERSION, 'state': state, 'base_url': cfg.base_url, 'pxe_url': cfg.pxe_url,
             'tec_enabled': getattr(cfg, 'tec_enabled', True),
             'download_url': getattr(cfg, 'download_url', 'https://b.1-s.es'), 'default_server': 'bastion', 'hierarchy': gen_arbol(rec_all),
             'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
             'resources': [{k: v for k, v in rec.items() if not k.startswith('_')} for rec in rec_all]}
    dat_json = json.dumps(datos, ensure_ascii=True, indent=2).replace('<', '\\u003c')
    pag = TEMPLATES['index.html'].replace('@@CANONICAL@@', html.escape(cfg.base_url + '/', quote=True))
    usb_link = ('<a href="downloads/usb/aux-ipxe-usb.img" download><span class="file-icon">USB</span>'
                '<span><strong>aux-ipxe-usb.img</strong><small>BIOS / x86_64 UEFI '
                '\u00b7 GRUB 5s, DHCP, iPXE \u00b7 unsigned UEFI</small></span>'
                '<span class="file-type">IMG</span><span class="file-arrow">\u2193</span></a>') if USB_FILES else ''
    for token, value in {
        '@@OPS_GUIDE@@': TEMPLATES.get('operations.html', ''),
        '@@CHROOT_GUIDE@@': TEMPLATES.get('chroot.html', ''),
        '@@HIERARCHY@@': gen_catalog_nav(datos['hierarchy']),
        '@@ROWS@@': gen_rows(rec_all, cfg), '@@COUNT@@': str(len(rec_all)),
        '@@LABEL@@': 'LOCAL CATALOG' if state == 'synced' else 'SOURCE CATALOG',
        '@@PXE_URL@@': html.escape(cfg.pxe_url, quote=True),
        '@@BASE_URL@@': html.escape(cfg.base_url, quote=True),
        '@@TEC_URL@@': html.escape(obt_tec_url(cfg), quote=True),
        '@@LICENSE@@': pie_licencia(),
        '@@USB_FILES@@': usb_link,
    }.items():
        pag = pag.replace(token, value)
    pag_html = pag.replace('@@CATALOG@@', dat_json)
    php_str = lambda val: "'" + val.replace('\\', '\\\\').replace("'", "\\'") + "'"
    cab_php = f'''<?php
/**
 * Timestamp: {dt.date.today()} | Version: {VERSION}
 * Author & Credits: {CREDITS}
 * Read the generated catalog from a fixed local path, without request-controlled redirects.
 */
$host = strtolower(explode(':', $_SERVER['HTTP_HOST'] ?? '', 2)[0]);
$cli_hosts = json_decode({php_str(json.dumps(getattr(cfg, 'bastion', {}).get('cli_hosts', ['p.1-s.es','p.1-s.eu']) + getattr(cfg, 'hosts', {}).get('pxe', ['pxe.1-s.es','pxe.1-s.eu'])))}, true);
if (in_array($host, $cli_hosts, true)) {{ readfile(__DIR__ . '/cli.html'); exit; }}
$arc_cat = __DIR__ . '/catalog.json';
$dat_cat = is_file($arc_cat) ? json_decode(file_get_contents($arc_cat), true) : array('resources' => array());
if (!is_array($dat_cat)) {{ $dat_cat = array('resources' => array()); }}
$dat_cat += array('base_url' => {php_str(cfg.base_url)}, 'pxe_url' => {php_str(cfg.pxe_url)});
?>
'''
    pag_php = cab_php + pag.replace('@@CATALOG@@', '<?php echo json_encode($dat_cat, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT); ?>')
    artifacts = {'index.html': pag_html, 'index.php': pag_php, 'catalog.json': dat_json,
                 'cli.html': gen_cli_page(rec_all, cfg), 'cli-all.html': gen_cli_page(rec_all, cfg, expanded=True), 'index-aux.php': pag_php,
                 'index-pxe.html': gen_cli_page(rec_all, cfg),
                 'menu.ipxe': gen_ipxe(rec_all, cfg), 'sitemaps.xml': gen_sitemap(rec_all, cfg),
                 'sitemaps-aux.xml': gen_sitemap(rec_all, cfg), 'sitemaps-pxe.xml': gen_sitemap(rec_all, cfg, 'pxe'),
                 'robots.txt': 'User-agent: *\nAllow: /\nSitemap: ' + cfg.base_url + '/sitemaps.xml\n',
                 'assets/portal.css': TEMPLATES['portal.css'], 'assets/portal.js': TEMPLATES['portal.js'],
                 'downloads/url.txt': SOURCE_FILES.get('url.txt', DEFAULT_URLS),
                 'downloads/DEPLOYMENT.md': TEMPLATES['DEPLOYMENT.md']}
    artifacts.update(content_artifacts)
    guia_chroot = TEMPLATES.get('chroot.html', '')
    artifacts['chroot.html'] = gen_plain_page('Chroot Linux', gen_view_nav(cfg) + guia_chroot)
    artifacts['chroot-all.html'] = gen_plain_page('Chroot Linux / Links', gen_view_nav(cfg) +
        re.sub(r'<details(?![^>]*\bopen\b)([^>]*)>', r'<details open\1>', guia_chroot))
    artifacts['operations.html'] = gen_plain_page('FTP and permissions', gen_view_nav(cfg) +
        re.sub(r'<details(?![^>]*\bopen\b)([^>]*)>', r'<details open\1>', TEMPLATES.get('operations.html', '')))
    for nom, titulo in [('usb-guide.html', 'Crear la llave USB'), ('debian-deploy.html', 'Despliegue Debian'), ('architectures.html', 'Arquitecturas, IoT y cloud'), ('alpine-guide.html', 'Alpine completo'), ('configuration.html', 'Configuración central'), ('next-key.html', 'Próxima llave y SSD')]:
        artifacts[nom] = gen_plain_page(titulo, gen_view_nav(cfg) + TEMPLATES.get(nom, ''), language='es')
    guia_iso = TEMPLATES.get('iso-guide.html', '<p>Install the complete source bundle to read the ISO guide.</p>')
    paquetes_iso = [lin.strip() for lin in SOURCE_FILES.get('iso/packages.txt', '').splitlines()
                    if lin.strip() and not lin.lstrip().startswith('#')]
    guia_iso = guia_iso.replace('@@ISO_PACKAGE_COUNT@@', str(len(paquetes_iso))).replace(
        '@@ISO_PACKAGES@@', html.escape('\n'.join(paquetes_iso)))
    artifacts['iso-guide.html'] = gen_plain_page('Construir una ISO / aux-rescue.iso', gen_view_nav(cfg) + guia_iso, language='es')
    artifacts['tec-502.html'] = gen_plain_page('TEC / diagnosticar 502', gen_view_nav(cfg) + TEMPLATES.get('tec-502.html', ''), language='es')
    for nom, titulo in [('release-6.html', 'AUX / WAN Arsenal / TEC 6.4 · Two terminals'), ('work.html', '/work · RAM de trabajo')]:
        texto = TEMPLATES.get(nom, '')
        if nom == 'work.html':
            texto = texto.replace('@@WORK_SOURCE@@', html.escape(SOURCE_FILES.get('iso/payload/work.py', '')))
        artifacts[nom] = gen_plain_page(titulo, gen_view_nav(cfg) + texto, language='es')
    artifacts['downloads/work.py'] = SOURCE_FILES.get('iso/payload/work.py', '')
    artifacts['downloads/work.py.sha256'] = hashlib.sha256(artifacts['downloads/work.py'].encode()).hexdigest() + '  work.py\n'
    if getattr(cfg, 'target', None) in ('bastion', 'contingency'):
        artifacts['.htaccess'] = SOURCE_FILES.get('ovh/shared.htaccess', '')
    artifacts['downloads/isos.tsv'] = 'filename\tarchitecture\turl\tsha256\n' + ''.join(
        '\t'.join([rec['filename'], rec['arch'], obt_preferred_url(rec, cfg),
                   (rec['sha256'] or '') if rec['published'] and rec['status'] != 'checksum-failed' else '']) + '\n'
        for rec in rec_all if rec['format'] == 'ISO')
    for rec in rec_all:
        artifacts['files/' + rec['id'] + '.html'] = gen_resource_page(rec, cfg)
    artifacts['downloads/index.php.txt'] = pag_php
    artifacts['downloads/menu.ipxe'] = artifacts['menu.ipxe']
    artifacts['downloads/sitemaps.xml'] = artifacts['sitemaps.xml']
    if 'iso/prepare.py' in SOURCE_FILES:
        # Package only declared public recipe files; never collect client/VPN configuration.
        buf_iso = io.BytesIO()
        with zipfile.ZipFile(buf_iso, 'w', compression=zipfile.ZIP_DEFLATED) as arc_iso:
            for nom in ISO_SOURCE_FILES + ['manifest.json']:
                if 'iso/' + nom in SOURCE_FILES:
                    arc_iso.writestr(nom, SOURCE_FILES['iso/' + nom])
        nom_iso = 'tec-fedora44-rescue-5.0.1-dev.5-sources.zip'
        artifacts['downloads/' + nom_iso] = buf_iso.getvalue()
        artifacts['downloads/' + nom_iso + '.sha256'] = hashlib.sha256(buf_iso.getvalue()).hexdigest() + '  ' + nom_iso + '\n'
        artifacts['downloads/iso-packages.txt'] = SOURCE_FILES.get('iso/packages.txt', '')
    for nom, val in BINARY_ASSETS.items():
        artifacts['assets/' + nom] = base64.b64decode(val)
    for nom, val in SOURCE_FILES.items():
        # PHP source downloads must remain inert; the ZIP retains their original names.
        artifacts['downloads/' + nom + ('.txt' if nom.endswith('.php') else '')] = configura_ejemplo(nom, val, cfg)
    for nom, val in USB_FILES.items():
        artifacts['downloads/' + nom] = val
    # TEC is optional navigation, independent of AUX/PXE generation and ISO use.
    if not getattr(cfg, 'tec_enabled', True):
        url_tec = re.escape(html.escape(obt_tec_url(cfg), quote=True))
        for nom in list(artifacts):
            if not nom.startswith('downloads/') and nom.endswith(('.html', '.php')) and isinstance(artifacts[nom], str):
                artifacts[nom] = re.sub(r'<a\b[^>]*href="' + url_tec + r'[^\"]*"[^>]*>.*?</a>', '', artifacts[nom], flags=re.S)
    # Previous generated files are recoverable, and unrelated directory contents are preserved.
    pth_bak = cfg.cache / 'backups' / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S')
    for nom, val in artifacts.items():
        pth = cfg.output / nom
        crea_dir_publico(pth.parent)
        byt = val if isinstance(val, bytes) else val.encode()
        if pth.is_file() and pth.read_bytes() != byt:
            des = pth_bak / nom
            des.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pth, des)
        esc_atomic(pth, byt)
        if nom.endswith('.sh'):
            ajusta_publico(pth, ejecutable=True)
    esc_atomic(cfg.output / 'SHA256SUMS', ''.join(f'{rec["sha256"]}  {rec.get("path", rec["filename"])}\n' for rec in rec_all if rec['published'] and rec['sha256'] and rec['status'] != 'checksum-failed'))
    pth_zip = cfg.output / 'downloads/aux-fast-boot.zip'
    tmp = pth_zip.with_suffix('.zip.tmp')
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_DEFLATED) as arc:
        # Ship one editable copy of the commands; ISO payloads stay in the cache.
        for nom in BINARY_ASSETS:
            arc.write(cfg.output / 'assets' / nom, 'assets/' + nom)
        for nom, val in SOURCE_FILES.items():
            ent = zipfile.ZipInfo(nom)
            ent.compress_type = zipfile.ZIP_DEFLATED
            ent.external_attr = (0o100755 if nom.endswith('.sh') else 0o100644) << 16
            arc.writestr(ent, val)
        for nom, val in USB_FILES.items():
            ent = zipfile.ZipInfo(nom)
            ent.compress_type = zipfile.ZIP_DEFLATED
            ent.external_attr = 0o100644 << 16
            arc.writestr(ent, val)
        if 'url.txt' not in SOURCE_FILES:
            arc.writestr('url.txt', artifacts['downloads/url.txt'])
        arc.writestr('DEPLOYMENT.md', TEMPLATES['DEPLOYMENT.md'])
    ajusta_publico(tmp)
    os.replace(tmp, pth_zip)
    return datos



def carga_recursos():
    global USB_FILES
    # Only generation needs visual assets; other commands never read them.
    tpl = {nom: (pth_app / 'src' / nom).read_text() for nom in
           ['index.html', 'portal.css', 'portal.js', 'DEPLOYMENT.md', 'operations.html', 'chroot.html']}
    tpl.update({nom: (pth_app / 'src' / nom).read_text() for nom in ['iso-guide.html', 'tec-502.html', 'usb-guide.html', 'debian-deploy.html', 'architectures.html', 'alpine-guide.html', 'configuration.html', 'next-key.html', 'release-6.html', 'work.html']
                if (pth_app / 'src' / nom).is_file()})
    bin_assets = {nom: base64.b64encode((pth_app / 'assets' / nom).read_bytes()).decode() for nom in ['aux-logo.png', 'favicon.png']}
    if (pth_app / 'assets/pxe-bits.ttf').is_file():
        bin_assets['pxe-bits.ttf'] = base64.b64encode((pth_app / 'assets/pxe-bits.ttf').read_bytes()).decode()
    # Other task files are optional downloads, never imported or executed.
    noms = ['download.sh', 'deploy.sh', 'generate.sh', 'fast-boot.json', 'url.txt', 'light-url.txt', 'heavy-url.txt',
            'alpine-sources.json', 'alpine-SHA256SUMS', 'CONFIGURATION.md', 'usb/NEXT-KEY.md', 'tec/MIGRATION-5.1.0.md', 'src/common.py', 'build.py', 'verify.py', 'verify-portal.cjs', 'verify-routing.py', 'TESTING.md',
            'usb/build.sh', 'usb/bootstrap.ipxe.in', 'usb/bootstrap.ipxe', 'usb/general.h',
            'usb/console.h', 'usb/colour.h', 'usb/grub.cfg', 'usb/grub-image.py', 'usb/LICENSE-GRUB.txt',
            'usb/README.md', 'usb/build-info.json', 'usb/SHA256SUMS',
            'nginx/aux-pxe-tec.conf.example', 'nginx/test_vhosts.py',
            'tec/php-fpm.conf.example', 'tec/postfix.conf.example', 'tec/MAIL.md', 'tec/MIGRATION-5.0.2.md',
            'tec/TROUBLESHOOTING.md', 'tec/REGISTRY.md', 'fonts/build-pxe-font.py', 'iso/packages.txt', 'iso/manifest.json']
    noms += ['debian/' + nom for nom in ['fast-boot.json', 'nginx.conf.example', 'aux-pool.conf.example', 'tec-pool.conf.example']]
    noms += ['iso/' + nom for nom in ISO_SOURCE_FILES]
    # Distribute public source only; no private profiles, key files or runtime state.
    for carpeta in ['cli', 'ovh', 'iso-assist']:
        noms += [arc.relative_to(pth_app).as_posix() for arc in sorted((pth_app / carpeta).rglob('*'))
                 if arc.is_file() and '__pycache__' not in arc.parts and arc.suffix in
                 ('.py', '.sh', '.service', '.json', '.txt', '.in', '.conf', '.md', '.example', '.htaccess')]
    noms += ['RELEASE-6.md', 'CHECKLIST-6.json', 'RELEASE-6.1.md', 'CHECKLIST-6.1.json', 'TEST-6.1.md',
             'RELEASE-6.2.md', 'CHECKLIST-6.2.json', 'TEST-6.2.md', 'INSTALL-6.2.md', 'RELEASE-6.3.md', 'CHECKLIST-6.3.json', 'TEST-6.3.md', 'INSTALL-6.3.md', 'install-web.py',
             'verify-v6.py', 'verify-v61.py', 'verify-v62.py', 'verify-v63.py',
             'usb/create-usb.sh', 'usb/create-usb.py', 'usb/USB-6.1.md', 'usb/USB-6.2.md', 'usb/USB-6.3.md']
    noms += ['RELEASE-6.4.md', 'CHECKLIST-6.4.json', 'TEST-6.4.md', 'INSTALL-6.4.md', 'verify-v64.py']
    noms += [arc.relative_to(pth_app).as_posix() for arc in sorted((pth_app / 'usb/portable').glob('*'))
             if arc.is_file() and arc.suffix in ('.py', '.md', '.json')]
    arc_src = {nom: (pth_app / nom).read_text() for nom in noms if (pth_app / nom).is_file()}
    arc_src.update({'src/' + nom: val for nom, val in tpl.items()})
    configura(arc_src.get('url.txt', ''), tpl, bin_assets, arc_src)
    # Publishing copies a prebuilt client; generation never downloads or compiles iPXE.
    pth_usb = pth_app / 'usb/aux-ipxe-usb.img'
    USB_FILES = {'usb/aux-ipxe-usb.img': pth_usb.read_bytes()} if pth_usb.is_file() else {}


def main():
    cfg = obt_args('generate', pth_app)
    if not cfg.dry_run:
        inicia_informe(cfg)
    rec_all = descubre([], cfg)
    if cfg.dry_run:
        muestra_plan(cfg, rec_all)
        return 0
    sumas = obt_sumas(cfg)
    carga_recursos()
    cfg.cache.mkdir(parents=True, exist_ok=True)
    crea_dir_publico(cfg.output)
    tms_ini = time.monotonic()
    with bloq_cache(cfg):
        # Re-scan under the lock so deployment cannot change the inventory mid-generation.
        rec_all = descubre([], cfg)
        for num, rec in enumerate(rec_all, 1):
            rec.update(_num=num, _total=len(rec_all))
        rec_all = rastrea(rec_all, cfg, sumas)
        cfg.resources = rec_all
        url_live = None
        if any(rec['published'] and rec['family'] in ('debian', 'clonezilla', 'gparted', 'kali')
               and (cfg.output / rec['tree'] / 'live/filesystem.squashfs').is_file() for rec in rec_all):
            url_live = obt_live_url(cfg)
        for rec in rec_all:
            rec['_boot'] = gen_boot(rec, cfg, url_live)
            rec['pxe_ready'] = bool(rec['_boot'])
            rec['boot_group'] = rec['_boot']['group'] if rec['_boot'] else None
            rec['pxe_reason'] = ('Required boot files found; hardware boot test pending' if rec['_boot'] else
                rec.get('error') or rec.get('tree_error') or rec.get('boot_error') or 'No complete supported network boot recipe found')
            if rec['published']:
                arc_pub = cfg.output / rec.get('path', rec['filename'])
                if arc_pub.exists() and arc_pub.is_file():
                    ajusta_publico(arc_pub, enlace=True)
                pth_tree = cfg.output / rec['tree']
                if rec.get('contents_ready') and pth_tree.is_dir():
                    ajusta_tree(pth_tree)
                msg_descarga(cfg, rec, 'PXE', rec['pxe_reason'])
        gen_pages(rec_all, cfg, 'synced')
        print(f'Generated AUX/PXE indexes, menu.ipxe and sitemaps in {cfg.output}')
        print(f'{sum(rec["pxe_ready"] for rec in rec_all)} complete boot file sets.')
        return fin_tarea(cfg, rec_all, tms_ini)


if __name__ == '__main__':
    raise SystemExit(ejecuta_main(main))
AUXPY
