# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
# Author & Credits: https://www.alawise.es/1-s
"""Native apk plans and explicit post-install profiles for Alpine Linux."""
from pathlib import Path
import re
import shlex
import shutil

from .common import DIR_APP, atomico


def repositorios(rama='edge'):
    if rama != 'edge' and not re.fullmatch(r'v[0-9]+\.[0-9]+',rama):
        raise ValueError('Rama Alpine: edge o vMAJOR.MINOR.')
    return ['https://dl-cdn.alpinelinux.org/alpine/'+rama+'/'+nom for nom in ('main','community')]


def comandos(raiz,nueva,paquetes,rama):
    repos=repositorios(rama)
    cmd=['apk']
    if nueva:
        cmd += ['--root',str(raiz),'--initdb']
    if nueva:
        for url in repos:cmd += ['--repository',url]
    return [cmd+['add','--no-cache']+list(paquetes)]


def prepara_raiz(raiz,rama):
    """Copy builder-trusted keys before apk resolves the new root's repositories."""
    pth=Path('/etc/apk/keys')
    claves=list(pth.glob('*.pub'))
    if not claves:
        raise ValueError('La raíz Alpine requiere las claves de confianza de un constructor Alpine en /etc/apk/keys.')
    dst=Path(raiz)/'etc/apk/keys';dst.mkdir(parents=True,exist_ok=True)
    for arc in claves:
        if arc.is_symlink():raise ValueError('Clave apk simbólica no admitida.')
        shutil.copy2(arc,dst/arc.name)
    atomico(Path(raiz)/'etc/apk/repositories','\n'.join(repositorios(rama))+'\n')


def perfil(destino,paquetes,roles,build_id=None):
    dst=Path(destino)
    atomico(dst/'repositories','\n'.join(repositorios())+'\n')
    atomico(dst/'world','\n'.join(p for p in paquetes if not p.startswith('@'))+'\n')
    txt=(DIR_APP/'profiles/alpine/apply-alpine.sh.in').read_text()
    cmd='apk add --no-cache '+' '.join(shlex.quote(p) for p in paquetes)+'\n'
    txt=txt.replace('apk add --no-cache __AUX_PACKAGES__\n','')
    if build_id:
        txt+='sys_src="$(CDPATH= cd -- "$(dirname -- "$0")/../source" && pwd)"\n'
        txt+='[ "$(cat "$sys_src/.aux-build-id")" = "'+build_id+'" ] || exit 1\n'
        txt+='(cd "$sys_src" && sha256sum -c SHA256SUMS)\n'
    txt+=cmd
    if build_id:
        txt+='python3 "$sys_src/aux-setup" --mode tools --distro alpine --roles '+shlex.quote(','.join(roles))+' --apply\n'
    atomico(dst/'apply-alpine.sh',txt,0o755)
    atomico(dst/'README.txt','Alpine conserva su instalador oficial setup-alpine. Este perfil se aplica explícitamente tras instalar el sistema; no configura particiones ni arranque. Las pruebas físicas de ISO y firmware se realizan por separado.\n')
