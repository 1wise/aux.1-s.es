# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Observe files, remote inventories and login evidence without deploying anything."""
import argparse
import datetime
import ftplib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import ssl
import subprocess
import tempfile
import time
from urllib.parse import quote, urlsplit
import urllib.request

from .catalog_v8 import carga, ahora, huella, ruta_cfg, rel_segura, identidad, url_publica, ruta_publicada
from .common import guarda_json, suma
from .policy24 import LOCATIONS, combina
from .settings import lee_config, ruta_config, lee_secretos


def config_digest(cfg):
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fecha(txt):
    val = datetime.datetime.fromisoformat(txt)
    if val.tzinfo is None: raise ValueError('La fecha debe incluir zona horaria.')
    return val


def vigente(dat, cat, cfg):
    try:
        edad = (datetime.datetime.now(datetime.timezone.utc) - fecha(dat['checked_at'])).total_seconds()
        return (dat.get('schema') == 'aux-status-v1' and dat['catalog_sha256'] == huella(cat)
                and dat.get('configuration_sha256') == config_digest(cfg)
                and 0 <= edad <= cfg.get('checkstatus', {}).get('max_age_seconds', 3600))
    except (KeyError, TypeError, ValueError):
        return False


def _raiz(txt):
    if not isinstance(txt, str) or not txt.startswith('/') or '..' in txt.split('/') or re.search(r'[\x00-\x1f\x7f\\]', txt):
        raise ValueError('El directorio remoto debe ser absoluto y no contener .. ni controles.')
    return txt.rstrip('/') or '/'


def inventario_rsync(cfg, directorio, limites):
    from .mirror_transport import ssh_args
    ssh, host = ssh_args(cfg)
    with tempfile.TemporaryDirectory(prefix='aux-list-') as sys_tmp:
        cmd = ['rsync','--recursive','--dry-run','--itemize-changes','--protect-args',
               '--out-format=%i\t%l\t%n','-e',shlex.join(ssh),
               host+':'+_raiz(directorio).rstrip('/')+'/',sys_tmp+'/']
        # A dry-run only obtains metadata; it never copies a remote image here.
        with tempfile.TemporaryFile() as sys_out, tempfile.TemporaryFile() as sys_err:
            rsp = subprocess.run(cmd, stdout=sys_out, stderr=sys_err, timeout=limites['timeout_seconds'])
            if rsp.returncode: raise ValueError('Inventario rsync fallido (código '+str(rsp.returncode)+'); revisar acceso SSH, known_hosts y directorio. La contraseña requiere terminal y mirror.ssh_auth=auto o password.')
            if sys_out.tell() > limites['max_inventory_bytes']: raise ValueError('Inventario rsync demasiado grande.')
            sys_out.seek(0)
            sal = []
            for lin in sys_out.read().decode('utf-8').splitlines():
                par = lin.split('\t', 2)
                if len(par) != 3 or len(par[0]) != 11 or par[0][1] != 'f': continue
                rel = rel_segura(par[2])
                if len(PurePosixPath(rel).parts) > limites['max_depth']: raise ValueError('Inventario rsync demasiado profundo.')
                sal.append({'relative':rel,'size':int(par[1])})
                if len(sal) > limites['max_files']: raise ValueError('Demasiados archivos remotos.')
            return sal


def inventario_ftp(cfg, directorio, limites, sec=None):
    host, usr = cfg.get('ftp_host'), cfg.get('ftp_user')
    if not host or not usr: raise ValueError('Configurar ftp_host y ftp_user antes del inventario.')
    sec = sec or {}
    clave = sec.get('ftp_password') or os.environ.get('AUX_FTP_PASSWORD')
    if not clave: raise ValueError('Falta la credencial FTP en el almacén privado.')
    if cfg.get('ftp_tls', True):
        conn = ftplib.FTP_TLS(context=ssl.create_default_context(), timeout=limites['timeout_seconds'])
    else:
        conn = ftplib.FTP(timeout=limites['timeout_seconds'])
    raiz, sal, vistos = _raiz(directorio), [], set()
    ultimo = time.monotonic()
    def recorre(rel='', nivel=0):
        nonlocal ultimo
        if nivel > limites['max_depth']: raise ValueError('Inventario FTP demasiado profundo.')
        actual = raiz.rstrip('/')+'/'+rel
        if actual in vistos: return
        vistos.add(actual)
        if time.monotonic()-ultimo>=2:
            from .transfer_events import evento
            evento('bastion','INVENTORY',str(len(sal))+' archivos · '+str(len(vistos))+' directorios · '+actual)
            ultimo=time.monotonic()
        if len(vistos)>limites['max_files']:raise ValueError('Demasiados directorios FTP.')
        try:
            items = list(conn.mlsd(actual, facts=['type','size']))
        except ftplib.error_perm as exc:
            if not str(exc).startswith(('500','501','502','504')): raise
            # Older shared-hosting servers may expose only NLST and SIZE.
            conn.cwd(actual)
            items = []
            for val in conn.nlst():
                nom = PurePosixPath(val).name
                if nom in ('.','..'): continue
                try:
                    conn.voidcmd('TYPE I'); tam = conn.size(nom)
                except ftplib.error_perm:
                    tam = None
                items.append((nom, {'type':'file' if tam is not None else 'dir','size':str(tam or 0)}))
        if len(items)+len(sal) > limites['max_files']: raise ValueError('Demasiadas entradas FTP.')
        for nom, facts in items:
            if nom in ('.','..') or facts.get('type') in ('cdir','pdir'): continue
            if '/' in nom or nom.startswith('.') or facts.get('type') not in ('file','dir'): continue
            sub = rel_segura(str(PurePosixPath(rel)/nom))
            if facts['type'] == 'dir': recorre(sub, nivel+1)
            else:
                sal.append({'relative':sub,'size':int(facts.get('size','0'))})
                if len(sal) > limites['max_files']: raise ValueError('Demasiados archivos FTP.')
    try:
        conn.connect(host, int(cfg.get('ftp_port',21)))
        conn.login(usr, clave)
        if cfg.get('ftp_tls', True): conn.prot_p()
        conn.set_pasv(True)
        recorre()
        return sal
    except ftplib.all_errors:
        raise ValueError('No se pudo completar el inventario FTP; revisar acceso y directorios.') from None
    finally:
        conn.close()


def limites_check(cfg):
    ent = cfg.get('checkstatus', {})
    sal = {k:ent.get(k,v) for k,v in {'timeout_seconds':30,'max_files':100000,
           'max_depth':32,'max_inventory_bytes':16777216,'max_age_seconds':3600}.items()}
    for nom, val in sal.items():
        if type(val) is not int or val <= 0: raise ValueError('Límite checkstatus inválido: '+nom)
    return sal


def _ruta_ftp(cfg, ent):
    if ent.get('ftp_path'):return _raiz(ent['ftp_path'])
    raiz = cfg.get('mirror',{}).get('remote_root')
    pth = ent['path']
    if not raiz or not cfg.get('ftp_root'):
        raise ValueError('Indicar ftp_path para este directorio: SSH y FTP pueden tener raíces distintas.')
    raiz = _raiz(raiz)
    if pth != raiz and not pth.startswith(raiz.rstrip('/')+'/'):
        raise ValueError('El directorio no pertenece a mirror.remote_root; indicar su ftp_path.')
    return _raiz(cfg['ftp_root'].rstrip('/')+'/'+pth[len(raiz):].lstrip('/'))


def remoto(cfg, config=None):
    from .transfer_events import evento
    est = cfg.get('checkstatus', {}).get('bastion', {})
    if not est.get('enabled'):
        motivo = 'Bastion desactivado: B en el tablero permite activar el inventario con la conexión guardada.'
        evento('bastion','DISABLED',motivo)
        return {'status':'disabled','files':[],'errors':[],'reason':motivo}
    lim = limites_check(cfg); sal, errores, intentos, avisos = [], [], [], []
    transporte = est.get('transport', cfg.get('mirror',{}).get('transport','ftps'))
    if transporte == 'auto':
        transporte = 'rsync' if all(cfg.get('mirror',{}).get(k) for k in ('ssh_host','ssh_user')) else 'ftps' if cfg.get('ftp_tls',True) else 'ftp'
    directorios = est.get('directories', [])
    if not directorios:
        errores.append({'directory':None,'error':'Activar Bastion con B y revisar el directorio y su URL pública.'})
    for ent in directorios:
        ruta = ent.get('path'); modo = transporte
        try:
            _raiz(ruta); url_publica(ent['public_url'])
            evento('bastion','INVENTORY',modo+' · '+ruta)
            if modo == 'rsync':
                try:
                    filas = inventario_rsync(cfg, ruta, lim)
                    intentos.append({'transport':'rsync','directory':ruta,'status':'ok'})
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    intentos.append({'transport':'rsync','directory':ruta,'status':'error','error':str(exc)})
                    if not est.get('fallback_ftp',True) or not cfg.get('ftp_host') or not cfg.get('ftp_user'):raise
                    ruta = _ruta_ftp(cfg,ent)
                    modo = 'ftps' if cfg.get('ftp_tls',True) else 'ftp'
                    avisos.append({'directory':ent['path'],'error':str(exc),'fallback':modo})
                    evento('bastion','FALLBACK',modo+' configurado · '+ruta)
                    filas = inventario_ftp({**cfg,'ftp_tls':modo=='ftps'},ruta,lim,lee_secretos(config=config))
                    intentos.append({'transport':modo,'directory':ruta,'status':'ok'})
            elif modo in ('ftp','ftps'):
                filas = inventario_ftp({**cfg,'ftp_tls':modo=='ftps'},ruta,lim,lee_secretos(config=config))
                intentos.append({'transport':modo,'directory':ruta,'status':'ok'})
            else: raise ValueError('Inventario remoto: usar auto, rsync, ftp o ftps.')
            for fila in filas:
                fila.update(directory=ruta,transport=modo,public_url=ent['public_url'].rstrip('/')+'/'+quote(fila['relative'],safe='/'))
            sal.extend(filas)
            evento('bastion','INVENTORY',str(len(filas))+' archivos observados · '+modo)
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
            errores.append({'directory':ruta,'transport':modo,'error':str(exc)})
            evento('bastion','ERROR',str(exc))
    return {'status':'error' if errores else 'observed','files':sal,'errors':errores,'attempts':intentos,'warnings':avisos}


def local(pth, raices, esperado=None, verificar=False):
    try:
        esperado = esperado or {}
        arc = Path(pth)
        if not any(arc.resolve().is_relative_to(r.resolve()) for r in raices):
            return {'status':'error','error':'Enlace fuera de las raíces configuradas.'}
        if not arc.is_file(): return {'status':'absent'}
        tam = arc.stat().st_size
        if tam <= 0 or esperado.get('size_bytes') and tam != esperado['size_bytes']:
            return {'status':'invalid','size':tam,'error':'Tamaño vacío o distinto del catálogo.'}
        sal = {'status':'present','path':str(arc),'size':tam,'integrity':'not-checked'}
        if verificar:
            dig = suma(arc); sal['sha256'] = dig
            sal['integrity'] = 'matched' if esperado.get('sha256') == dig else 'unverified' if not esperado.get('sha256') else 'mismatch'
            if sal['integrity'] == 'mismatch': sal['status'] = 'invalid'
        return sal
    except OSError as exc:
        return {'status':'error','error':str(exc)}


def prueba(ent, evidencias):
    for ev in reversed(evidencias.get('entries', [])):
        if ev.get('resource_id') != ent['id'] or ev.get('identity') != identidad(ent): continue
        try:
            fecha(ev['recorded_at'])
            valido = (ev.get('result') == 'login-reached' and ent.get('sha256')
                      and suma(ev['log_path']) == ev.get('log_sha256'))
        except (OSError, KeyError, TypeError, ValueError): valido = False
        return {'status':'passed' if valido else 'invalid','evidence':ev}
    return {'status':'not-tested'}


def comprueba(cat, cfg, config=None, hash_archivos=False, probar_origen=False, inventario_remoto=None):
    # The release workflow may supply its already verified immutable remote inventory.
    remoto_dat = inventario_remoto if inventario_remoto is not None else remoto(cfg, config)
    arc_cfg = ruta_config(config)
    from .catalog_v8 import raiz_artefacto
    raices = {k:ruta_cfg(cfg, k, v, arc_cfg) for k,v in
              [('cache','../isos'),('output','../public'),('ram_dir','/dev/shm/aux-pxe')]}
    ev_path = ruta_cfg(cfg,'evidence_file','state/boot-evidence.json',arc_cfg)
    evidencias = json.loads(ev_path.read_text()) if ev_path.is_file() else {'entries':[]}
    anterior_path=ruta_cfg(cfg,'status_file','state/status.json',arc_cfg)
    anterior=json.loads(anterior_path.read_text()) if anterior_path.is_file() else {'entries':[]}
    anteriores={e['id']:e for e in anterior.get('entries',[])}
    filas = []
    for ent in cat['entries']:
        estados, disp = {}, 0
        for nom, clave in [('ram','ram_dir'),('ssd','output')]:
            rel = ruta_publicada(ent,nom)
            obs = local(raices[clave]/rel, list(raices.values()), ent, hash_archivos)
            if obs['status']=='absent' and not ent.get('paths',{}).get(nom):
                rel=ent['filename'];obs=local(raices[clave]/rel,list(raices.values()),ent,hash_archivos)
            if nom=='ssd' and obs['status']=='present' and Path(obs['path']).resolve().is_relative_to(raices['ram_dir'].resolve()):
                obs['status']='alias';obs['served_from']='ram'
            if obs['status'] == 'present':
                obs['public_url'] = cfg.get('pxe_url',cfg['base_url']).rstrip('/')+'/'+quote(rel,safe='/')
                disp |= LOCATIONS[nom]
            estados[nom] = obs
        cache = local(raices['cache']/raiz_artefacto(ent)/ent['filename'], list(raices.values()), ent, hash_archivos)
        # Existing v7 caches remain usable after migration without duplicating payload bytes.
        if cache['status'] == 'absent': cache = local(raices['cache']/ent['filename'], list(raices.values()), ent, hash_archivos)
        estados['cache'] = cache
        rel = ruta_publicada(ent,'bastion')
        mats = [e for e in remoto_dat['files'] if e['relative'] == rel]
        if not mats and not ent.get('paths',{}).get('bastion'):
            mats=[e for e in remoto_dat['files'] if e['relative']==ent['filename']]
        if not mats and not ent.get('paths',{}).get('bastion'):
            # Existing replicas may predate AUX's versioned resources/ layout.
            # A unique filename and expected size identify presence, never verified integrity.
            mats=[e for e in remoto_dat['files'] if PurePosixPath(e['relative']).name==ent['filename'] and
                  (not ent.get('size_bytes') or e['size']==ent['size_bytes'])]
        if len(mats) == 1 and (not ent.get('size_bytes') or ent['size_bytes'] == mats[0]['size']) and mats[0]['size'] > 0:
            estados['bastion'] = {'status':'present', **mats[0], 'integrity':'not-checked'}; disp |= 8
        else:
            estados['bastion'] = {'status':'unknown' if remoto_dat['status'] != 'observed' else 'ambiguous' if len(mats)>1 else 'absent'}
        estados['origin'] = {'status':'unknown'}
        if probar_origen:
            try:
                req=urllib.request.Request(url_publica(ent['original_url']), method='HEAD', headers={'User-Agent':'AUX/8.0'})
                with urllib.request.urlopen(req, timeout=limites_check(cfg)['timeout_seconds']) as rsp:
                    url_publica(rsp.url)
                    if rsp.status != 200: raise ValueError('El origen no confirmó el archivo completo.')
                    if ent['artifact_type'] not in ('menu','manifest') and 'text/html' in rsp.headers.get('Content-Type',''):
                        raise ValueError('El origen devuelve HTML en lugar del artefacto.')
                    tam=rsp.headers.get('Content-Length')
                    if tam and ent.get('size_bytes') and int(tam)!=ent['size_bytes']:
                        raise ValueError('El tamaño del origen difiere del catálogo.')
                    estados['origin']={'status':'present','public_url':ent['original_url'],'checked_at':ahora()}; disp |= 4
            except (OSError,ValueError) as exc:
                estados['origin']={'status':'unknown','error':str(exc)}
        fuente = cache['status'] == 'present' or any(estados[n]['status']=='present' for n in ('ram','ssd','bastion'))
        desplegada = any(estados[n]['status']=='present' for n in ('ram','ssd','bastion'))
        receta = bool(ent.get('recipe'))
        comprobada = prueba(ent, evidencias)
        previo=anteriores.get(ent['id'],{})
        if previo.get('identity')==ent['identity']:
            for nom,obs in estados.items():
                ant=previo.get('locations',{}).get(nom,{})
                if obs['status'] in ('unknown','error'):
                    ultimo=ant if ant.get('status')=='present' else ant.get('last_success')
                    if ultimo:obs['last_success']={**ultimo,'observed_at':previo.get('checked_at')}
        est = int(fuente) | (int(desplegada)<<1) | (int(receta)<<2) | (int(comprobada['status']=='passed')<<3)
        filas.append({'id':ent['id'],'identity':ent['identity'],'policy':ent['policy'],
                      'word24':combina(ent['policy'],disp,est,ent.get('priority','0')),'availability':disp,'state':est,
                      'locations':estados,'boot_test':comprobada,'checked_at':ahora()})
    return {'schema':'aux-status-v1','checked_at':ahora(),'catalog_sha256':huella(cat),
            'configuration_sha256':config_digest(cfg),'entries':filas,'remote_inventory':remoto_dat}


def registra(cat, cfg, recurso, log, entorno, firmware, config=None):
    ents = [e for e in cat['entries'] if e['id']==recurso]
    if len(ents)!=1: raise ValueError('Recurso desconocido.')
    ent=ents[0]
    if not ent.get('sha256'): raise ValueError('Fijar el SHA-256 del artefacto antes de registrar la prueba.')
    if not entorno or len(entorno)>300: raise ValueError('Indicar el entorno real de la prueba.')
    arc=Path(log).resolve(strict=True)
    if not arc.is_file() or arc.stat().st_size==0: raise ValueError('La prueba requiere un log no vacío.')
    pth=ruta_cfg(cfg,'evidence_file','state/boot-evidence.json',ruta_config(config))
    dat=json.loads(pth.read_text()) if pth.is_file() else {'schema':'aux-boot-evidence-v1','entries':[]}
    dat['entries'].append({'resource_id':ent['id'],'identity':ent['identity'],'result':'login-reached',
                          'recorded_at':ahora(),'environment':entorno,'firmware':firmware,
                          'log_path':str(arc),'log_sha256':suma(arc),'method':'operator-attestation'})
    guarda_json(pth,dat,0o600)


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--config'); par.add_argument('--catalog'); par.add_argument('--output')
    par.add_argument('--json',action='store_true'); par.add_argument('--hash',action='store_true',help='Read complete local artifacts and compare their hashes; does not boot them')
    par.add_argument('--origin',action='store_true',help='Probe configured upstream HTTP(S) URLs with HEAD')
    par.add_argument('--dry-run',action='store_true'); par.add_argument('-i','--interactive',action='store_true')
    par.add_argument('--resource',action='append',help='Filter displayed resources; the saved snapshot remains complete')
    par.add_argument('--show',action='store_true',help='Read the saved report without probes or writes')
    par.add_argument('--bastion',choices=['rsync','ftp','ftps'],help='Include Bastion using an existing connection and its configured root; does not change saved settings')
    par.add_argument('--record-test',metavar='RESOURCE'); par.add_argument('--log'); par.add_argument('--environment')
    par.add_argument('--firmware',choices=['bios','uefi'],default='uefi'); par.add_argument('--login-reached',action='store_true')
    par.add_argument('--apply',action='store_true')
    args=par.parse_args(argv)
    cfg=lee_config(args.config); cat=carga(args.catalog,args.config)
    if args.interactive:
        from .resource_board import interactivo
        return interactivo(args.config,args.catalog)
    if args.record_test:
        if not (args.apply and args.login_reached and args.log and args.environment):
            par.error('Registrar requiere --apply --login-reached --log y --environment; solo tras una prueba real.')
        registra(cat,cfg,args.record_test,args.log,args.environment,args.firmware,args.config)
        print('Evidencia registrada; ejecutar checkstatus para actualizar la instantánea.'); return 0
    cfg_remoto=cfg
    if args.bastion:
        from .bastion_status import activa
        cfg_remoto=activa(cfg,args.bastion)
    if args.dry_run:
        print(json.dumps({'operation':'checkstatus','resources':len(cat['entries']),
                          'remote':cfg_remoto.get('checkstatus',{}).get('bastion',{}),'writes':False},ensure_ascii=False));return 0
    archivo=args.output or ruta_cfg(cfg,'status_file','state/status.json',ruta_config(args.config))
    if args.show:
        reporte=json.loads(Path(archivo).read_text())
    else:
        from .transfer_events import evento
        evento('checkstatus','CONFIG',str(ruta_config(args.config)))
        inv_remoto=remoto(cfg_remoto,args.config) if args.bastion else None
        reporte=comprueba(cat,cfg,args.config,args.hash,args.origin,inventario_remoto=inv_remoto)
        guarda_json(archivo,reporte,0o600)
    if args.resource:
        reporte={**reporte,'entries':[e for e in reporte['entries'] if e['id'] in args.resource],'filtered_view':True}
    if args.json: print(json.dumps(reporte,ensure_ascii=False))
    else:
        inv=reporte['remote_inventory']
        print('BASTION: '+inv['status']+' · '+str(len(inv['files']))+' archivos remotos.')
        if inv.get('reason'):print(inv['reason'])
        for err in inv['errors']:print('BASTION ERROR ['+str(err.get('directory'))+'] '+err['error'])
        for ent in reporte['entries']: print(ent['word24']+'  '+ent['id']+'  boot='+ent['boot_test']['status'])
        if reporte['remote_inventory']['errors']: print('Inventario remoto incompleto; consultar los errores del informe.')
    return 1 if reporte['remote_inventory']['errors'] else 0
