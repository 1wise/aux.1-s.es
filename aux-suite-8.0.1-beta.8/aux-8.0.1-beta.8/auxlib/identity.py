# Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
# Author & Credits: https://www.alawise.es/1-s
"""Share explicit installation identity across CLI, profiles and exported JSON."""
import json
from pathlib import Path
import re
import shlex
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError

from .common import atomico,dentro,ejecuta,guarda_json

CAMPOS=('hostname','locale','timezone','user')
DEFECTOS={'hostname':'','locale':'es_ES.UTF-8','timezone':'Europe/Andorra','user':''}


def normaliza(dat=None):
    if dat is None:return {}
    if not isinstance(dat,dict) or set(dat)-set(CAMPOS):raise ValueError('Identidad: hostname, locale, timezone y user; sin contraseñas.')
    sal={}
    for nom,val in dat.items():
        if val in (None,''):continue
        if not isinstance(val,str) or val!=val.strip():raise ValueError('Identidad inválida: '+nom)
        if nom=='hostname':
            if len(val)>253 or not all(re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?',p) for p in val.split('.')):
                raise ValueError('Hostname: etiquetas DNS válidas, sin espacios ni guiones en los extremos.')
            val=val.lower()
        elif nom=='locale':
            if not re.fullmatch(r'(?:C|POSIX|[a-z]{2,3}(?:_[A-Z]{2})?)(?:\.(?:UTF-8|utf8))?',val):raise ValueError('Locale: usar C.UTF-8 o idioma_PAIS.UTF-8.')
        elif nom=='timezone':
            if not re.fullmatch(r'[A-Za-z0-9_+-]+(?:/[A-Za-z0-9_+-]+)*',val):raise ValueError('Zona IANA inválida.')
            try:ZoneInfo(val)
            except ZoneInfoNotFoundError:raise ValueError('Zona IANA desconocida: '+val) from None
        elif not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',val) or val in ('root','bin','daemon','sys','sync','nobody','osquery','aux-ai','aux-catalog'):
            raise ValueError('Usuario: cuenta personal válida de hasta 32 caracteres; sin cuentas del sistema.')
        sal[nom]=val
    return sal


def desde_cfg(cfg):
    base=dict(getattr(cfg,'identity',None) or {})
    for nom in CAMPOS:
        if getattr(cfg,nom,None) is not None:base[nom]=getattr(cfg,nom)
    return normaliza(base)


def argumentos(par):
    for nom in CAMPOS:par.add_argument('--'+nom,help={'hostname':'Stable unique hostname for the target machine.','locale':'Primary locale, for example es_ES.UTF-8.','timezone':'IANA timezone, for example Europe/Andorra.','user':'Personal login name; no passwords are stored in selections.'}[nom])
    par.set_defaults(identity=None)


def pregunta(cfg):
    from .console_ui import campo
    if campo('Personalizar hostname, locale, timezone y usuario [s/N]','N').lower()!='s':return cfg
    dat={}
    for nom in CAMPOS:
        def verifica(val,nom=nom):normaliza({nom:val});return val
        dat[nom]=campo('Identidad / '+nom,DEFECTOS[nom],resumen=['Hostname único y estable por equipo. El usuario se crea con contraseña bloqueada; definirla localmente con passwd.','Vacío conserva la selección del instalador. No se solicita ni exporta una contraseña.'],validar=verifica)
    cfg.identity=normaliza(dat)
    return cfg


def paquetes(dis,dat):
    if not dat:return []
    sal=['tzdata'] if dat.get('timezone') else []
    if dat.get('locale'):
        sal+=['locales'] if dis=='debian' else ['musl-locales','musl-locales-lang'] if dis=='alpine' else ['glibc-langpack-'+dat['locale'].split('_')[0]] if dat['locale'] not in ('C','C.UTF-8','POSIX') else []
    return sal


def perfil(dis,txt,dat):
    dat=normaliza(dat)
    if not dat:return txt
    if dis=='fedora':
        if 'locale' in dat:txt=re.sub(r'(?m)^lang .*$', 'lang '+dat['locale'],txt)
        if 'timezone' in dat:txt=re.sub(r'(?m)^timezone .*$', 'timezone '+dat['timezone']+' --utc',txt)
        if 'hostname' in dat:txt=re.sub(r'(?m)^(network .*)$',r'\1 --hostname='+dat['hostname'],txt)
        if 'user' in dat:txt+='\n# Set the personal password in the installer or with passwd before use.\nuser --name='+dat['user']+' --lock\nfirstboot --enable\n'
    elif dis=='debian':
        if 'locale' in dat:txt=re.sub(r'(?m)^d-i debian-installer/locale string .*$', 'd-i debian-installer/locale string '+dat['locale'],txt)
        if 'timezone' in dat:txt=re.sub(r'(?m)^d-i time/zone string .*$', 'd-i time/zone string '+dat['timezone'],txt)
        if 'hostname' in dat:txt+='\nd-i netcfg/get_hostname string '+dat['hostname']+'\nd-i netcfg/hostname string '+dat['hostname']+'\n'
        if 'user' in dat:txt+='\nd-i passwd/user-fullname string '+dat['user']+'\nd-i passwd/username string '+dat['user']+'\n# The installer still requests the password interactively.\n'
    else:
        # The Alpine profile runs on the installed destination, never on the builder.
        txt+='\n# Explicit target identity; passwords are configured locally.\n'
        if 'hostname' in dat:txt+="printf '%s\\n' "+shlex.quote(dat['hostname'])+' > /etc/hostname\n'
        if 'locale' in dat:txt+="printf '%s\\n' "+shlex.quote('export LANG='+dat['locale'])+' > /etc/profile.d/aux-locale.sh\n'
        if 'timezone' in dat:txt+='ln -snf '+shlex.quote('/usr/share/zoneinfo/'+dat['timezone'])+' /etc/localtime\n'
        if 'user' in dat:txt+='id -u '+dat['user']+' >/dev/null 2>&1 || adduser -D -s /bin/ash '+dat['user']+'\n'
    return txt


def aplica(raiz,dis,dat,aplicar=False):
    dat=normaliza(dat);raiz=Path(raiz).resolve()
    if not dat:return
    print('Identidad del destino:',json.dumps(dat,ensure_ascii=False))
    if dat.get('user'):print('La cuenta nueva queda bloqueada hasta definir su contraseña con passwd. No se añade privilegio administrativo.')
    if not aplicar:return
    # Validate target prerequisites before the first write.
    if dat.get('timezone') and not dentro(raiz,'usr/share/zoneinfo/'+dat['timezone']).is_file():raise ValueError('Instalar tzdata en el destino antes de configurar su zona.')
    if dat.get('user'):
        pth=dentro(raiz,'etc/passwd')
        rows=[line.split(':') for line in pth.read_text().splitlines()] if pth.is_file() else []
        old=next((e for e in rows if e[0]==dat['user']),None)
        if old and int(old[2])<1000:raise ValueError('Se conserva la cuenta del sistema existente: '+dat['user'])
    for rel,txt in [('etc/hostname',dat.get('hostname')),('etc/locale.conf','LANG='+dat['locale'] if dat.get('locale') else None),('etc/timezone',dat.get('timezone'))]:
        if txt:atomico(dentro(raiz,rel),txt+'\n')
    if dat.get('timezone'):
        zona=dentro(raiz,'usr/share/zoneinfo/'+dat['timezone'])
        if not zona.is_file():raise ValueError('Instalar tzdata en el destino antes de configurar su zona.')
        pth=dentro(raiz,'etc/localtime');pth.unlink(missing_ok=True);pth.symlink_to('../usr/share/zoneinfo/'+dat['timezone'])
    if raiz==Path('/') and dat.get('hostname'):ejecuta(['hostname',dat['hostname']],True)
    if dat.get('locale') and dis=='debian' and dat['locale'] not in ('C','C.UTF-8','POSIX'):
        atomico(dentro(raiz,'etc/locale.gen'),dat['locale']+' UTF-8\n')
        ejecuta(['chroot',raiz,'locale-gen'],True)
    if dat.get('user'):
        usr=dat['user'];pth=dentro(raiz,'etc/passwd')
        filas=[s.split(':') for s in pth.read_text().splitlines()] if pth.is_file() else []
        actual=next((e for e in filas if e[0]==usr),None)
        if actual and int(actual[2])<1000:raise ValueError('Se conserva la cuenta del sistema existente: '+usr)
        if not actual:ejecuta(['chroot',raiz,'adduser','-D','-s','/bin/ash',usr] if dis=='alpine' else ['useradd','--root',raiz,'--create-home','--password','!','--shell','/bin/bash',usr],True)
    guarda_json(dentro(raiz,'var/lib/aux-assist/identity.json'),dat,0o600)
