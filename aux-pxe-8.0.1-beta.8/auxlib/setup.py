# Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
# Author & Credits: https://www.alawise.es/1-s
"""One explicit installer for an existing OS, a new root, ISO media or the portal."""
import argparse
import contextlib
import io
import datetime
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import uuid
import sys

from . import VERSION
from .common import CABECERA, DIR_APP, atomico, dentro, ejecuta, guarda_json, suma
from .profiles import ROLES, DEFAULT_ROLES, genera, seleccion, verifica


def copia(ori, dst, modo=None):
    if Path(ori).resolve() == Path(dst).resolve():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ori, dst)
    if modo is not None:
        dst.chmod(modo)


def instala_archivos(raiz, roles=None, dis=None):
    roles = list(DEFAULT_ROLES) if roles is None else list(roles)
    if any(nom not in ROLES for nom in roles):
        raise ValueError('Componente AUX desconocido.')
    asist = 'aux-assist' in roles
    raiz = Path(raiz).resolve()
    dst = dentro(raiz, 'usr/local/lib/aux')
    if dst != DIR_APP and DIR_APP.is_relative_to(dst):
        raise ValueError('La fuente no puede estar dentro del destino de instalación.')
    dst.mkdir(parents=True, exist_ok=True)
    for nom in ('auxlib', 'ui', 'profiles', 'config', 'assist', 'tec', 'cli', 'src', 'assets', 'fonts',
                'nginx', 'ovh', 'usb', 'iso', 'iso-assist', 'debian', 'docs'):
        for ori in (DIR_APP / nom).rglob('*'):
            if ori.is_file() and not ori.is_symlink() and '__pycache__' not in ori.parts:
                copia(ori, dentro(raiz, 'usr/local/lib/aux/' + str(ori.relative_to(DIR_APP))))
    for nom in ('install-web.py', 'fast-boot.json', 'download.sh', 'deploy.sh', 'generate.sh',
                'build.py', 'catalog.json', 'alpine-sources.json',
                'alpine-SHA256SUMS', 'SOURCE.json', 'SHA256SUMS'):
        if (DIR_APP / nom).is_file():
            copia(DIR_APP / nom, dentro(raiz, 'usr/local/lib/aux/' + nom))
    for nom in ('aux', 'aux-setup', 'aux-profile', 'aux-catalog', 'aux-enter', 'aux-assist', 'aux-tools', 'aux-images', 'aux-config', 'aux-release', 'aux-observe', 'aux-checkstatus'):
        if nom == 'aux-assist' and not asist:
            continue
        ori = DIR_APP / nom
        copia(ori, dentro(raiz, 'usr/local/lib/aux/' + nom), 0o755)
        pth = raiz / 'usr/local/bin' / nom
        if pth.is_symlink() and os.readlink(pth) == '/usr/local/lib/aux/' + nom:
            continue
        pth = dentro(raiz, 'usr/local/bin/' + nom)
        if pth.exists() or pth.is_symlink():
            raise ValueError('Se conserva el ejecutable existente: ' + str(pth))
        pth.parent.mkdir(parents=True, exist_ok=True)
        pth.symlink_to('/usr/local/lib/aux/' + nom)
    for nom in ('work', 'storage', 'var/lib/aux-assist'):
        pth = dentro(raiz, nom)
        pth.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Store the marker outside the public web tree and never infer Live semantics.
    atomico(dentro(raiz, 'etc/aux-installed'), VERSION + '\n')
    if 'kernel-modeler' in roles:
        from .kernel_modeler import instala
        instala(raiz,dis or 'debian')
    if asist:
        instala_asistencia(raiz,dis)
    for nom,rot,cmd,terminal in [
        ('aux','AUX - Consola unificada','/usr/local/bin/aux','true'),
        ('aux-workspace','AUX - Area de trabajo','/usr/local/bin/aux-tools --gui','false'),
        ('aux-setup','AUX - Instalar y personalizar','pkexec /usr/local/bin/aux-setup --interactive','true'),
        ('aux-systems','AUX - Sistemas y chroot','pkexec /usr/local/bin/aux-enter --interactive','true')]:
        txt=CABECERA+'[Desktop Entry]\nType=Application\nName='+rot+'\nExec='+cmd+'\nIcon=utilities-terminal\nTerminal='+terminal+'\nCategories=System;\n'
        atomico(dentro(raiz,'usr/share/applications/'+nom+'.desktop'),txt)
    from .webapps import publica_paginas
    pth_web = dentro(raiz,'usr/local/share/aux')
    publica_paginas(pth_web)
    for nom in ('observability.html','help.html','operations.html'):
        cuerpo = (DIR_APP/'src'/nom).read_text()
        atomico(pth_web/nom, '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="assets/workspace.css"><title>Guía AUX</title><body><nav><a href="workspace.html">./aux</a></nav><main>'+cuerpo+'</main></body></html>')
    for ori in (DIR_APP/'docs').glob('*.md'):
        copia(ori,pth_web/'downloads/docs'/ori.name)
    cfg = {'version': VERSION, 'installed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'selected_components':['aux-assist'] if asist else []}
    if (DIR_APP / '.git').exists():
        cfg['git_commit'] = subprocess.run(['git','-C',str(DIR_APP),'rev-parse','HEAD'],capture_output=True,text=True,check=True).stdout.strip()
        cfg['git_dirty'] = bool(subprocess.run(['git','-C',str(DIR_APP),'status','--porcelain','--untracked-files=no'],capture_output=True,text=True,check=True).stdout.strip())
    if (DIR_APP / 'SHA256SUMS').is_file():
        cfg['source_manifest_sha256'] = suma(DIR_APP / 'SHA256SUMS')
    guarda_json(dentro(raiz, 'var/lib/aux-assist/install.json'), cfg, 0o600)


def instala_asistencia(raiz,dis=None):
    """Install the selected client integration and preserve existing client data."""
    pth = dentro(raiz, 'etc/aux-assist/tmux.conf')
    copia(DIR_APP / 'config/tmux.conf', pth)
    for nom in ('ai.json', 'cli.json', 'profiles.json'):
        pth = dentro(raiz, 'etc/aux-assist/' + nom)
        if not pth.exists():
            copia(DIR_APP / 'assist/payload' / nom, pth)
    if dis != 'alpine':
        for ori in (DIR_APP / 'assist/installed').glob('*.service'):
            copia(ori, dentro(raiz, 'etc/systemd/system/' + ori.name))
    txt = CABECERA + '''[Desktop Entry]
Type=Application
Name=AUX Assist
Comment=Open local assistance controls
Exec=pkexec /usr/local/bin/aux-assist
Icon=utilities-terminal
Terminal=false
Categories=System;
'''
    atomico(dentro(raiz, 'usr/share/applications/aux-assist.desktop'), txt)
    if dis != 'alpine':
        atomico(dentro(raiz, 'usr/lib/sysusers.d/aux-ai.conf'), CABECERA + 'u aux-ai - \"AUX API assistants\" /nonexistent /usr/sbin/nologin\n')


def comandos_base(dis, raiz, nueva, roles, release, native=None, identity=None):
    paq = seleccion(dis, roles, native)['packages']
    from . import identity as idn
    paq=list(dict.fromkeys(paq+idn.paquetes(dis,idn.normaliza(identity))))
    raiz = Path(raiz).resolve()
    if nueva and raiz == Path('/'):
        raise ValueError('Una base nueva necesita un directorio vacío distinto de /.')
    if not nueva and raiz != Path('/'):
        raise ValueError('Para otro destino usar --mode root.')
    if dis == 'alpine':
        from .alpine import comandos
        return comandos(raiz,nueva,paq,release)
    if dis == 'fedora':
        cmd = ['dnf']
        if nueva:
            # Fedora 45 ships vendor repositories outside the local override directory.
            cmd += ['--installroot=' + str(raiz), '--releasever=' + release,
                    '--setopt=reposdir=/etc/yum.repos.d,/usr/share/dnf5/repos.d', '--disablerepo=*']
            cmd += ['--enablerepo=rawhide'] if release == 'rawhide' else ['--enablerepo=fedora','--enablerepo=updates']
        return [cmd + ['-y', 'install', '@core'] + paq]
    if nueva:
        return [['debootstrap', '--components=main,contrib,non-free,non-free-firmware',
                 '--include=' + ','.join(paq), release, str(raiz), 'https://deb.debian.org/debian']]
    return [['apt-get', 'update'], ['apt-get', '-y', 'install'] + paq]


def instala_base(cfg):
    raiz = cfg.root.resolve()
    nueva = cfg.mode == 'root'
    roles = cfg.roles.split(',')
    if not nueva:
        print('DESTINO: SISTEMA ACTUAL · ' + socket.gethostname() + ' · /')
        print('Esta opción instala paquetes y aplicaciones sobre este equipo y puede modificar sus servicios y configuración.')
    from .software import carga
    release = cfg.release or (carga(cfg.distro)['release'] if cfg.distro in ('fedora','alpine') else 'testing')
    if cfg.distro == 'fedora' and nueva and getattr(cfg, 'native', None):
        if release != carga('fedora')['release']:
            raise ValueError('La rama elegida no coincide con el catálogo de grupos Fedora; revisar la selección.')
    native = getattr(cfg, 'native', None)
    from . import identity as idn
    ident=idn.desde_cfg(cfg)
    cmds = comandos_base(cfg.distro, raiz, nueva, roles, release, native,ident)
    idn.aplica(raiz,cfg.distro,ident,False)
    if cfg.apply:
        if nueva and raiz.exists() and any(raiz.iterdir()):
            raise ValueError('La raíz nueva debe estar vacía; no se sustituye un sistema existente.')
        if not nueva:
            dat = Path('/etc/os-release').read_text()
            ids = {lin.split('=',1)[0]:lin.split('=',1)[1].strip('"') for lin in dat.splitlines() if '=' in lin}
            if ids.get('ID') != cfg.distro:
                raise ValueError('La distribución elegida no coincide con el sistema actual.')
        for cmd in cmds:
            if not shutil.which(cmd[0]):
                raise ValueError('Falta herramienta del constructor: ' + cmd[0])
    if cfg.apply and nueva and cfg.distro == 'alpine':
        from .alpine import prepara_raiz
        prepara_raiz(raiz,release)
    for cmd in cmds:
        ejecuta(cmd, cfg.apply)
    print('Instalar herramientas AUX en:', raiz)
    print('aux-assist:', 'seleccionado; cliente, lanzador y servicios de activación manual' if 'aux-assist' in roles else 'sin seleccionar; conservar cualquier instalación anterior')
    if cfg.apply:
        instala_archivos(raiz, roles,cfg.distro)
        idn.aplica(raiz,cfg.distro,ident,True)
        guarda_json(dentro(raiz, 'var/lib/aux-assist/selection.json'), seleccion(cfg.distro, roles, native), 0o600)
        if not nueva and cfg.distro != 'alpine':
            if 'aux-assist' in roles:
                ejecuta(['systemd-sysusers', '/usr/lib/sysusers.d/aux-ai.conf'], True)
            ejecuta(['systemctl', 'daemon-reload'], True)
    if nueva:
        print('Raíz preparada. Particiones, fstab, cuenta, initramfs y cargador requieren la instalación estándar; no se formatea ningún disco.')


def modifica_iso(cfg):
    from . import identity as idn
    if not cfg.iso or not cfg.output or not cfg.iso_sha256:
        raise ValueError('ISO requiere --iso, --iso-sha256 y --output.')
    ori, dst = cfg.iso.resolve(), cfg.output.resolve()
    if dst.is_relative_to(DIR_APP):
        raise ValueError('Guardar la ISO fuera del directorio de fuentes para evitar copiar su propia construcción.')
    if ori == dst or dst.exists() or dst.is_symlink():
        raise ValueError('La ISO de salida debe ser una ruta nueva distinta del origen.')
    if not ori.is_file() or suma(ori) != cfg.iso_sha256.lower():
        raise ValueError('La suma de la ISO de entrada no coincide.')
    if cfg.apply and not shutil.which('xorriso'):
        raise ValueError('Falta xorriso en el constructor.')
    from . import wan_boot
    _, wan = wan_boot.informacion()
    print('Conservar arranque del instalador oficial y añadir perfiles y todas las fuentes AUX bajo /aux.')
    print(wan_boot.TITULO + ' | ' + wan['menu_url'] + ' | BIOS / UEFI x86_64')
    print('El menú oficial se conserva: Fedora inst.ks=cdrom:/aux/profile/installed.ks; Debian preseed/file=/cdrom/aux/profile/preseed.cfg; Alpine conserva setup-alpine y añade /aux/profile/apply-alpine.sh para aplicación explícita posterior.')
    print('La ISO necesita --check-packages antes de --apply. La suma declarada no sustituye la verificación de la firma oficial.')
    if not cfg.apply:
        return
    if not cfg.check_packages:
        raise ValueError('Antes de construir usar --check-packages en un constructor con repositorios de la misma rama.')
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aux-iso-', dir=dst.parent) as tmp:
        pth = Path(tmp)
        build_id = uuid.uuid4().hex
        genera(cfg.distro, cfg.roles.split(','), pth / 'profile', True, build_id, getattr(cfg, 'native', None),idn.desde_cfg(cfg))
        (pth / 'source').mkdir()
        for ori_src in DIR_APP.iterdir():
            if ori_src.is_symlink() or ori_src.name in ('.git','.openai','.venv','__pycache__','dist'):
                continue
            if ori_src.is_dir():
                shutil.copytree(ori_src, pth / 'source' / ori_src.name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                copia(ori_src, pth / 'source' / ori_src.name)
        if not (pth / 'source/SHA256SUMS').is_file():
            raise ValueError('Falta SHA256SUMS del paquete de fuentes.')
        atomico(pth / 'source/.aux-build-id', build_id + '\n')
        parcial = pth / 'output.iso'
        mapas, cola, archivos, _ = wan_boot.prepara_iso(ori, pth / 'wan')
        ejecuta(['xorriso', '-abort_on', 'FAILURE', '-indev', ori, '-outdev', parcial,
                 '-map', pth / 'profile', '/aux/profile', '-map', pth / 'source', '/aux/source',
                 *mapas,
                 '-boot_image', 'any', 'replay', *cola, '-commit', '-end'], True)
        wan_boot.verifica_iso(parcial, archivos, pth / 'readback')
        os.replace(parcial, dst)
    atomico(Path(str(dst) + '.sha256'), suma(dst) + '  ' + dst.name + '\n')
    print('ISO creada. Pendiente de arranque BIOS/UEFI y de instalación real:', dst)


def main(argv=None):
    argv=list(argv) if argv is not None else sys.argv[1:]
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--mode', choices=('iso', 'root', 'kernel-modeler', 'server', 'tools', 'catalog-service', 'existing'))
    par.add_argument('--distro', choices=('fedora', 'debian','alpine'), default='debian')
    par.add_argument('--root', type=Path, default=Path('/'))
    par.add_argument('--roles',help='Comma-separated package roles; kernel-modeler starts with base,kernel-modeler')
    par.add_argument('--target-mode',choices=('iso','root','existing'),help='Explicit destination for kernel-modeler')
    par.add_argument('--release')
    par.add_argument('--iso', type=Path)
    par.add_argument('--iso-sha256')
    par.add_argument('--output', type=Path)
    par.add_argument('--check-packages', action='store_true')
    par.add_argument('--apply', action='store_true')
    par.add_argument('--nginx', action='store_true')
    par.add_argument('--selection',type=Path)
    par.add_argument('--interactive',action='store_true')
    par.set_defaults(native=None,workbench=None)
    pre=argparse.ArgumentParser(add_help=False)
    pre.add_argument('--selection',type=Path)
    ini,_=pre.parse_known_args(argv)
    if ini.selection:
        from .interactive import lee_seleccion
        par.set_defaults(**lee_seleccion(ini.selection))
    par.add_argument('--version',action='version',version='aux-setup '+VERSION)
    from . import identity as idn
    idn.argumentos(par)
    cfg=par.parse_args(argv)
    if cfg.interactive or (not argv and sys.stdin.isatty()):
        from .interactive import prepara
        cfg=prepara(cfg)
        plan=io.StringIO()
        with contextlib.redirect_stdout(plan):
            ejecuta_seleccion(cfg)
        print(plan.getvalue())
        from .console_ui import aplicacion, campo
        with aplicacion('AUX SETUP','ejecucion'):
            respuesta=campo('Revisar el plan y escribir APLICAR; Esc cancela',resumen=plan.getvalue().splitlines())
        if respuesta!='APLICAR':
            print('Plan conservado; no se ejecuta la instalación.')
            return
        cfg.apply=True
    if cfg.mode is None:
        if not argv:
            par.print_help()
            return
        par.error('Elegir explícitamente --mode o --selection; existing instala sobre el sistema actual.')
    from .kernel_modeler import normaliza
    cfg=normaliza(cfg)
    if cfg.roles is None:cfg.roles=','.join(DEFAULT_ROLES)
    if cfg.apply and os.geteuid() != 0 and cfg.mode != 'iso':
        par.error('--apply requiere root para este modo.')
    ejecuta_seleccion(cfg)


def ejecuta_seleccion(cfg):
    from .precautions import lineas
    print('\n'.join(lineas('writes','load')))
    if {'aux-assist','admin'}&set((cfg.roles or '').split(',')):print('\n'.join(lineas('remote')))
    from .kernel_modeler import normaliza,resumen
    cfg=normaliza(cfg)
    if getattr(cfg,'roles',None) is None:cfg.roles=','.join(DEFAULT_ROLES)
    if getattr(cfg,'workbench',None)=='kernel-modeler':print('\n'.join(resumen(cfg.distro)))
    if cfg.mode in ('existing', 'root'):
        instala_base(cfg)
    elif cfg.mode == 'tools':
        print('Instalar herramientas AUX en', cfg.root)
        roles = cfg.roles.split(',')
        seleccion(cfg.distro, roles)
        print('Componentes:', ', '.join(roles))
        if cfg.apply:
            instala_archivos(cfg.root, roles,cfg.distro)
            if cfg.root.resolve() == Path('/') and cfg.distro != 'alpine':
                if 'aux-assist' in roles:
                    ejecuta(['systemd-sysusers', '/usr/lib/sysusers.d/aux-ai.conf'], True)
                ejecuta(['systemctl', 'daemon-reload'], True)
    elif cfg.mode == 'iso':
        modifica_iso(cfg)
    elif cfg.mode == 'catalog-service':
        if cfg.distro == 'alpine':
            raise ValueError('catalog-service requiere systemd; en Alpine ejecutar aux-catalog manualmente.')
        print('Instalar servicio y temporizador; cuenta aux-catalog; configuración /etc/aux/fast-boot.json; catalog_file debe apuntar a /srv/aux/catalog/catalog.json.')
        print('Calendario incluido: sábado 03:00 Europe/Andorra. Activación manual tras revisar las fuentes y el primer resultado.')
        if cfg.root.resolve() != Path('/'):
            raise ValueError('catalog-service se instala en el servidor actual; --root debe ser /.')
        if cfg.apply:
            instala_archivos(Path('/'), ['base'])
            atomico(Path('/usr/lib/sysusers.d/aux-catalog.conf'), CABECERA + 'u aux-catalog - "AUX catalogue updater" /nonexistent /usr/sbin/nologin\n')
            ejecuta(['systemd-sysusers','/usr/lib/sysusers.d/aux-catalog.conf'],True)
            Path('/etc/aux').mkdir(exist_ok=True)
            Path('/srv/aux/catalog').mkdir(parents=True,exist_ok=True)
            shutil.chown('/srv/aux/catalog',user='aux-catalog',group='aux-catalog')
            cfg_srv=Path('/etc/aux/fast-boot.json')
            if not cfg_srv.exists():
                srv=json.loads((DIR_APP/'fast-boot.json').read_text())
                srv.update(catalog_file='/srv/aux/catalog/catalog.json',catalog_git_repository='/srv/aux/catalog',
                           catalog_sources_file='/usr/local/lib/aux/config/catalog.sources.json',metadata_cache='/var/cache/aux-catalog')
                guarda_json(cfg_srv,srv)
            pth_cat=Path('/srv/aux/catalog/catalog.json')
            if not pth_cat.exists():
                copia(DIR_APP/'catalog.json',pth_cat)
                shutil.chown(pth_cat,user='aux-catalog',group='aux-catalog')

            for nom in ('aux-catalog-update.service','aux-catalog-update.timer'):
                copia(DIR_APP/'config'/nom,Path('/etc/systemd/system')/nom)
            ejecuta(['systemctl','daemon-reload'],True)
    else:
        raiz = cfg.root if cfg.root != Path('/') else Path('/var/www/aux.1-s.es')
        cmd = ['python3', str(DIR_APP / 'install-web.py'), '--source', str(DIR_APP), '--root', str(raiz)]
        if cfg.nginx:
            cmd.append('--nginx')
        if cfg.apply:
            cmd.append('--apply')
        # The legacy installer also defaults to a read-only plan.
        ejecuta(cmd, True)
