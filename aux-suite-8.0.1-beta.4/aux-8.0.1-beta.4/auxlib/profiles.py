# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Select common roles and render Debian, Fedora and Alpine profiles."""
import argparse
import json
import re
import subprocess
from pathlib import Path

from . import VERSION
from .common import CABECERA, DIR_APP, atomico, ejecuta, guarda_json
from . import software

ROLES = {
    'base': {
        'fedora': 'kernel kernel-modules kernel-modules-extra linux-firmware NetworkManager NetworkManager-tui chrony firewalld sudo python3 python3-aiohttp python3-pyyaml tmux openssh-clients nano less curl rsync gnupg2',
        'debian': 'linux-image-amd64 firmware-linux firmware-iwlwifi firmware-realtek firmware-atheros firmware-brcm80211 firmware-sof-signed network-manager chrony sudo python3 python3-aiohttp python3-yaml tmux openssh-client nano less curl rsync gpg',
    },
    'desktop': {'fedora': '@base-x @xfce-desktop xterm polkit',
                'debian': 'task-xfce-desktop xterm polkitd pkexec network-manager-gnome'},
    'aux-assist': {'fedora': 'python3-aiohttp tmux openssh-server openssh-clients kbd procps-ng polkit',
                   'debian': 'python3-aiohttp tmux openssh-server openssh-client kbd procps pkexec'},
    'disks': {'fedora': 'util-linux parted gparted gdisk cryptsetup lvm2 mdadm btrfs-progs xfsprogs e2fsprogs dosfstools exfatprogs ntfs-3g smartmontools nvme-cli ddrescue testdisk',
              'debian': 'util-linux parted gparted gdisk cryptsetup lvm2 mdadm btrfs-progs xfsprogs e2fsprogs dosfstools exfatprogs ntfs-3g smartmontools nvme-cli gddrescue testdisk'},
    'forensics': {'fedora': 'sleuthkit file strace lsof', 'debian': 'sleuthkit file strace lsof'},
    'network': {'fedora': 'iproute iputils bind-utils ethtool tcpdump nmap iperf3',
                'debian': 'iproute2 iputils-ping dnsutils ethtool tcpdump nmap iperf3'},
    'admin': {'fedora': 'cockpit cockpit-storaged cockpit-networkmanager cockpit-packagekit bash-completion git pciutils usbutils',
              'debian': 'cockpit cockpit-storaged cockpit-networkmanager cockpit-packagekit bash-completion git pciutils usbutils'},
    'build': {'fedora': 'xorriso squashfs-tools mtools unzip dialog qrencode python3-pip',
              'debian': 'xorriso squashfs-tools mtools unzip dialog qrencode python3-pip'},
}


from .kernel_modeler import PACKAGES as KERNEL_PACKAGES
ROLES['kernel-modeler']=dict(KERNEL_PACKAGES)
DEFAULT_ROLES=tuple(nom for nom in ROLES if nom not in ('kernel-modeler','aux-assist','admin'))


# Alpine collections use names verified against the recorded official APK indexes.
ALPINE_PACKAGES = {'base': 'alpine-base linux-lts linux-firmware-none openrc bash sudo python3 py3-aiohttp py3-yaml tmux openssh-client-default nano less curl rsync chrony gnupg',
    'desktop': 'xfce4 xfce4-terminal xorg-server xinit dbus elogind polkit networkmanager',
    'aux-assist': 'py3-aiohttp tmux openssh kbd procps-ng polkit',
    'disks': 'util-linux parted gparted gptfdisk cryptsetup lvm2 mdadm btrfs-progs xfsprogs e2fsprogs dosfstools exfatprogs ntfs-3g smartmontools nvme-cli ddrescue testdisk',
    'forensics': 'sleuthkit file strace lsof',
    'network': 'iproute2 iputils bind-tools ethtool tcpdump nmap iperf3',
    'admin': 'bash-completion git pciutils usbutils htop',
    'build': 'alpine-sdk xorriso squashfs-tools mtools unzip dialog libqrencode-tools py3-pip'}
for nom, paquetes in ALPINE_PACKAGES.items():
    ROLES[nom]['alpine'] = paquetes


ROTULOS = {'kernel-modeler':'Kernel Modeler · configuración, compilación y pruebas', 'base':'Base, kernel y firmware', 'desktop':'Escritorio XFCE',
           'aux-assist':'RED TEAM / Red Robin · aux-assist · Cliente de asistencia',
           'disks':'Discos y recuperación', 'forensics':'Análisis forense',
           'network':'Red y diagnóstico', 'admin':'RED TEAM / Red Robin · Administración y SSH',
           'build':'Construcción de medios'}


def seleccion(dis, roles, native=None):
    if dis not in ('fedora', 'debian', 'alpine'):
        raise ValueError('Distribución admitida: fedora, debian o alpine.')
    roles = list(dict.fromkeys(['base'] + list(roles)))
    if any(nom not in ROLES for nom in roles):
        raise ValueError('Rol desconocido. Disponibles: ' + ', '.join(ROLES))
    paq = list(dict.fromkeys(val for nom in roles for val in ROLES[nom][dis].split()))
    dat = {'distribution': dis, 'roles': roles, 'packages': paq,
           'components':['aux-assist'] if 'aux-assist' in roles else []}
    if native is not None:
        nat = software.resuelve(dis, native)
        dat['native'] = nat['native']
        dat['packages'] = list(dict.fromkeys(nat['packages'] + paq))
    return dat


def verifica(dis, paq):
    # Ask the configured native repositories; missing packages abort generation.
    for nom in paq:
        if dis == 'debian':
            res = subprocess.run(['apt-cache', 'policy', nom], text=True, capture_output=True, check=True)
            if not re.search(r'Candidate:\s+(?!\(none\))\S+', res.stdout):
                raise ValueError('Paquete sin candidato: ' + nom)
        elif dis == 'alpine':
            res = subprocess.run(['apk','search','--exact',nom],text=True,capture_output=True,check=True)
            if not any(lin.startswith(nom+'-') for lin in res.stdout.splitlines()):
                raise ValueError('Paquete apk no disponible: '+nom)
        else:
            cmd = ['dnf', 'group', 'info', nom[1:]] if nom.startswith('@') else ['dnf', 'repoquery', '--available', '--qf', '%{name}', nom]
            res = subprocess.run(cmd, text=True, capture_output=True, check=True)
            if not res.stdout.strip() or (not nom.startswith('@') and nom not in res.stdout.split()):
                raise ValueError('Paquete o grupo no disponible: ' + nom)


def genera(dis, roles, destino, comprobar=False, build_id=None, native=None, identity=None):
    if build_id is not None and not re.fullmatch('[a-f0-9]{32}', build_id):
        raise ValueError('Identificador de construcción inválido.')
    dat = seleccion(dis, roles, native)
    from . import identity as idn
    ident=idn.normaliza(identity)
    if ident:
        dat['identity']=ident;dat['packages']=list(dict.fromkeys(dat['packages']+idn.paquetes(dis,ident)))
    if comprobar:
        verifica(dis, dat['packages'])
    dat['repository_check'] = 'passed-on-builder' if comprobar else 'not-run'
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    guarda_json(destino / 'selection.json', dat)
    atomico(destino / 'packages.txt', CABECERA + '\n'.join(dat['packages']) + '\n')
    if 'kernel-modeler' in dat['roles']:
        from .kernel_modeler import escribe
        escribe(destino/'kernel-modeler',dis,dat['packages'])
    if dis == 'fedora':
        txt = (DIR_APP / 'profiles/fedora/installed.ks').read_text()
        if native is not None:
            rama = software.carga('fedora')['release']
            if rama != 'rawhide' and not re.fullmatch(r'[0-9]+',rama):
                raise ValueError('Rama Fedora no admitida para el instalador.')
            ruta = 'development/rawhide' if rama == 'rawhide' else 'releases/'+rama
            txt = re.sub(r'(?m)^url --url=.*$', 'url --url=https://download.fedoraproject.org/pub/fedora/linux/'+ruta+'/Everything/x86_64/os/',txt)
        ini, resto = txt.split('%packages\n', 1)
        _, fin = resto.split('%end', 1)
        txt = ini + '%packages\n@core\n' + '\n'.join(dat['packages']) + '\n%end' + fin
        if native is not None and not any('desktop' in nom or nom == '@base-x' for nom in dat['packages']):
            txt = txt.replace('xconfig --startxonboot\n', '')
        if build_id:
            txt += '''
%post --nochroot --erroronfail --interpreter=/usr/bin/bash
# Locate only the media carrying this exact source build marker.
set -euo pipefail
sys_mnt="$(mktemp -d /run/aux-media.XXXXXX)"
trap 'umount "$sys_mnt" 2>/dev/null || true; rmdir "$sys_mnt" 2>/dev/null || true' EXIT
instala_aux() {
    while IFS= read -r sys_dev; do
        mount -o ro "$sys_dev" "$sys_mnt" || continue
        if [ -f "$sys_mnt/aux/source/.aux-build-id" ] && [ "$(cat "$sys_mnt/aux/source/.aux-build-id")" = "''' + build_id + '''" ]; then
            mkdir -p /mnt/sysroot/opt/aux-source
            cp -a "$sys_mnt/aux/source/." /mnt/sysroot/opt/aux-source/
            (cd /mnt/sysroot/opt/aux-source; sha256sum -c SHA256SUMS)
            /usr/bin/python3 /mnt/sysroot/opt/aux-source/aux-setup --mode tools --distro fedora --root /mnt/sysroot --roles ''' + ','.join(dat['roles']) + ''' --apply
            return 0
        fi
        umount "$sys_mnt"
    done < <(blkid -t TYPE=iso9660 -o device)
    return 1
}
instala_aux
%end
'''
        atomico(destino / 'installed.ks', idn.perfil(dis,txt,ident))
    elif dis == 'alpine':
        from .alpine import perfil
        perfil(destino, dat['packages'], dat['roles'], build_id)
        pth=destino/'apply-alpine.sh';atomico(pth,idn.perfil(dis,pth.read_text(),ident),0o755)
    else:
        txt = (DIR_APP / 'profiles/debian/preseed.cfg').read_text()
        txt = re.sub(r'^d-i pkgsel/include string .*$', 'd-i pkgsel/include string ' + ' '.join(dat['packages']), txt, flags=re.M)
        if native is not None:
            txt = re.sub(r'^tasksel tasksel/first multiselect .*$',
                         'tasksel tasksel/first multiselect ' + ', '.join(dat['native']['tasks']), txt, flags=re.M)
        if build_id:
            txt += 'd-i preseed/late_command string test "$(cat /cdrom/aux/source/.aux-build-id)" = "' + build_id + '" && mkdir -p /target/opt/aux-source && cp -a /cdrom/aux/source/. /target/opt/aux-source/ && in-target /bin/sh -c "cd /opt/aux-source && sha256sum -c SHA256SUMS && python3 aux-setup --mode tools --roles ' + ','.join(dat['roles']) + ' --apply"\n'
        atomico(destino / 'preseed.cfg', idn.perfil(dis,txt,ident))
    return dat


def main(argv=None):
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--distro', choices=('fedora', 'debian', 'alpine'))
    par.add_argument('--roles', default=','.join(nom for nom in DEFAULT_ROLES if nom != 'desktop'))
    par.add_argument('--output', type=Path)
    par.add_argument('--check-packages', action='store_true')
    par.add_argument('--interactive', action='store_true')
    par.add_argument('--tasks', help='Debian tasksel IDs separated by commas.')
    par.add_argument('--environment', help='Fedora environment ID; empty selects groups only.')
    par.add_argument('--groups', help='Fedora additional group IDs separated by commas.')
    par.add_argument('--version',action='version',version='aux-profile '+VERSION)
    from . import identity as idn
    idn.argumentos(par)
    cfg = par.parse_args(argv)
    if cfg.interactive:
        from .console_ui import aplicacion, campo
        from .interactive import elige
        with aplicacion('AUX PROFILE','ejecucion'):
            cfg.distro=cfg.distro or elige('Distribución del perfil',[('Debian','debian'),('Fedora','fedora'),('Alpine','alpine')])
            cfg.output=cfg.output or Path(campo('Directorio nuevo de salida'))
    elif cfg.distro is None or cfg.output is None:
        par.error('Indicar --distro y --output, o usar --interactive.')
    roles = cfg.roles.split(',')
    native = software.defecto(cfg.distro)
    if cfg.interactive:
        from .interactive import software_nativo, marca
        with aplicacion('AUX PROFILE','ejecucion'):
            native = software_nativo(cfg.distro)
            lista = [nom for nom in ROLES if nom not in ('base', 'desktop')]
            roles = ['base'] + marca('Herramientas adicionales AUX', [(nom, ROTULOS[nom]) for nom in lista], [nom for nom in lista if nom in DEFAULT_ROLES])
    if cfg.tasks is not None or cfg.environment is not None or cfg.groups is not None:
        native = software.defecto(cfg.distro)
        if cfg.distro == 'debian':
            if cfg.environment is not None or cfg.groups is not None:
                par.error('--groups corresponde a Fedora/Alpine; --environment a Fedora.')
            native['tasks'] = [nom for nom in cfg.tasks.split(',') if nom]
        else:
            if cfg.tasks is not None:
                par.error('--tasks es una opción de Debian.')
            if cfg.environment is not None:
                if cfg.distro != 'fedora':
                    par.error('--environment es una opción de Fedora.')
                native['environment'] = cfg.environment
                native['groups'] = []
            if cfg.groups is not None:
                native['groups'] = [nom for nom in cfg.groups.split(',') if nom]
    if cfg.interactive:
        cfg=idn.pregunta(cfg)
        if cfg.output.exists():
            raise ValueError('La salida interactiva debe ser un directorio nuevo.')
        with aplicacion('AUX PROFILE','ejecucion'):
            datos=['Distribución: '+cfg.distro,'Salida: '+str(cfg.output),'Herramientas: '+', '.join(roles),
                   'Selección nativa: '+json.dumps(native,ensure_ascii=False)]
            if campo('Revisar y escribir GENERAR para crear los perfiles',resumen=datos)!='GENERAR':
                return
    print(json.dumps(genera(cfg.distro, roles, cfg.output, cfg.check_packages, native=native, identity=idn.desde_cfg(cfg)), indent=2))
