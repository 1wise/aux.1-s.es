# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
# Author & Credits: https://www.alawise.es/1-s
"""Central settings; private credentials never belong to deployable inputs."""
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

from .common import DIR_APP, crea_si_falta, guarda_json

SECRETOS = ('ftp_password', 'ssh_password', 'openai_api_key', 'gemini_api_key', 'osctrl_api_token')
CAMPOS = {
    'observe.api_url': 'https', 'observe.environment': 'id',
    'observe.limit': 'observe_limit', 'observe.ca_file': 'path',
    'output': 'path', 'cache': 'path', 'ram_dir': 'path',
    'catalog_git_repository':'path','metadata_cache':'path', 'status_file':'path', 'evidence_file':'path', 'catalog_sources_file':'path',
    'checkstatus.bastion.enabled':'bool','checkstatus.bastion.transport':'inventory_transport','checkstatus.bastion.directories':'directories',
    'checkstatus.bastion.fallback_ftp':'bool',
    'checkstatus.max_age_seconds':'positive','checkstatus.timeout_seconds':'positive',
    'ai.max_output_tokens':'tokens',
    'catalog_file': 'path', 'catalog_profile': 'path', 'checksums': 'path',
    'url_file': 'path', 'light_url_file': 'path', 'heavy_url_file': 'path',
    'base_url': 'url', 'pxe_url': 'url', 'download_url': 'url',
    'targets.bastion.base_url': 'url', 'targets.bastion.pxe_url': 'url',
    'targets.bastion.download_url': 'url', 'targets.bastion.tec_url': 'url',
    'targets.excalibur.base_url': 'url', 'targets.excalibur.pxe_url': 'url',
    'targets.excalibur.download_url': 'url', 'targets.excalibur.tec_url': 'url',
    'bastion.web_hosts': 'hosts', 'bastion.cli_hosts': 'hosts',
    'ftp_host': 'host', 'ftp_user': 'user', 'ftp_port': 'port',
    'ftp_root': 'remote', 'ftp_tls': 'bool',
    'mirror.transport': 'transport', 'mirror.ssh_host': 'host',
    'mirror.ssh_user': 'user', 'mirror.ssh_port': 'port',
    'mirror.ssh_identity': 'path', 'mirror.ssh_known_hosts':'path', 'mirror.ssh_auth':'ssh_auth', 'mirror.remote_root': 'remote',
    'mirror.state_root': 'path', 'mirror.source_root': 'path',
    'mirror.release_id': 'id',
    'mirror.minimum_isos': 'count',
    'ai.enabled': 'bool', 'ai.openai.model': 'model', 'ai.gemini.model': 'model',
    'presets.preset_ram_gib':'positive','presets.preset_ssd_gib':'positive',
    'ram_budget_gib': 'positive', 'ssd_budget_gib': 'positive',
    'ram_reserve_percent': 'percent', 'jobs': 'jobs',
    'tec.public_url': 'url', 'tec.data_dir': 'path', 'tec.web_dir': 'path',
    'tls.certificate': 'path', 'tls.key': 'path',
}
HOST = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\Z')


def ruta_config(pth=None):
    pth_usr = Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'aux/config.json'
    arc_cfg = pth or os.environ.get('AUX_CONFIG_FILE') or (pth_usr if pth_usr.is_file() else DIR_APP/'fast-boot.json')
    return Path(arc_cfg).expanduser().resolve()


def lee_config(pth=None):
    dat = json.loads(ruta_config(pth).read_text())
    def revisa(val):
        if isinstance(val, dict):
            for nom, ent in val.items():
                if re.search(r'password|passwd|api.?key|access.?token|osctrl_api_token|^token$', nom, re.I):
                    raise ValueError('Credencial en configuración pública: ' + nom)
                revisa(ent)
        elif isinstance(val, list):
            for ent in val: revisa(ent)
    if not isinstance(dat, dict): raise ValueError('La configuración debe ser un objeto JSON.')
    revisa(dat)
    return dat


def valor(dat, nom, defecto=None):
    for parte in nom.split('.'):
        if not isinstance(dat, dict) or parte not in dat: return defecto
        dat = dat[parte]
    return dat


def convierte(nom, txt):
    tip = CAMPOS[nom]
    txt = txt.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in txt):
        raise ValueError('No se admiten caracteres de control.')
    if tip == 'bool':
        if txt.lower() not in ('true','false','si','sí','no','1','0'):
            raise ValueError('Usar true/false.')
        return txt.lower() in ('true','si','sí','1')
    if tip in ('port','positive','percent','jobs','count','observe_limit','tokens'):
        lim = {'port':(1,65535),'positive':(1,1048576),'percent':(0,99),'jobs':(1,16),'count':(0,1000000),'observe_limit':(1,1000),'tokens':(128,4096)}[tip]
        if not txt.isdigit() or not lim[0] <= int(txt) <= lim[1]:
            raise ValueError('Número fuera de límites: '+nom)
        return int(txt)
    if tip == 'directories':
        from .checkstatus import _raiz
        from .catalog_v8 import url_publica
        val=json.loads(txt)
        if not isinstance(val,list) or not val or len(val)>32:raise ValueError('Indicar entre 1 y 32 directorios JSON.')
        for ent in val:
            if not isinstance(ent,dict) or not {'path','public_url'}<=set(ent) or set(ent)-{'path','public_url','ftp_path'}:raise ValueError('Cada directorio requiere path y public_url; ftp_path es opcional.')
            _raiz(ent['path']);url_publica(ent['public_url'])
            if 'ftp_path' in ent:_raiz(ent['ftp_path'])
        return val
    if tip == 'path': return str(Path(txt).expanduser().resolve()) if txt else None
    if tip == 'https':
        if not txt: return None
        from .observe import url_api
        return url_api(txt)
    if tip == 'url':
        url = urlsplit(txt)
        if url.scheme not in ('http','https') or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('URL HTTP(S) sin credenciales, consulta ni fragmento.')
        return txt.rstrip('/')
    if tip in ('host','hosts'):
        vals = txt.split(',') if tip == 'hosts' else [txt]
        if not vals or any(not HOST.fullmatch(v.strip()) for v in vals):
            raise ValueError('Host sin protocolo, puerto ni credenciales.')
        return [v.strip().lower() for v in vals] if tip == 'hosts' else txt
    if tip == 'user':
        if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', txt):
            raise ValueError('Usuario inválido.')
    if tip == 'remote' and not (nom=='ftp_root' and txt=='/'):
        if not txt.startswith('/') or '..' in txt.split('/') or '//' in txt or txt == '/':
            raise ValueError('Ruta remota absoluta del sitio, distinta de / y sin ..')
    if tip in ('id','model'):
        if not txt and tip == 'model': return None
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', txt):
            raise ValueError('Identificador inválido.')
    if tip == 'transport' and txt not in ('rsync','ftps'):
        raise ValueError('Transporte: rsync o ftps.')
    if tip == 'inventory_transport' and txt not in ('auto','rsync','ftp','ftps'):
        raise ValueError('Inventario: auto, rsync, ftp o ftps.')
    if tip == 'ssh_auth' and txt not in ('auto','key','password'):
        raise ValueError('Autenticación SSH: auto, key o password.')
    return txt


def establece(nom, txt, pth=None):
    val = convierte(nom, txt)
    dat = lee_config(pth)
    arc_cfg = ruta_config(pth)
    if pth is None and not os.environ.get('AUX_CONFIG_FILE') and arc_cfg == DIR_APP/'fast-boot.json':
        # Runtime edits must not invalidate the release checksums used by ISO builds.
        personal = Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'aux'
        if dat.get('catalog_file', 'catalog.json') == 'catalog.json' and nom != 'catalog_file':
            pth_cat = personal/'catalog.json'
            if not pth_cat.exists():
                crea_si_falta(pth_cat, (DIR_APP/'catalog.json').read_bytes())
            dat['catalog_file'] = str(pth_cat.resolve())
        for clave in ('url_file','light_url_file','heavy_url_file','catalog_file','catalog_profile','checksums','status_file','evidence_file','catalog_sources_file'):
            if dat.get(clave) and not Path(dat[clave]).is_absolute(): dat[clave]=str(DIR_APP/dat[clave])
        arc_cfg = Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'aux/config.json'
        arc_cfg.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    obj = dat
    partes = nom.split('.')
    for parte in partes[:-1]: obj = obj.setdefault(parte, {})
    obj[partes[-1]] = val
    guarda_json(arc_cfg, dat)
    return val


def ruta_secretos(pth=None):
    return Path(pth or os.environ.get('AUX_CREDENTIAL_FILE') or
                Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'aux/credentials.json').expanduser()


def valida_privado(pth, config=None):
    arc = Path(pth)
    dat = lee_config(config)
    raices = [DIR_APP, dat.get('output'), dat.get('cache'), dat.get('ram_dir'),
              valor(dat,'mirror.source_root'), valor(dat,'tec.web_dir')]
    if arc.is_symlink() or any(arc.resolve().is_relative_to(Path(r).expanduser().resolve()) for r in raices if r):
        raise ValueError('Las claves deben quedar fuera de código, caché, RAM y raíces web.')


def lee_secretos(pth=None, config=None):
    arc = ruta_secretos(pth)
    valida_privado(arc, config)
    if not arc.exists(): return {}
    st = arc.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) != 0o600:
        raise ValueError('El almacén privado debe pertenecer al usuario y tener modo 0600.')
    dat = json.loads(arc.read_text())
    if not isinstance(dat,dict) or set(dat)-set(SECRETOS): raise ValueError('Almacén privado inválido.')
    return dat


def guarda_secreto(nom, txt, pth=None, config=None):
    if nom not in SECRETOS: raise ValueError('Credencial desconocida.')
    arc = ruta_secretos(pth)
    dat = lee_secretos(arc, config)
    if txt: dat[nom] = txt
    else: dat.pop(nom, None)
    arc.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if arc.parent.stat().st_uid != os.getuid() or stat.S_IMODE(arc.parent.stat().st_mode) & 0o077:
        raise ValueError('La carpeta privada debe pertenecer al usuario y tener modo 0700.')
    guarda_json(arc, dat, 0o600)


def secreto_api(proveedor):
    return lee_secretos().get(proveedor+'_api_key')


def diagnostico(config=None, secretos=None):
    dat = lee_config(config)
    claves = lee_secretos(secretos, config)
    avisos = []
    for nom in ('output','cache'):
        if not Path(dat[nom]).is_dir(): avisos.append('No disponible aquí: '+nom+' = '+dat[nom])
    for nom in ('catalog_file','catalog_profile'):
        if dat.get(nom) and not Path(dat[nom]).is_file(): avisos.append('No existe: '+nom)
    modo = valor(dat,'mirror.transport','rsync')
    campos = ('mirror.ssh_host','mirror.ssh_user','mirror.remote_root') if modo == 'rsync' else ('ftp_host','ftp_user','ftp_root')
    for nom in campos:
        if not valor(dat,nom): avisos.append('Falta configurar '+nom)
    return {'transport':modo,'warnings':avisos,
            'credentials':{n:('configured' if claves.get(n) else 'missing') for n in SECRETOS}}
