# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Additive release phases over original beta.19; payload bytes are never staged."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import datetime

from .common import DIR_APP, guarda_json
from . import settings as cfg
from . import mirror_inventory as inv
from . import mirror_transport as net


def contexto(config=None, release_id=None):
    dat = cfg.lee_config(config)
    nom = cfg.convierte('mirror.release_id',release_id or cfg.valor(dat,'mirror.release_id','beta20'))
    base = Path(cfg.valor(dat,'mirror.state_root') or Path.home()/'.local/share/aux/mirrors').expanduser().resolve()
    src = Path(cfg.valor(dat,'mirror.source_root') or dat['output']).expanduser().resolve()
    cache,ram = (Path(dat[n]).expanduser().resolve() for n in ('cache','ram_dir'))
    for pth in (DIR_APP,src,cache,ram):
        if base.is_relative_to(pth) or pth.is_relative_to(base):
            raise ValueError('OUTPUT de trabajo debe estar fuera de código, INPUT, caché y RAM.')
    huella = hashlib.sha256(json.dumps(dat,sort_keys=True).encode()).hexdigest()
    return {'config':str(cfg.ruta_config(config)),'settings':dat,'id':nom,'base':base,
            'root':base/nom,'source':src,'cache':cache,'ram':ram,'config_sha256':huella}


def estado(ctx, requerido=False):
    arc = ctx['root']/'state.json'
    if not arc.exists():
        if requerido: raise ValueError('Ejecutar inventory --apply primero.')
        return None
    if arc.is_symlink(): raise ValueError('Estado enlazado no permitido.')
    dat = json.loads(arc.read_text())
    if dat.get('config_sha256') != ctx['config_sha256']:
        raise ValueError('Configuración distinta; utilizar otro --release-id.')
    for nom in ('inventory','web'):
        if dat.get(nom) and inv.huella(dat[nom]['files']) != dat[nom]['sha256']:
            raise ValueError('Inventario alterado: '+nom)
    return dat


def guarda(ctx, dat):
    guarda_json(ctx['root']/'state.json',dat,0o600)


@contextmanager
def bloqueo(ctx):
    ctx['base'].mkdir(parents=True,exist_ok=True,mode=0o700)
    arc = ctx['base']/'.release.lock'
    fd = os.open(arc,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    except BlockingIOError:
        raise ValueError('Otra operación de réplica está activa.') from None
    finally: os.close(fd)


def plan(ctx):
    dat = estado(ctx)
    modo = cfg.valor(ctx['settings'],'mirror.transport','rsync')
    nom = 'mirror.remote_root' if modo == 'rsync' else 'ftp_root'
    return {'release':ctx['id'],'input':str(ctx['source']),'cache':str(ctx['cache']),
            'output_web':str(ctx['root']/'web'),'transport':modo,
            'remote_host':cfg.valor(ctx['settings'],'mirror.ssh_host') if modo == 'rsync' else ctx['settings'].get('ftp_host'),
            'remote_user':cfg.valor(ctx['settings'],'mirror.ssh_user') if modo == 'rsync' else ctx['settings'].get('ftp_user'),
            'remote_port':cfg.valor(ctx['settings'],'mirror.ssh_port',22) if modo == 'rsync' else ctx['settings'].get('ftp_port',21),
            'remote_root':cfg.valor(ctx['settings'],nom),
            'minimum_isos':cfg.valor(ctx['settings'],'mirror.minimum_isos',0),
            'phases':['inventory','deploy','verify','generate','publish','verify'],
            'payload_copies':0,'remote_delete':False,'state':resumen(dat)}


def resumen(dat):
    if dat is None: return {'phase':'not-inventoried'}
    sal = {k:v for k,v in dat.items() if k not in ('inventory','web','config_sha256')}
    for nom in ('inventory','web'):
        if dat.get(nom): sal[nom] = {k:v for k,v in dat[nom].items() if k not in ('files','excluded_private')}
    return sal


def captura(ctx):
    if estado(ctx): raise ValueError('Inventario ya capturado; conservarlo y elegir otro --release-id.')
    for nom in ('catalog_file','catalog_profile','checksums'):
        if ctx['settings'].get(nom) and not Path(ctx['settings'][nom]).is_file():
            raise ValueError('No existe el INPUT configurado: '+nom)
    perfil = Path(ctx['settings'].get('catalog_profile') or Path(ctx['config']).parent/'state/catalog-profile.json')
    if any((ctx['source']/'origins').glob('custom_*.ipxe')) and not perfil.is_file():
        raise ValueError('Conservar recetas personalizadas: configurar catalog_profile con el perfil original antes de transferir.')
    dat = inv.inventario(ctx['source'],ctx['cache'],ctx['ram'],ctx['settings'].get('checksums'))
    if not dat['files']: raise ValueError('El INPUT público y la caché están vacíos.')
    minimo = cfg.convierte('mirror.minimum_isos',str(cfg.valor(ctx['settings'],'mirror.minimum_isos',0)))
    if dat['iso_count'] < minimo:
        raise ValueError(f"Inventario incompleto: {dat['iso_count']} ISO; mínimo esperado {minimo}. Revisar el INPUT original antes de publicar.")
    guarda(ctx,{'config_sha256':ctx['config_sha256'],'inventory':dat,'phase':'inventoried',
                'deployed':False,'media_verified':False,'published':False,'final_verified':False})
    return estado(ctx)


def despliega(ctx, secretos=None):
    dat = estado(ctx,True)
    if dat['published']: raise ValueError('Publicación terminada; utilizar otro --release-id.')
    todos = dat['inventory']['files']
    items = [e for e in todos if not pagina(e['relative'])]
    # Reuse only the aliases from this immutable release; never duplicate ISO bytes.
    vista = ctx['root']/'input-view'
    if not vista.exists(): inv.vista(todos,vista)
    pth = ctx['root']/'deploy-view'
    if not pth.exists(): inv.vista(items,pth)
    net.envia(ctx['settings'],items,pth,cfg.lee_secretos(secretos,ctx['config']))
    dat.update(deployed=True,media_verified=False,phase='deployed')
    guarda(ctx,dat)
    return dat


def pagina(rel):
    pth = Path(rel)
    return (pth.parts[0] in ('assets','downloads','files','contents','origins','catalog') or
            len(pth.parts) == 1 and (pth.suffix.lower() in ('.html','.htm','.css','.js','.json','.xml','.ipxe','.txt','.md')
                                    or rel == '.htaccess'))


def finales(dat):
    items = {e['relative']:e for e in dat['inventory']['files']}
    if dat['published']:
        items.update({e['relative']:e for e in dat['web']['files']})
    return sorted(items.values(),key=lambda e:e['relative'])


def verifica(ctx, secretos=None):
    dat = estado(ctx,True)
    if not dat['deployed']: raise ValueError('Ejecutar deploy --apply antes de verificar.')
    items = finales(dat) if dat['published'] else [e for e in dat['inventory']['files'] if not pagina(e['relative'])]
    print('VERIFY: SHA-256 remoto de '+str(len(items))+' archivos; '+
          str(sum(e['size'] for e in items))+' bytes. La lectura puede tardar varios minutos.',flush=True)
    ret = net.verifica(ctx['settings'],items,cfg.lee_secretos(secretos,ctx['config']))
    correcto = not ret['failures'] and ret['checked'] == len(items)
    campo = 'final_verified' if dat['published'] else 'media_verified'
    dat[campo] = correcto
    if campo=='media_verified':
        dat['media_verified_at']=datetime.datetime.now(datetime.timezone.utc).isoformat() if correcto else None
    dat['verification'] = ret
    dat['phase'] = ('verified' if dat['published'] else 'media-verified') if correcto else 'verification-failed'
    guarda(ctx,dat)
    if not correcto: raise ValueError('La réplica no coincide; ver status. No se avanza a Generate.')
    return dat


def apache(dat):
    hosts = dat.get('bastion',{}).get('cli_hosts',['p.1-s.es','p.1-s.eu'])
    patron = '|'.join(re.escape(cfg.convierte('ftp_host',h)) for h in hosts)
    return '''# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
DirectoryIndex index.html
Options -Indexes
AddType text/plain .ipxe
AddType application/octet-stream .iso .img .efi .kpxe .lkrn .bin .bzi
RewriteEngine On
RewriteRule (?:^|/)(?:[.]env|[.]git|[.]ssh|credentials[.]json|manage[.]php|private|sessions|logs)(?:/|$) - [F,L,NC]
RewriteRule ^(?:tec|assist|cli)(?:/|$) - [F,L,NC]
RewriteRule [.]php$ - [F,L,NC]
RewriteCond %%{HTTP_HOST} ^(?:%s)(?::[0-9]+)?$ [NC]
RewriteRule ^(?:index[.](?:php|html))?$ cli.html [L]
''' % patron


def genera(ctx):
    dat = estado(ctx,True)
    if not dat['media_verified']: raise ValueError('Verificar todos los archivos remotos antes de Generate.')
    from .checkstatus import fecha
    try:
        edad=(datetime.datetime.now(datetime.timezone.utc)-fecha(dat['media_verified_at'])).total_seconds()
    except (KeyError,TypeError,ValueError):edad=-1
    if not 0 <= edad <= ctx['settings'].get('checkstatus',{}).get('max_age_seconds',3600):
        raise ValueError('Verificación remota caducada o sin fecha; ejecutar verify de nuevo.')
    if dat.get('web'): raise ValueError('La web ya está generada para este inventario.')
    inv.comprueba_local(dat['inventory']['files'])
    web = ctx['root']/'web'
    if web.exists(): raise ValueError('Generación interrumpida conservada; utilizar otro --release-id.')
    # Generated reports use a private cache; the original download cache stays untouched.
    cache = ctx['root']/'generation-cache'
    cache.mkdir(parents=True,exist_ok=True)
    meta = ctx['cache']/'downloads.json'
    if meta.is_file(): shutil.copyfile(meta,cache/'downloads.json')
    # Bridge the verified release into the same observation contract as checkstatus.
    from .catalog_v8 import carga
    from .v8 import campos_absolutos
    from .checkstatus import comprueba
    from urllib.parse import quote
    cfg_gen=campos_absolutos(ctx['settings'],ctx['config'])
    cfg_gen['status_file']=str(ctx['root']/'status.json')
    arc_cfg=ctx['root']/'generation-config.json'
    guarda_json(arc_cfg,cfg_gen,0o600)
    url=ctx['settings']['targets']['bastion']['download_url'].rstrip('/')
    inv_rem={'status':'observed','via':'verified-release','errors':[],
             'files':[{'relative':e['relative'],'size':e['size'],'public_url':url+'/'+quote(e['relative'],safe='/')}
                      for e in dat['inventory']['files'] if not pagina(e['relative'])]}
    snapshot=comprueba(carga(config=arc_cfg),cfg_gen,arc_cfg,inventario_remoto=inv_rem)
    snapshot['checked_at']=dat['media_verified_at']
    guarda_json(cfg_gen['status_file'],snapshot,0o600)
    cmd = ['bash',str(DIR_APP/'generate.sh'),'--config',str(arc_cfg),'--target','bastion',
           '--input-root',str(ctx['root']/'input-view'),'--output',str(web),
           '--cache',str(cache),'--tec','link','--quiet']
    subprocess.run(cmd,check=True,env={**os.environ,'AUX_V8_LEGACY':'1'})
    for nom in ('index.php','index-aux.php'): (web/nom).unlink(missing_ok=True)
    (web/'.htaccess').write_text(apache(ctx['settings']))
    seo = ctx['settings']['targets']['excalibur']['base_url'].rstrip('/')
    aux = ctx['settings']['targets']['bastion']['base_url'].rstrip('/')
    for nom in ('workspace','installer','catalogue','systems'):
        arc = web/(nom+'.html')
        txt = arc.read_text().replace('property="og:url" content="'+aux+'/',
                                      'property="og:url" content="'+seo+'/')
        arc.write_text(txt)
    anterior = ctx['source']/'catalog.json'
    if anterior.is_file(): inv.compara_catalogos(json.loads(anterior.read_text()),json.loads((web/'catalog.json').read_text()))
    # Refuse a missing reviewed recipe rather than silently publishing a shorter menu.
    for ent in dat['inventory']['files']:
        if ent['relative'].startswith('origins/custom_') and not (web/ent['relative']).is_file():
            raise ValueError('Falta receta personalizada en Generate: '+ent['relative']+'; configurar catalog_profile.')
    items = []
    for arc in sorted(web.rglob('*')):
        if arc.is_symlink(): raise ValueError('Enlace inesperado en OUTPUT web.')
        if arc.is_file():
            rel = arc.relative_to(web).as_posix()
            if inv.privado(rel): raise ValueError('Archivo privado en OUTPUT web: '+rel)
            items.append(inv.elemento(arc,rel))
    inv.comprueba_local(dat['inventory']['files'])
    dat['web'] = {'files':items,'sha256':inv.huella(items),'files_count':len(items),
                  'bytes':sum(e['size'] for e in items)}
    dat['phase'] = 'generated'
    guarda(ctx,dat)
    return dat


def publica(ctx, secretos=None):
    dat = estado(ctx,True)
    if not dat.get('web') or not dat['media_verified']: raise ValueError('Falta web generada sobre medios verificados.')
    inv.comprueba_local(dat['inventory']['files'])
    previos = {e['relative']:e for e in dat['inventory']['files'] if pagina(e['relative'])}
    previos.update({e['relative']:e for e in dat['web']['files']})
    items = list(previos.values())
    # Transfer support pages first and entry points last; no remote deletion is issued.
    claves = {'index.html','cli.html','catalog.json','menu.ipxe'}
    for nom,vals in [('web-support',[e for e in items if e['relative'] not in claves]),
                     ('web-entry',[e for e in items if e['relative'] in claves])]:
        pth = ctx['root']/nom
        if not pth.exists(): inv.vista(vals,pth)
        net.envia(ctx['settings'],vals,pth,cfg.lee_secretos(secretos,ctx['config']))
    dat.update(published=True,final_verified=False,phase='published')
    guarda(ctx,dat)
    return dat
