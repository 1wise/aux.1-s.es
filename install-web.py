#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Install AUX/PXE, TEC and the Excalibur gateway; show the plan unless --apply."""
import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import grp
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import tempfile
import zipfile

VERSION = '6.4.0-dev.1'
DIR_APP = Path(__file__).resolve().parent


def orden(*args, **kwargs):
    return subprocess.run(list(args), check=True, **kwargs)


def extrae(arc, dest):
    suma = arc.with_suffix('.zip.sha256').read_text().split()[0]
    if len(suma) != 64 or hashlib.sha256(arc.read_bytes()).hexdigest() != suma:
        raise ValueError('SHA-256 incorrecto: ' + arc.name)
    with zipfile.ZipFile(arc) as zipf:
        for ent in zipf.infolist():
            pth = dest / ent.filename
            if not pth.resolve().is_relative_to(dest.resolve()) or ent.is_dir():
                if ent.is_dir() and pth.resolve().is_relative_to(dest.resolve()):
                    continue
                raise ValueError('Ruta de paquete no permitida: ' + ent.filename)
            if (ent.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('No se admiten enlaces en paquetes de instalación.')
        zipf.extractall(dest)


@contextlib.contextmanager
def fuentes(pth):
    if (pth / 'tec/web/totp.php').is_file() and (pth / 'cli/server.py').is_file():
        yield pth
        return
    with tempfile.TemporaryDirectory(prefix='aux-62-install-') as tmp:
        base = Path(tmp)
        extrae(pth / ('aux-pxe-' + VERSION + '.zip'), base)
        extrae(pth / ('tec-platform-' + VERSION + '.zip'), base / 'tec')
        extrae(pth / ('aux-cli-' + VERSION + '.zip'), base / 'cli')
        yield base


def configura(dat, root):
    cfg = copy.deepcopy(dat)
    cfg.setdefault('_meta', {})['Version'] = VERSION
    cfg['cli']['enabled'] = True
    cfg['cli']['primary'] = 'excalibur'
    cfg['tec']['web_dir'] = str(root / 'web')
    cfg['tec']['config_file'] = str(root / 'fast-boot.json')
    cfg['output'] = str(root / 'html')
    cfg['cache'] = str(root / 'isos')
    for nom in ('data_dir', 'session_dir'):
        pth = Path(cfg['tec'][nom])
        if not pth.is_absolute() or any(pth.resolve().is_relative_to((root / pub).resolve()) for pub in ('html','web')):
            raise ValueError('El directorio privado ' + nom + ' debe quedar fuera de las raíces públicas.')
    # TEC and CLI use an identical signing secret, provisioned separately below.
    cfg['cli']['nodes']['excalibur']['secret_file'] = str(Path(cfg['tec']['data_dir']) / 'cli-excalibur.secret')
    return cfg


def usuario(nom, home):
    try:
        pwd.getpwnam(nom)
    except KeyError:
        orden('useradd', '--system', '--user-group', '--no-create-home',
              '--home-dir', str(home), '--shell', '/usr/sbin/nologin', nom)


def directorio(pth, modo=0o755, usr='root'):
    pth.mkdir(parents=True, exist_ok=True)
    ent = pwd.getpwnam(usr)
    os.chmod(pth, modo)
    os.chown(pth, ent.pw_uid, ent.pw_gid)


def escribe(pth, byt, modo=0o644, usr='root', grupo=None):
    # Atomic replacement prevents PHP or the gateway reading half a configuration.
    ent = pwd.getpwnam(usr)
    fd, nom = tempfile.mkstemp(prefix='.' + pth.name, dir=pth.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(byt)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(nom, modo)
        os.chown(nom, ent.pw_uid, grp.getgrnam(grupo).gr_gid if grupo else ent.pw_gid)
        os.replace(nom, pth)
    finally:
        Path(nom).unlink(missing_ok=True)


def secreto_cli(origen, destino):
    byt = origen.read_bytes() if origen.exists() else (secrets.token_hex(32) + '\n').encode()
    if len(byt.strip()) < 32:
        raise ValueError('El secreto CLI existente es inválido; no se ha reemplazado.')
    escribe(origen, byt, 0o600, 'aux-cli')
    escribe(destino, byt, 0o600, 'tec')


def sincroniza(src, dst, excluir=()):
    directorio(dst)
    for arc in sorted(src.rglob('*')):
        rel = arc.relative_to(src)
        if '__pycache__' in rel.parts or arc.is_symlink() or not arc.is_file() or str(rel) in excluir:
            continue
        directorio((dst / rel).parent)
        escribe(dst / rel, arc.read_bytes(), 0o755 if arc.suffix == '.sh' else 0o644)


def instala(src, root, nginx):
    if os.geteuid() != 0:
        raise ValueError('Usar sudo para --apply; el plan no requiere root.')
    for nom in ('php', 'php-fpm', 'nginx', 'openssl', 'runuser', 'systemctl', 'semanage', 'restorecon'):
        if not shutil.which(nom):
            raise ValueError('Dependencia ausente: ' + nom + '. Consultar INSTALL-6.3.md.')
    cfg_path = root / 'fast-boot.json'
    cfg = configura(json.loads((cfg_path if cfg_path.exists() else src / 'fast-boot.json').read_text()), root)
    if Path('/etc/aux-cli/secret').exists() and len(Path('/etc/aux-cli/secret').read_bytes().strip()) < 32:
        raise ValueError('El secreto CLI existente es inválido; no se modificó la instalación.')
    # Check the existing certificate before replacing any live vhost.
    if nginx:
        for host in ('aux.1-s.es', 'aux.1-s.eu', 'pxe.1-s.es', 'pxe.1-s.eu',
                     'tec.1-s.es', 'tec.1-s.eu', 'cli.1-s.es'):
            orden('openssl', 'x509', '-in', cfg['tls']['certificate'], '-noout', '-checkhost', host)
    usuario('tec', cfg['tec']['data_dir'])
    usuario('aux-cli', '/opt/aux-cli')
    directorio(root)
    bak = Path('/var/backups/aux-assist') / dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directorio(bak, 0o700)
    for pth, nom in ((root / 'web', 'web'), (cfg_path, 'fast-boot.json'),
                     (Path('/etc/php-fpm.d/tec.conf'), 'tec.conf'),
                     (Path('/etc/nginx/conf.d/aux-pxe-tec.conf'), 'aux-pxe-tec.conf'),
                     (Path('/etc/nginx/conf.d/aux-cli.conf'), 'aux-cli.conf')):
        if pth.is_dir():
            shutil.copytree(pth, bak / nom)
        elif pth.is_file():
            shutil.copy2(pth, bak / nom)
    # The source root is separate from both public roots; accounts never enter it.
    for nom in ('src', 'assets', 'fonts', 'nginx', 'ovh', 'usb', 'iso', 'iso-assist', 'debian', 'cli', 'tec'):
        if (src / nom).is_dir():
            sincroniza(src / nom, root / nom)
    for nom in ('download.sh', 'deploy.sh', 'generate.sh', 'build.py', 'url.txt', 'light-url.txt',
                'heavy-url.txt', 'alpine-sources.json', 'alpine-SHA256SUMS', 'CONFIGURATION.md',
                'RELEASE-6.md', 'CHECKLIST-6.json', 'RELEASE-6.1.md', 'CHECKLIST-6.1.json',
                'TEST-6.1.md', 'RELEASE-6.3.md', 'CHECKLIST-6.3.json', 'TEST-6.3.md', 'INSTALL-6.3.md',
                'RELEASE-6.4.md', 'CHECKLIST-6.4.json', 'TEST-6.4.md', 'INSTALL-6.4.md'):
        if (src / nom).is_file():
            escribe(root / nom, (src / nom).read_bytes(), 0o755 if nom.endswith('.sh') else 0o644)
    sincroniza(src / 'tec/web', root / 'web')
    escribe(root / 'manage.php', (src / 'tec/manage.php').read_bytes())
    for nom in ('html', 'isos'):
        directorio(root / nom)
    data = Path(cfg['tec']['data_dir'])
    directorio(data, 0o700, 'tec')
    directorio(Path(cfg['tec']['session_dir']), 0o700, 'tec')
    directorio(Path('/etc/aux-cli'), 0o750, 'aux-cli')
    directorio(Path('/opt/aux-cli'))
    arc_sec = Path('/etc/aux-cli/secret')
    secreto_cli(arc_sec, Path(cfg['cli']['nodes']['excalibur']['secret_file']))
    byt_cfg = (json.dumps(cfg, ensure_ascii=False, indent=2) + '\n').encode()
    escribe(cfg_path, byt_cfg, 0o640, grupo='tec')
    escribe(Path('/etc/aux-cli/fast-boot.json'), byt_cfg, 0o600, 'aux-cli')
    for nom in ('server.py', 'history.py', 'requirements.txt'):
        escribe(Path('/opt/aux-cli') / nom, (src / 'cli' / nom).read_bytes())
    orden('python3', '-m', 'venv', '/opt/aux-cli/venv')
    orden('/opt/aux-cli/venv/bin/pip', 'install', '-r', '/opt/aux-cli/requirements.txt')
    escribe(Path('/etc/systemd/system/aux-cli.service'), (src / 'cli/aux-cli.service').read_bytes())
    pool = (src / 'tec/php-fpm.conf.example').read_text().replace('/var/www/aux.1-s.es', str(root))
    escribe(Path('/etc/php-fpm.d/tec.conf'), pool.encode())
    directorio(Path('/var/log/php-fpm'))
    if not Path('/var/log/php-fpm/tec-error.log').exists():
        escribe(Path('/var/log/php-fpm/tec-error.log'), b'', 0o640, 'tec')
    # Keep SELinux enforcing while permitting the web services' required transports.
    if shutil.which('selinuxenabled') and subprocess.run(['selinuxenabled']).returncode == 0:
        for tipo, patron in (('httpd_sys_rw_content_t', str(data) + '(/.*)?'),
                             ('httpd_var_run_t', cfg['tec']['session_dir'] + '(/.*)?')):
            res = subprocess.run(['semanage', 'fcontext', '-a', '-t', tipo, patron])
            if res.returncode:
                orden('semanage', 'fcontext', '-m', '-t', tipo, patron)
        orden('setsebool', '-P', 'httpd_can_network_connect', 'on')
        orden('setsebool', '-P', 'httpd_can_sendmail', 'on')
    orden('restorecon', '-RF', str(root), str(data), cfg['tec']['session_dir'], '/etc/aux-cli', '/var/log/php-fpm')
    orden('runuser', '-u', 'tec', '--', 'env', 'AUX_ASSIST_CONFIG=' + str(cfg_path),
          'AUX_ASSIST_DATA_DIR=' + str(data), 'php', str(root / 'manage.php'), 'init')
    orden('bash', str(root / 'generate.sh'), '--config', str(cfg_path))
    if nginx:
        for rel, nom in (('nginx/aux-pxe-tec.conf.example', 'aux-pxe-tec.conf'),
                         ('cli/nginx.conf.example', 'aux-cli.conf')):
            txt = (src / rel).read_text().replace('/var/www/aux.1-s.es', str(root))
            txt = txt.replace('/etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem', cfg['tls']['certificate'])
            txt = txt.replace('/etc/letsencrypt/live/ntp1.1-s.eu/privkey.pem', cfg['tls']['key'])
            escribe(Path('/etc/nginx/conf.d') / nom, txt.encode())
    orden('php-fpm', '-t')
    orden('nginx', '-t')
    orden('systemctl', 'daemon-reload')
    orden('systemctl', 'enable', '--now', 'aux-cli.service', 'php-fpm.service', 'nginx.service')
    orden('systemctl', 'restart', 'aux-cli.service', 'php-fpm.service')
    if nginx:
        orden('systemctl', 'reload', 'nginx.service')
    print('Instalación completada. Copia previa:', bak)
    print('Registrar/confirmar cuenta TEC, aprobar perfil y abrir totp.php para configurar el segundo factor.')


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--source', type=Path, default=DIR_APP)
    par.add_argument('--root', type=Path, default=Path('/var/www/aux.1-s.es'))
    par.add_argument('--apply', action='store_true')
    par.add_argument('--nginx', action='store_true', help='Install both reviewed vhosts; reject certificates lacking required names')
    args = par.parse_args()
    try:
        with fuentes(args.source.resolve()) as src:
            if not args.apply:
                print('AUX ' + VERSION + ' · plan; no se modifica el sistema.')
                print('Instalar AUX/PXE y TEC en:', args.root)
                print('Instalar aux-cli en /opt/aux-cli, puerto interno 127.0.0.1:8096.')
                print('Conservar cuentas y secreto existente; sincronizar su copia privada con TEC; habilitar CLI.')
                print('Configurar pool PHP y etiquetas/booleanos SELinux de red y correo; generar índices sin descargar ISO.')
                print('Instalar vhosts Nginx:', args.nginx, '· validar configuración y reiniciar aux-cli/PHP.')
                print('Aplicar con --apply; para instalar los vhosts revisados añadir --nginx. Leer INSTALL-6.4.md.')
            else:
                instala(src, args.root.resolve(), args.nginx)
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print('Instalación detenida:', exc)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
