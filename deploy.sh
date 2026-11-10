#!/usr/bin/env bash
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
# The task body lives here so the command can be reviewed and run on its own.
set -Eeuo pipefail
pth_app="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "${pth_app}" "$@" <<'AUXPY'
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Deploy only: RAM, disk or an FTP replica, without download or generation."""
import sys
import ftplib
import getpass
import ssl
from pathlib import Path

pth_app = Path(sys.argv.pop(1)).resolve() if __name__ == '__main__' else Path(__file__).resolve().parent
sys.path.insert(0, str(pth_app / 'src'))
from common import *


def pub_arc(pth_src, pth_dst, fisico=False, owned=False):
    if pth_src == pth_dst:
        ajusta_publico(pth_dst)
        return
    if pth_dst.is_symlink() and pth_dst.resolve() == pth_src.resolve() and not fisico:
        ajusta_publico(pth_dst, enlace=True)
        return
    if pth_dst.exists() and not pth_dst.is_symlink():
        es_igual = pth_dst.is_file() and pth_dst.stat().st_size == pth_src.stat().st_size and obt_sha(pth_dst) == obt_sha(pth_src)
        if es_igual and fisico:
            ajusta_publico(pth_dst)
            return
        if not es_igual and not owned:
            raise ValueError(f'Refusing to overwrite an unrelated payload: {pth_dst}')
    elif pth_dst.is_symlink() and not owned and pth_dst.resolve() != pth_src.resolve():
        raise ValueError(f'Refusing to replace an unrelated symlink: {pth_dst}')
    tmp = pth_dst.with_name('.fast-boot-link-' + pth_dst.name)
    tmp.unlink(missing_ok=True)
    try:
        if fisico:
            shutil.copy2(pth_src, tmp)
            ajusta_publico(tmp)
        else:
            tmp.symlink_to(pth_src)
            ajusta_publico(tmp, enlace=True)
        os.replace(tmp, pth_dst)
    finally:
        tmp.unlink(missing_ok=True)



def ext_archive(pth_src, pth_dst):
    if pth_src.name.endswith('.zip'):
        with zipfile.ZipFile(pth_src) as arc:
            for ent in arc.infolist():
                if not (pth_dst / ent.filename).resolve().is_relative_to(pth_dst.resolve()):
                    raise ValueError('Archive contains an unsafe path')
            arc.extractall(pth_dst)
    elif pth_src.name.endswith('.tar.gz'):
        with tarfile.open(pth_src) as arc:
            # The data filter rejects escapes, device nodes and unsafe link targets.
            arc.extractall(pth_dst, filter='data')
    else:
        subprocess.run(['bsdtar', '-xf', str(pth_src), '-C', str(pth_dst)], check=True, capture_output=True)
    # Memtest distributions often wrap their actual native binaries in one ISO.
    for iso in list(pth_dst.rglob('*.iso')):
        des = iso.with_suffix('')
        des.mkdir(exist_ok=True)
        subprocess.run(['bsdtar', '-xf', str(iso), '-C', str(des)], check=True, capture_output=True)


def pub_rec(rec, cfg, pth_src):
    if rec['size'] is None or rec['status'] == 'checksum-failed':
        return
    arc_pub = cfg.output / rec['filename']
    arc_pub_est = obt_estado(cfg, 'file-state', rec)
    pub_ant = lee_estado(cfg, 'file-state', rec)
    owned = pub_ant.get('path') == str(arc_pub) and (arc_pub.is_symlink() or
            (arc_pub.is_file() and pub_ant.get('sha256') == obt_sha(arc_pub)))
    pub_arc(pth_src, arc_pub, fisico=cfg.mode == 'extract', owned=owned)
    rec['published'] = True
    esc_atomic(arc_pub_est, json.dumps({'path': str(arc_pub), 'sha256': rec['sha256']}))
    if not rec['filename'].endswith(('.iso', '.zip', '.tar.gz')):
        return
    pth_pub = cfg.output / rec['tree']
    pth_tree = (cfg.ram_dir if cfg.mode == 'ram' else cfg.output) / rec['tree']
    arc_est = obt_estado(cfg, 'tree-state', rec)
    est_ant = lee_estado(cfg, 'tree-state', rec)
    est_nue = {'sha256': rec['sha256'], 'mode': cfg.mode, 'source': str(pth_src),
               'tree': str(pth_pub), 'prepared': str(pth_tree)}
    ctx = getattr(cfg, 'mount_context', None)
    if ctx:
        est_nue['mount_context'] = ctx
    is_mount = os.path.ismount(pth_tree)
    if (est_ant == est_nue and pth_tree.is_dir() and pth_pub.is_dir()
            and (cfg.mode != 'ram' or pth_pub.is_symlink() and pth_pub.resolve() == pth_tree.resolve())
            and (is_mount or cfg.mode == 'extract' or not rec['filename'].endswith('.iso')) and any(pth_tree.iterdir())):
        ajusta_tree(pth_tree)
        if pth_pub.is_symlink():
            ajusta_publico(pth_pub, enlace=True)
        return
    managed = est_ant.get('tree') == str(pth_pub)
    pth_ant = Path(est_ant.get('prepared', str(pth_pub)))
    if managed and pth_ant != pth_tree and os.path.ismount(pth_ant):
        subprocess.run(['umount', str(pth_ant)], check=True, capture_output=True)
    if pth_pub.is_symlink():
        if not managed:
            raise ValueError(f'Existing unmanaged tree link: {pth_pub}')
        pth_pub.unlink()
    elif pth_pub.exists() and pth_pub != pth_tree:
        if not managed:
            raise ValueError(f'Existing unmanaged tree: {pth_pub}')
        if os.path.ismount(pth_pub):
            subprocess.run(['umount', str(pth_pub)], check=True, capture_output=True)
        shutil.rmtree(pth_pub)
    if is_mount:
        if not managed:
            raise ValueError(f'Refusing to unmount an unmanaged tree: {pth_tree}')
        subprocess.run(['umount', str(pth_tree)], check=True, capture_output=True)
    if pth_tree.exists():
        if pth_tree.is_symlink() or (any(pth_tree.iterdir()) and not managed):
            raise ValueError(f'Existing unmanaged tree: {pth_tree}; inspect it and run generate.sh if appropriate')
    if rec['filename'].endswith('.iso') and cfg.mode in ('mount', 'ram'):
        crea_dir_publico(pth_tree)
        opts = 'loop,ro,nosuid,nodev,noexec' + (',context=' + ctx if ctx else '')
        subprocess.run(['mount', '-o', opts, str(pth_src), str(pth_tree)], check=True, capture_output=True)
    else:
        tmp = Path(tempfile.mkdtemp(prefix='.fast-boot-tree-', dir=pth_tree.parent))
        try:
            ext_archive(pth_src, tmp)
            if not any(tmp.iterdir()):
                raise ValueError('Payload extraction produced an empty tree')
            ajusta_tree(tmp)
            if pth_tree.exists():
                shutil.rmtree(pth_tree)
            os.replace(tmp, pth_tree)
        finally:
            if tmp.exists():
                shutil.rmtree(tmp)
    if cfg.mode == 'ram':
        pth_pub.symlink_to(pth_tree, target_is_directory=True)
        ajusta_publico(pth_pub, enlace=True)
    esc_atomic(arc_est, json.dumps(est_nue))


def tam_expandido(pth):
    """Budget allocated pages, including nested ISO extraction in ZIP media."""
    pagina = os.sysconf('SC_PAGE_SIZE')
    bloque = lambda n: ((n + pagina - 1) // pagina) * pagina
    if pth.name.endswith('.tar.gz'):
        with tarfile.open(pth, 'r:gz') as arc:
            return sum(bloque(ent.size) for ent in arc if ent.isfile())
    if pth.name.endswith('.zip'):
        with zipfile.ZipFile(pth) as arc:
            return sum(bloque(ent.file_size) * (2 if ent.filename.lower().endswith('.iso') else 1)
                       for ent in arc.infolist() if not ent.is_dir())
    return 0  # ISO loop mounts do not duplicate the file contents.


def prep_ram(rec, cfg):
    if rec['size'] is None or rec['status'] == 'checksum-failed':
        return
    crea_dir_publico(cfg.ram_dir)
    typ = subprocess.run(['stat', '-f', '-c', '%T', str(cfg.ram_dir)], check=True, capture_output=True, text=True).stdout.strip()
    if typ != 'tmpfs':
        raise ValueError('--ram-dir must be on an existing tmpfs filesystem')
    pth_src = cfg.ram_dir / rec['filename']
    reutiliza = arc_valido(pth_src, rec['filename']) and obt_sha(pth_src) == rec['sha256']
    copia = 0 if reutiliza else rec['size']
    expandido = 0
    if rec['filename'].endswith(('.tar.gz', '.zip')):
        est = lee_estado(cfg, 'tree-state', rec)
        pth_tree = cfg.ram_dir / rec['tree']
        ctx = getattr(cfg, 'mount_context', None)
        listo = (reutiliza and est.get('sha256') == rec['sha256'] and est.get('mode') == 'ram'
                 and est.get('prepared') == str(pth_tree) and est.get('source') == str(pth_src)
                 and est.get('mount_context') == ctx and pth_tree.is_dir() and not pth_tree.is_symlink()
                 and (cfg.output / rec['tree']).is_dir() and any(pth_tree.iterdir()))
        if not listo:
            expandido = tam_expandido(cfg.cache / rec['filename'])
    if copia or expandido:
        limite = int(getattr(cfg, 'ram_budget_gib', 22) * 1024 ** 3)
        margen = int(limite * getattr(cfg, 'ram_reserve_percent', 10) / 100)
        usado = 0
        for raiz, dirs, noms in os.walk(cfg.ram_dir, followlinks=False):
            dirs[:] = [nom for nom in dirs if not (Path(raiz) / nom).is_symlink()
                       and not os.path.ismount(Path(raiz) / nom)]
            usado += sum((Path(raiz) / nom).lstat().st_blocks * 512 for nom in noms
                         if not (Path(raiz) / nom).is_symlink())
        if usado + copia + expandido > limite - margen:
            # Disk fallback is explicit and still publishes the verified cached image.
            msg_descarga(cfg, rec, 'DISK', f'RAM budget: used {usado:,}, need {copia + expandido:,}, '
                         f'limit {limite:,}, reserved {margen:,}; deploying to disk')
            cfg_disk = copy.copy(cfg)
            cfg_disk.mode = 'extract'
            prep_disk(rec, cfg_disk)
            rec['deployment'] = 'disk-fallback'
            return
        reserva = 16 * 1024 * 1024
        disponible = shutil.disk_usage(cfg.ram_dir).free
        necesita = copia + expandido + reserva
        msg_descarga(cfg, rec, 'SPACE', f'Additional {necesita / 1024**2:.1f} MiB '
                     f'(copy {copia / 1024**2:.1f}, extraction {expandido / 1024**2:.1f}, reserve 16); '
                     f'free {disponible / 1024**2:.1f} MiB')
        if disponible < necesita:
            raise ValueError(f'Not enough tmpfs space for {rec["filename"]}: '
                             f'need {necesita / 1024**2:.1f} MiB including extraction; '
                             f'free {disponible / 1024**2:.1f} MiB')
    if not reutiliza:
        tmp = pth_src.with_name('.fast-boot-' + pth_src.name)
        msg_descarga(cfg, rec, 'RAM', f'Copying {rec["size"]:,} bytes into {cfg.ram_dir}')
        try:
            shutil.copy2(cfg.cache / rec['filename'], tmp)
            ajusta_publico(tmp)
            os.replace(tmp, pth_src)
        finally:
            tmp.unlink(missing_ok=True)
    else:
        msg_descarga(cfg, rec, 'RAM', 'Reusing the matching tmpfs copy')
    ajusta_publico(pth_src)
    pub_rec(rec, cfg, pth_src)
    rec['deployment'] = 'ram'


def prep_disk(rec, cfg):
    if cfg.mode == 'mount':
        # Public file links need traversal to the cache; extracted copies do not.
        crea_dir_publico(cfg.cache)
        ajusta_publico(cfg.cache / rec['filename'])
    pub_rec(rec, cfg, cfg.cache / rec['filename'])



def ver_requisitos(rec_all, cfg):
    req = []
    if cfg.mode in ('mount', 'ram'):
        req += ['mount', 'umount', 'stat']
        if os.geteuid() != 0:
            raise ValueError('Mount and RAM deployment require root')
    if any((cfg.mode == 'extract' and rec['filename'].endswith('.iso')) or
           rec['family'] == 'memtest' and rec['filename'].endswith(('.zip', '.tar.gz')) for rec in rec_all):
        req += ['bsdtar']
    for cmd in req:
        if not shutil.which(cmd):
            raise ValueError(f'Missing dependency: {cmd}; see DEPLOYMENT.md')


def valida_cache(rec, cfg, sumas):
    arc = cfg.cache / rec['filename']
    if not arc_valido(arc, rec['filename']):
        raise ValueError('Invalid cached payload; run download.sh again')
    msg_descarga(cfg, rec, 'VERIFY', 'Reading the cache and calculating SHA-256')
    rec.update(size=arc.stat().st_size, sha256=obt_sha(arc), status='cached')
    if rec['filename'] in sumas and rec['sha256'] != sumas[rec['filename']]:
        raise ValueError(f'Cached payload differs from trusted checksum: expected {sumas[rec["filename"]]}, obtained {rec["sha256"]}')


def plan_ftp(cfg):
    """Merge public relative paths and cached payloads; materialize only approved symlinks."""
    if not cfg.output.is_dir():
        raise ValueError('Public html directory is missing; deploy and generate locally first')
    rec_all = lee_cache(cfg)
    sumas = obt_sumas(cfg)
    plan, digests = {}, {}
    for rec in rec_all:
        valida_cache(rec, cfg, sumas)
        digests[(cfg.cache / rec['filename']).resolve()] = rec['sha256']
    roots = [cfg.output.resolve(), cfg.cache.resolve(), cfg.ram_dir.resolve()]
    def add(arc, rel):
        if any(ord(c) < 32 or ord(c) == 127 for c in rel):
            raise ValueError('FTP path contains control characters')
        real = arc.resolve(strict=True)
        if not any(real.is_relative_to(root) for root in roots):
            raise ValueError(f'Public link escapes html/cache/RAM roots: {rel}')
        sha = digests.get(real)
        if sha is None:
            sha = digests[real] = obt_sha(real)
        item = {'path': real, 'relative': rel, 'sha256': sha, 'size': real.stat().st_size}
        previous = plan.get(rel)
        if previous and (previous['sha256'], previous['size']) != (sha, item['size']):
            raise ValueError(f'html/cache collision has different bytes: {rel}')
        plan[rel] = item
    def walk(pth, rel='', ancestors=frozenset()):
        real = pth.resolve(strict=True)
        if not any(real.is_relative_to(root) for root in roots):
            raise ValueError(f'Public directory link escapes html/cache/RAM roots: {rel}')
        if real in ancestors:
            raise ValueError(f'Directory link cycle in public tree: {rel}')
        for arc in sorted(pth.iterdir()):
            if arc.name.startswith('.') and arc.name not in ('.treeinfo', '.discinfo') and not (rel == '' and arc.name == '.htaccess'):
                continue
            if arc.name.endswith(('.part', '.tmp')):
                continue
            sub = rel + '/' + arc.name if rel else arc.name
            if arc.is_dir():
                walk(arc, sub, ancestors | {real})
            elif arc.is_file():
                add(arc, sub)
            elif arc.is_symlink():
                raise ValueError(f'Broken public link; RAM may need redeployment: {sub}')
            else:
                raise ValueError(f'Non-regular public entry: {sub}')
    walk(cfg.output)
    for rec in rec_all:
        add(cfg.cache / rec['filename'], rec['filename'])
    for rel in plan:
        parts = rel.split('/')
        if any('/'.join(parts[:idx]) in plan for idx in range(1, len(parts))):
            raise ValueError(f'FTP file/directory collision: {rel}')
    # Payloads and asset files go first; catalog entry points are published last.
    entrypoints = {'catalog.json', 'index.html', 'index.php', 'index-aux.php', 'index-pxe.html',
                   'cli.html', 'cli-all.html', 'menu.ipxe', 'sitemaps.xml', 'sitemaps-aux.xml', 'sitemaps-pxe.xml'}
    return sorted(plan.values(), key=lambda item: (item['relative'] in entrypoints, item['relative']))


def ftp_size(conn, name):
    try:
        return conn.size(name)
    except ftplib.error_perm as exc:
        if str(exc).startswith('550'):
            return None
        raise


def ftp_perm(conn, nom, modo, cfg):
    """FTP ownership belongs to the hosting account; SITE CHMOD is optional there."""
    if getattr(cfg, '_ftp_chmod_unavailable', False):
        return
    try:
        conn.sendcmd('SITE CHMOD ' + modo + ' ' + nom)
    except ftplib.error_perm as exc:
        if str(exc).startswith(('500', '502', '504')):
            cfg._ftp_chmod_unavailable = True
            print('FTP: SITE CHMOD unavailable; remote modes depend on the hosting account umask.', file=sys.stderr)
        else:
            raise


def sube_ftp(conn, item, cfg, num, total):
    rel, arc = item['relative'], item['path']
    rec = {'filename': rel, '_num': num, '_total': total}
    conn.cwd(cfg.ftp_root)
    parts = rel.split('/')
    for folder in parts[:-1]:
        try:
            conn.cwd(folder)
        except ftplib.error_perm:
            conn.mkd(folder)
            conn.cwd(folder)
        ftp_perm(conn, '.', '755', cfg)
    conn.voidcmd('TYPE I')
    # A content-addressed temporary name permits restart without resuming another version.
    tmp = '.aux-upload-' + item['sha256'] + '.part'
    offset = ftp_size(conn, tmp) or 0
    if offset > item['size']:
        raise ValueError(f'Remote partial is larger than the local file: {rel}')
    sent, last = offset, time.monotonic()
    tms_ini = last
    msg_descarga(cfg, rec, 'FTP', f'{offset:,}/{item["size"]:,} bytes; ' + ('resume' if offset else 'upload'))
    def progress(block):
        nonlocal sent, last
        sent += len(block)
        now = time.monotonic()
        if now - last >= 2 or sent == item['size']:
            rate = (sent - offset) / max(now - tms_ini, .001)
            eta = (item['size'] - sent) / rate if rate else 0
            pct = 100 * sent / max(item['size'], 1)
            msg_descarga(cfg, rec, 'FTP', f'{pct:5.1f}% | {sent:,}/{item["size"]:,} bytes | {rate / 1024**2:.2f} MiB/s | ETA {eta:.0f}s')
            last = now
    if offset < item['size'] or item['size'] == 0:
        with arc.open('rb') as src:
            src.seek(offset)
            conn.storbinary('STOR ' + tmp, src, blocksize=256 * 1024,
                            callback=progress, rest=offset if offset else None)
    if ftp_size(conn, tmp) != item['size']:
        raise ValueError(f'Remote size verification failed: {rel}')
    if arc.stat().st_size != item['size'] or obt_sha(arc) != item['sha256']:
        raise ValueError(f'Local file changed during upload: {rel}')
    # Keep the previous public file until a complete replacement can be renamed into place.
    conn.rename(tmp, parts[-1])
    ftp_perm(conn, parts[-1], '644', cfg)
    msg_descarga(cfg, rec, 'DONE', 'Uploaded, size checked and renamed')


def despliega_ftp(cfg):
    if cfg.dry_run:
        plan = plan_ftp(cfg)
        print(f'deploy-ftp {VERSION} | {len(plan)} files | {sum(item["size"] for item in plan):,} bytes')
        print(f'FTP destination: {cfg.ftp_host or "<host>"}:{cfg.ftp_port}{cfg.ftp_root}')
        for item in plan:
            print(f'{item["path"]} -> {cfg.ftp_root.rstrip("/")}/{item["relative"]} [{item["size"]:,} bytes]')
        return 0
    if not cfg.ftp_host or not cfg.ftp_user:
        raise ValueError('FTP requires --ftp-host and --ftp-user (or AUX_FTP_HOST / AUX_FTP_USER)')
    with bloq_cache(cfg):
        plan = plan_ftp(cfg)
        password = os.environ.get('AUX_FTP_PASSWORD')
        if password is None:
            try:
                password = getpass.getpass('FTP password: ')
            except EOFError:
                raise ValueError('FTP password requires a terminal prompt or AUX_FTP_PASSWORD') from None
        if any(ord(c) < 32 or ord(c) == 127 for c in password):
            raise ValueError('FTP password must not contain control characters')
        conn = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=60) if cfg.ftp_tls else ftplib.FTP(timeout=60)
        tms_ini = time.monotonic()
        try:
            conn.connect(cfg.ftp_host, cfg.ftp_port)
            conn.login(cfg.ftp_user, password)
            if cfg.ftp_tls:
                conn.prot_p()
            conn.set_pasv(True)
            # The account's FTP root must exist; it may be / or an OVH website directory.
            conn.cwd(cfg.ftp_root)
            for num, item in enumerate(plan, 1):
                cfg._ftp_current = item['relative']
                sube_ftp(conn, item, cfg, num, len(plan))
            print(f'deploy-ftp: {len(plan)} OK | {sum(item["size"] for item in plan) / 1024**2:.1f} MiB | {time.monotonic() - tms_ini:.1f}s')
        except ftplib.all_errors + (ValueError,) as exc:
            # FTP replies must never expose the credential supplied through the prompt/environment.
            msg = str(exc).replace(password, '[redacted]') if password else str(exc)
            raise ValueError('FTP upload failed at ' + getattr(cfg, '_ftp_current', 'connect/login') +
                             '; rerun to resume partial files: ' + msg) from None
        finally:
            conn.close()
    return fin_tarea(cfg, [], tms_ini)


def main():
    cfg = obt_args('deploy', pth_app)
    if not cfg.dry_run:
        inicia_informe(cfg)
    if cfg.dest == 'ftp':
        return despliega_ftp(cfg)
    rec_all = lee_cache(cfg)
    if cfg.dry_run:
        muestra_plan(cfg, rec_all)
        return 0
    ver_requisitos(rec_all, cfg)
    sumas = obt_sumas(cfg)
    cfg.cache.mkdir(parents=True, exist_ok=True)
    crea_dir_publico(cfg.output)
    tms_ini = time.monotonic()
    with bloq_cache(cfg):
        for num, rec in enumerate(rec_all, 1):
            rec.update(_num=num, _total=len(rec_all))
            try:
                valida_cache(rec, cfg, sumas)
                msg_descarga(cfg, rec, 'DEPLOY', f'{cfg.mode} -> {cfg.output}')
                if cfg.dest == 'ram':
                    prep_ram(rec, cfg)
                else:
                    prep_disk(rec, cfg)
                rec['status'] = 'deployed'
                msg_descarga(cfg, rec, 'DONE', 'Payload and image contents published')
            except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as exc:
                rec.update(status='prepare-failed', error=describe_error(exc), error_stage=cfg.mode)
                msg_descarga(cfg, rec, 'ERROR', rec['error'], forzar=True)
        return fin_tarea(cfg, rec_all, tms_ini)


if __name__ == '__main__':
    raise SystemExit(ejecuta_main(main))
AUXPY
