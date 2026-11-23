# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Coordinate independent AUX 8 tasks using the canonical JSON catalogue."""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

from .common import DIR_APP, guarda_json, suma
from .catalog_v8 import (carga, guarda, ruta_cfg, ahora, acciones, valida, nombre,
                         huella, presets, raiz_artefacto, refresca, rel_segura)
from .catalog_v8 import ruta_publicada
from .settings import lee_config, ruta_config
from . import VERSION


def campos_absolutos(cfg, arc_cfg):
    dat=copy.deepcopy(cfg)
    for nom, defecto in [('output','../public'),('cache','../isos'),('ram_dir','/dev/shm/aux-pxe'),
                         ('catalog_file','catalog.json'),('status_file','state/status.json'),
                         ('evidence_file','state/boot-evidence.json'),('catalog_sources_file','config/catalog.sources.json')]:
        dat[nom]=str(ruta_cfg(cfg,nom,defecto,arc_cfg))
    return dat


def elegidos(cat, args, destino=None):
    sal=[]
    for ent in cat['entries']:
        if args.resource and ent['id'] not in args.resource: continue
        if args.only and args.only.lower() not in (ent['id']+' '+ent['filename']+' '+ent['family']).lower():continue
        if destino and destino not in acciones(ent['policy'])['locations']:continue
        sal.append(ent)
    return sal


def plan(cat,cfg,args):
    recursos=elegidos(cat,args)
    if args.command=='download': recursos=[e for e in recursos if acciones(e['policy'])['download'] or acciones(e['policy'])['update']]
    if args.command=='deploy':
        from .deploy_prepare import destinos
        recursos=[e for e in recursos if destinos(e,args)]
    from .capacity import prevision
    planning=cat.get('planning',{});cfg_plan={**cfg,'presets':dict(cfg.get('presets',{}))}
    for key in ('ram_budget_gib','ssd_budget_gib'):
        if key in planning:cfg_plan[key]=min(cfg.get(key,30 if key.startswith('ram') else 225),planning[key])
    for key in ('preset_ram_gib','preset_ssd_gib'):
        if key in planning:cfg_plan['presets'][key]=planning[key]
    cfg_plan['ssd_mode']=planning.get('ssd_mode','extract')
    forecast=prevision(recursos,cfg_plan,planning.get('presets',[]),getattr(args,'mode',None))
    return {**forecast,'operation':args.command,'version':VERSION,'resources':[{'id':e['id'],'policy':e['policy'],
            'original_url':e['original_url'],'actions':acciones(e['policy'])} for e in recursos],
            'writes':bool(args.apply and not args.dry_run)}


def descarga(ent,cfg,actualizar=False):
    from .transfer_events import evento,verifica,transfiere
    if ent.get('resolved') is False or ent['artifact_type']=='manifest':raise ValueError('Resolver el artefacto antes de descargar: '+ent['id'])
    if not ent.get('sha256'):raise ValueError('Resolver checksum o firma oficial antes de descargar: '+ent['id'])
    pth=ruta_cfg(cfg,'cache','../isos')/raiz_artefacto(ent)/ent['filename']
    pth.parent.mkdir(parents=True,exist_ok=True)
    if pth.is_file() and pth.stat().st_size and not actualizar:
        if verifica(pth,ent)!=ent['sha256']:raise ValueError('Hash de caché incorrecto: '+ent['id'])
        evento(ent['id'],'CACHE','Reutilizar archivo verificado')
        return pth
    from .precautions import protege
    partial=pth.with_name(pth.name+'.part')
    if ent.get('size_bytes'):protege(pth.parent,max(0,ent['size_bytes']-(partial.stat().st_size if partial.is_file() else 0)))
    parcial=pth.with_name(pth.name+'.part');cab=pth.with_name(pth.name+'.part.headers')
    # A complete, verified partial needs no new request, including after HTTP 416.
    if parcial.is_file() and (not ent.get('size_bytes') or parcial.stat().st_size==ent['size_bytes']) and verifica(parcial,ent)==ent['sha256']:
        os.replace(parcial,pth);cab.unlink(missing_ok=True);return pth
    if parcial.is_file() and ent.get('size_bytes') and parcial.stat().st_size>=ent['size_bytes']:
        parcial.unlink();cab.unlink(missing_ok=True)
    resume=[]
    if parcial.exists() and cab.exists():
        bloques=re.split(r'\r?\n\r?\n',cab.read_text(errors='replace'))
        ultimo=next((b for b in reversed(bloques) if b.startswith('HTTP/')),'')
        etag=re.search(r'^etag:\s*("[^"\r\n]+")\s*$',ultimo,re.I|re.M)
        modified=re.search(r'^last-modified:\s*([^\r\n]+)',ultimo,re.I|re.M)
        val=etag[1] if etag else modified[1].strip() if modified else None
        if val:resume=['--continue-at','-','--header','If-Range: '+val]
        else:parcial.unlink()
    elif parcial.exists():parcial.unlink()
    base=['curl','--fail','--location','--silent','--show-error','--retry','2','--connect-timeout','20',
          '--proto','=http,https','--proto-redir','=http,https','--output',str(parcial),'--dump-header',str(cab),'--write-out','%{http_code}']
    rsp=transfiere(base+resume+[ent['original_url']],parcial,ent)
    # Some mirrors ignore ranges. Restart once instead of preserving an unusable resume forever.
    if resume and (rsp.returncode in (33,36) or (rsp.stdout or '').strip()=='416'):
        parcial.unlink(missing_ok=True);cab.unlink(missing_ok=True)
        evento(ent['id'],'DOWNLOAD','El espejo rechazó el rango; reiniciar una vez')
        rsp=transfiere(base+[ent['original_url']],parcial,ent)
    if rsp.returncode:
        http=(rsp.stdout or '').strip();detalle=next((l for l in reversed((rsp.stderr or '').splitlines()) if l.startswith('curl:')),'sin detalle adicional')
        raise ValueError('Transferencia interrumpida: '+ent['id']+'; curl '+str(rsp.returncode)+(' / HTTP '+http if http.isdigit() else '')+'; '+detalle+'; se conserva el parcial disponible.')
    actual=verifica(parcial,ent) if parcial.is_file() else 'sin archivo'
    if not parcial.is_file() or not parcial.stat().st_size or actual!=ent['sha256']:
        parcial.unlink(missing_ok=True);cab.unlink(missing_ok=True)
        raise ValueError('Checksum distinto del catálogo: '+ent['id']+'; esperado '+ent['sha256']+'; recibido '+actual+'. No se publica; repetir download revalida los metadatos permitidos por C.')
    if ent.get('size_bytes') and parcial.stat().st_size!=ent['size_bytes']:raise ValueError('Tamaño distinto del catálogo: '+ent['id'])
    os.replace(parcial,pth);cab.unlink(missing_ok=True)
    return pth


def fuente_local(ent,cfg):
    cache=ruta_cfg(cfg,'cache','../isos')
    for pth in (cache/raiz_artefacto(ent)/ent['filename'],cache/ent['filename']):
        if pth.is_file() and pth.stat().st_size:
            if ent.get('sha256') and suma(pth)!=ent['sha256']:raise ValueError('Checksum de fuente incorrecto: '+ent['id'])
            return pth
    raise ValueError('No hay fuente local para '+ent['id']+'; descargar es una fase independiente.')


def despliega(ent,cfg,destino,args):
    src=fuente_local(ent,cfg)
    from .precautions import protege
    if destino!='bastion':protege(ruta_cfg(cfg,'output','../public'),ent.get('deployment_size_bytes') or src.stat().st_size,ram=destino=='ram')
    if destino=='bastion':
        from .mirror_transport import conecta_ftp, comando_rsync
        from .settings import lee_secretos
        rel=ruta_publicada(ent,'bastion')
        if cfg.get('mirror',{}).get('transport')=='rsync':
            with tempfile.TemporaryDirectory(prefix='aux-send-') as sys_tmp:
                pth=Path(sys_tmp)/rel;pth.parent.mkdir(parents=True,exist_ok=True);pth.symlink_to(src)
                cmd=comando_rsync(cfg,sys_tmp)
                subprocess.run(cmd[:1]+['--ignore-existing']+cmd[1:],check=True)
            return
        conn=conecta_ftp(cfg,lee_secretos(config=args.config))
        try:
            for nom in Path(rel).parts[:-1]:
                try:conn.cwd(nom)
                except Exception:
                    conn.mkd(nom);conn.cwd(nom)
            tmp='.aux-upload-'+ent['identity']+'.part'
            try:existente=conn.size(Path(rel).name)
            except Exception:existente=None
            if existente is not None:
                import hashlib
                dig=hashlib.sha256();conn.retrbinary('RETR '+Path(rel).name,dig.update)
                if existente==src.stat().st_size and dig.hexdigest()==suma(src):return
                raise ValueError('El destino remoto contiene otro artefacto; configurar una ruta de versión distinta.')
            try:pos=conn.size(tmp) or 0
            except Exception:pos=0
            if pos>src.stat().st_size:raise ValueError('Parcial remoto demasiado grande.')
            with src.open('rb') as arc:
                arc.seek(pos);conn.storbinary('STOR '+tmp,arc,blocksize=262144,rest=pos or None)
            if conn.size(tmp)!=src.stat().st_size:raise ValueError('Transferencia FTP incompleta.')
            conn.rename(tmp,Path(rel).name)
        finally:conn.close()
        return
    clave='output'
    raiz=ruta_cfg(cfg,clave,'../public')
    rel=ruta_publicada(ent,destino)
    pth=raiz/rel
    if not pth.resolve().is_relative_to(raiz.resolve()):raise ValueError('Destino fuera de la raíz configurada.')
    pth.parent.mkdir(parents=True,exist_ok=True)
    if ent['artifact_type']!='iso':
        if pth.exists() and suma(pth)!=suma(src):raise ValueError('El destino ya contiene otro artefacto; usar una ruta de versión distinta.')
        if not pth.exists():
            real=pth if destino!='ram' else ruta_cfg(cfg,'ram_dir','/dev/shm/aux-pxe')/rel
            real.parent.mkdir(parents=True,exist_ok=True)
            tmp=real.with_name('.'+real.name+'.aux-part');shutil.copyfile(src,tmp);os.replace(tmp,real)
            if destino=='ram':pth.symlink_to(real)
        return
    # Retain the reviewed ISO extractor/mounter instead of implementing a second one.
    with tempfile.TemporaryDirectory(prefix='aux-deploy-') as sys_tmp:
        privado=Path(sys_tmp); guarda_json(privado/'config.json',cfg)
        lista=privado/'input.txt';lista.write_text(ent['original_url']+'\n')
        cmd=['bash',str(DIR_APP/'deploy.sh'),'ram' if destino=='ram' else 'disk',
             '--config',str(privado/'config.json'),'--cache',str(src.parent),'--output',str(pth.parent),
             '--ram-dir',str(ruta_cfg(cfg,'ram_dir','/dev/shm/aux-pxe')/Path(rel).parent),'--url-file',str(lista)]
        if args.mode and destino=='ssd':cmd+=['--mode',args.mode]
        subprocess.run(cmd,check=True,env={**os.environ,'AUX_V8_LEGACY':'1'})


def genera(cfg,args):
    from .checkstatus import vigente
    cat=carga(args.catalog,args.config)
    arc=ruta_cfg(cfg,'status_file','state/status.json',ruta_config(args.config))
    est=json.loads(arc.read_text()) if arc.is_file() else {}
    if not vigente(est,cat,lee_config(args.config)):
        raise ValueError('Falta un status.json vigente para este catálogo/configuración. Ejecutar aux checkstatus antes de generate.')
    cmd=['bash',str(DIR_APP/'generate.sh'),'--config',str(ruta_config(args.config)),'--catalog-file',str(args.catalog or ruta_cfg(cfg,'catalog_file','catalog.json'))]
    print('GENERATE: inventario Bastion '+est.get('remote_inventory',{}).get('status','unknown')+'; '+str(sum(e.get('locations',{}).get('bastion',{}).get('status')=='present' for e in est.get('entries',[])))+' copias reconocidas.',flush=True)
    for nom in ('output','input_root','target','only'):
        if getattr(args,nom,None):cmd+=['--'+nom.replace('_','-'),getattr(args,nom)]
    return subprocess.run(cmd,env={**os.environ,'AUX_V8_LEGACY':'1'},check=False).returncode


def interactivo(args):
    from .console_ui import aplicacion,campo
    from .interactive import elige,marca
    with aplicacion('AUX '+args.command.upper(),'configuracion' if args.command=='catalog' else 'ejecucion'):
        while True:
            try:
                if args.command=='catalog':
                    opt=elige('Catálogo único: políticas, presets y fuentes',[(x,y) for x,y in
                        [('Tablero de 24 casillas y fases','board'),('Ver recursos y política','show'),('Aplicar presets acumulables','preset'),('Editar política de un recurso','policy'),('Editar prioridad P','priority'),
                         ('Resolver fuentes/versiones (requiere red)','refresh'),('Asistencia GPT/Gemini','assist'),('Previsión y presupuestos','capacity'),('Volver','back')]])
                    if opt=='back':return 0
                    if opt=='board':
                        from .resource_board import interactivo as tablero
                        tablero(args.config,args.catalog);continue
                    if opt=='capacity':
                        ajusta_capacidad(args);continue
                    if opt=='assist':
                        from .catalog_assist_ui import asistencia_interactiva
                        def guardar_ai(entradas,limites,recetas,fuentes,asistente,avisos):
                            cat=carga(args.catalog,args.config);por_id={e['id']:e for e in cat['entries']}
                            for entrada in entradas:
                                previous=por_id.get(entrada['id'],{});ent={**previous,**entrada}
                                # An assistant can suggest; it cannot invent user or mandatory preference.
                                ent['priority']=f"{int(previous.get('priority','0'),16)|8:X}"
                                ent['priority_sectors']=previous.get('priority_sectors') or presets(ent)
                                ent['policy']={'light':'E15','heavy':'E16','origin':'E04'}.get(ent.get('selection_mode'),'E04')
                                for rec in recetas:
                                    if rec['recipe']['entry_id']==ent['id']:
                                        ent['recipe']={**rec['recipe'],'approved':rec['approved'] and rec['http']=='passed'}
                                por_id[ent['id']]=valida(ent)
                            cfg=lee_config(args.config)
                            if campo('Escribir APLICAR para guardar la propuesta en catalog.json',resumen=list(avisos))!='APLICAR':return None
                            guarda(args.catalog or ruta_cfg(cfg,'catalog_file','catalog.json',ruta_config(args.config)),{**cat,'entries':list(por_id.values())})
                            return True
                        entradas=carga(args.catalog,args.config)['entries']
                        for ent in entradas:ent.setdefault('download_class','light' if int(ent['policy'],16)&1 else 'heavy')
                        asistencia_interactiva(entradas,guardar=guardar_ai);continue
                    args.action='set-policy' if opt=='policy' else 'set-priority' if opt=='priority' else opt
                    if opt=='preset':args.presets=marca('Presets acumulables',[(x,x.title()) for x in ('alpine','fedora','debian','todos')],[])
                    if opt=='priority':
                        ents=carga(args.catalog,args.config)['entries']
                        args.resource=[elige('Prioridad del recurso',[(e['id']+' | P='+e.get('priority','0'),e['id']) for e in ents])]
                        args.priority=campo('P: 1 usuario, 2 tendencia, 4 obligatorio, 8 IA para el sector','0')
                    if opt=='policy':
                        ents=carga(args.catalog,args.config)['entries']
                        args.resource=[elige('Recurso',[(e['id']+' | '+e['policy'],e['id']) for e in ents])]
                        args.policy=campo('Política CDE (3 hex); A/S se obtienen de checkstatus','004')
                    args.apply=opt!='show' and campo('Escribir APLICAR para guardar el cambio o consultar fuentes','')=='APLICAR'
                    if opt!='show' and not args.apply:continue
                else:
                    args.apply=False;args.dry_run=True
                    lines=ajusta_capacidad(args,editar=False)
                    opt=elige('Plan de '+args.command,[('Ejecutar el plan revisado','apply'),('Ajustar presupuestos','capacity'),('Tablero de 24 casillas','board'),('Volver','back')],detalles=[lines]*4)
                    if opt=='capacity':ajusta_capacidad(args);continue
                    if opt=='board':
                        from .resource_board import interactivo as tablero
                        tablero(args.config,args.catalog);continue
                    if opt=='catalog':main(['catalog','-i']+(['--config',args.config] if args.config else [])+(['--catalog',args.catalog] if args.catalog else []));continue
                    if opt=='back':return 0
                    args.apply=campo('Escribir EJECUTAR para aplicar','')=='EJECUTAR';args.dry_run=not args.apply
                    if not args.apply:continue
                main(argumentos(args))
                campo('Terminado. Enter vuelve a la misma pantalla')
            except (ValueError,OSError,subprocess.SubprocessError) as exc:
                campo('Acción detenida; corregir y reintentar',resumen=[str(exc)])


def ajusta_capacidad(args,editar=True):
    from .capacity import prevision,resumen
    from .console_ui import campo
    from .interactive import elige
    from .settings import establece,convierte,valor
    while True:
        cfg=lee_config(args.config);cat=carga(args.catalog,args.config)
        forecast=plan(cat,cfg,args)
        if not editar:return resumen(forecast)
        fields=['ram_budget_gib','ssd_budget_gib','ram_reserve_percent','presets.preset_ram_gib','presets.preset_ssd_gib']
        key=elige('Ajustar capacidad; Bastion = SSD',[(k,k) for k in fields]+[('Volver','back')],detalles=[resumen(forecast)]*(len(fields)+1))
        if key=='back':return
        default=10 if key.endswith('preset_ram_gib') else 75 if key.endswith('preset_ssd_gib') else 0
        txt=campo(key,str(valor(cfg,key,default)),validar=lambda v:convierte(key,v))
        establece(key,txt,args.config)


def argumentos(args):
    sal=[args.command]
    if args.action:sal.append(args.action)
    for nom in ('config','catalog','policy','output','input_root','target','only','mode','jobs','priority'):
        if getattr(args,nom,None):sal+=['--'+nom.replace('_','-'),str(getattr(args,nom))]
    for nom in args.resource or []:sal+=['--resource',nom]
    for nom in args.presets or []:sal+=['--preset',nom]
    for nom in getattr(args,'sectors',None) or []:sal+=['--sector',nom]
    if args.apply:sal.append('--apply')
    if args.dry_run:sal.append('--dry-run')
    return sal


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='checkstatus':
        from .checkstatus import main as status_main
        return status_main(argv[1:])
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('command',choices=['catalog','download','deploy','generate'])
    par.add_argument('action',nargs='?',default='show')
    par.add_argument('--config');par.add_argument('--catalog');par.add_argument('--resource',action='append')
    par.add_argument('--input',help='Previous JSON catalogue/selection or legacy URL list to import explicitly')
    par.add_argument('--only');par.add_argument('--output');par.add_argument('--cache');par.add_argument('--input-root')
    par.add_argument('--jobs',type=int,help='Parallel downloads, from 1 to 16; defaults to fast-boot.json')
    par.add_argument('--target');par.add_argument('--mode',choices=['mount','extract'])
    par.add_argument('--priority',help='One hex digit: 1 user, 2 sector trend, 4 mandatory, 8 AI sector suggestion')
    par.add_argument('--sector',dest='sectors',action='append',choices=['fedora','debian','alpine'])
    par.add_argument('--policy');par.add_argument('--preset',dest='presets',action='append',choices=['alpine','fedora','debian','todos'])
    par.add_argument('--apply',action='store_true');par.add_argument('--dry-run',action='store_true')
    par.add_argument('-i','--interactive',action='store_true');par.add_argument('--json',action='store_true')
    par.add_argument('--refresh',action='store_true');par.add_argument('--version',action='version',version=VERSION)
    par.add_argument('--commit',action='store_true',help='Commit only the updated catalogue and its SHA-256 in the configured local Git repository; never push')
    args=par.parse_args(argv)
    if args.command=='catalog' and args.action=='board':
        from .resource_board import interactivo as tablero
        return tablero(args.config,args.catalog)
    if args.interactive:return interactivo(args)
    cfg=campos_absolutos(lee_config(args.config),ruta_config(args.config))
    try:cat=carga(args.catalog,args.config)
    except FileNotFoundError:
        if args.command=='catalog' and args.action in ('import','migrate'):
            cat={'schema':'aux-catalog-v8','entries':[]}
        else:raise
    if args.output:cfg['output']=str(Path(args.output).expanduser().resolve())
    if args.cache:cfg['cache']=str(Path(args.cache).expanduser().resolve())
    if args.jobs is not None:cfg['jobs']=args.jobs
    if not isinstance(cfg.get('jobs',4),int) or not 1 <= cfg.get('jobs',4) <= 16:
        raise ValueError('jobs debe estar entre 1 y 16.')
    arc=Path(args.catalog) if args.catalog else Path(cfg['catalog_file'])
    if args.command=='catalog':
        if args.action=='audit':
            from .catalog_audit import audita
            if not args.apply or args.dry_run:print(json.dumps({'operation':'audit','network':False,'resources':len(cat['entries'])}));return 0
            dat=audita(cat,cfg.get('jobs',6));dest=Path(args.output) if args.output else arc.parent/'catalog.audit.json'
            guarda_json(dest,dat);print(json.dumps(dat['summary']));return 0
        if args.action=='validate':print(f"{len(cat['entries'])} recursos válidos; catálogo único.");return 0
        if args.action in ('import','migrate'):
            if not args.input:par.error('import/migrate requiere --input.')
            from .catalog_v8 import importa
            nuevo=importa(args.input,cat)
            print(json.dumps({'before':len(cat['entries']),'after':len(nuevo['entries']),'apply_required':not args.apply}))
            if args.apply and not args.dry_run:guarda(arc,nuevo)
            return 0
        if args.action=='set-priority':
            from .policy24 import numero
            if not args.priority or not args.resource:par.error('set-priority requiere --resource y --priority.')
            numero(args.priority,1);unknown=set(args.resource)-{e['id'] for e in cat['entries']}
            if unknown:raise ValueError('Recurso desconocido: '+', '.join(unknown))
            nuevo=copy.deepcopy(cat)
            for ent in nuevo['entries']:
                if ent['id'] in args.resource:
                    ent['priority']=args.priority.upper()
                    if args.sectors is not None:ent['priority_sectors']=sorted(set(args.sectors))
            if args.apply and not args.dry_run:guarda(arc,nuevo)
            print('Prioridad P actualizada.' if args.apply else 'Plan de prioridad P; usar --apply para guardar.');return 0
        if args.action in ('set-policy','preset'):
            nuevo=copy.deepcopy(cat)
            if args.action=='set-policy':
                if not args.policy or not args.resource:par.error('set-policy requiere --resource y --policy CDE.')
                from .policy24 import politica
                politica(args.policy)
                unknown=set(args.resource)-{e['id'] for e in cat['entries']}
                if unknown:raise ValueError('ID desconocido: '+', '.join(sorted(unknown)))
                for ent in nuevo['entries']:
                    if ent['id'] in args.resource:ent['policy']=args.policy.upper()
            else:
                sel=set(args.presets or [])
                if 'todos' in sel:sel={'alpine','fedora','debian'}
                if not sel:raise ValueError('Elegir al menos un preset.')
                from .capacity import propuesta
                base=[e for e in cat['entries'] if acciones(e['policy'])['download'] or acciones(e['policy'])['update']]
                choices,deferred=propuesta(cat['entries'],cfg,sel,base)
                choices={e['id']:e for e in choices}
                nuevo['entries']=[choices.get(e['id'],e) for e in nuevo['entries']]
                print('Solo origen por presupuesto: '+str(len(deferred)))
                nuevo['planning']={**nuevo.get('planning',{}),'presets':sorted(sel)}
                from .capacity import prevision,resumen
                print('\n'.join(resumen(prevision(nuevo['entries'],cfg,sorted(sel)))))
            print(json.dumps({'changes':[{'id':a['id'],'before':a['policy'],'after':b['policy']} for a,b in zip(cat['entries'],nuevo['entries']) if a['policy']!=b['policy']]},ensure_ascii=False))
            if args.apply and not args.dry_run:guarda(arc,nuevo)
            return 0
        if args.action=='refresh':
            if args.dry_run or not args.apply:
                print(json.dumps({'operation':'refresh','resources':len(elegidos(cat,args)),'network':False,'apply_required':True}));return 0
            repo=cfg.get('catalog_git_repository')
            if args.commit:
                if not repo or not arc.resolve().is_relative_to(Path(repo).resolve()):raise ValueError('Configurar catalog_git_repository con el catálogo dentro del repositorio.')
                subprocess.run(['git','-C',repo,'rev-parse','--show-toplevel'],check=True,stdout=subprocess.DEVNULL)
                for key in ('user.name','user.email'):
                    subprocess.run(['git','-C',repo,'config','--get',key],check=True,stdout=subprocess.DEVNULL)
            nuevo=refresca(cat,cfg,args.resource or ())
            guarda(arc,nuevo)
            if args.commit:
                rel=arc.resolve().relative_to(Path(repo).resolve()).as_posix()
                subprocess.run(['git','-C',repo,'add','--',rel,rel+'.sha256'],check=True)
                rsp=subprocess.run(['git','-C',repo,'diff','--cached','--quiet','--',rel,rel+'.sha256'])
                if rsp.returncode==1:
                    subprocess.run(['git','-C',repo,'commit','--only','-m','Update AUX catalogue and SHA-256','--',rel,rel+'.sha256'],check=True)
                elif rsp.returncode:raise ValueError('No se pudo revisar el cambio Git del catálogo.')
            print('Catálogo actualizado con SHA-256. Ejecutar checkstatus.');return 0
        if args.action!='show':raise ValueError('Acción de catálogo desconocida.')
        print(json.dumps(cat,ensure_ascii=False,indent=2) if args.json else '\n'.join(e['id']+' | '+e['policy']+' | '+e['original_url'] for e in elegidos(cat,args)))
        return 0
    informe=plan(cat,cfg,args)
    if args.dry_run or not args.apply:
        from .capacity import resumen
        print(json.dumps(informe,ensure_ascii=False,indent=2) if args.json else '\n'.join(resumen(informe)))
        return 0
    if args.command=='generate':return genera(cfg,args)
    errores_metadata=[]
    if args.command=='download':
        from .download_prepare import prepara_descargas
        cat,errores_metadata=prepara_descargas(cat,cfg,args)
        if cat!=carga(args.catalog,args.config):guarda(arc,cat)
        informe=plan(cat,cfg,args)
    if args.command=='deploy':
        from .deploy_prepare import prepara_despliegues
        cat,errores_metadata=prepara_despliegues(cat,cfg,{e['id'] for e in informe['resources']})
        if cat!=carga(args.catalog,args.config):guarda(arc,cat)
        informe=plan({**cat,'entries':[e for e in cat['entries'] if e['id'] not in errores_metadata]},cfg,args)
    from .precautions import lineas
    if args.command in ('download','deploy','generate'):print('\n'.join(lineas('load','writes')),file=sys.stderr)
    if informe['over_budget'] and args.command!='download':raise ValueError('Presupuesto excedido: '+', '.join(informe['over_budget']))
    if args.command=='download':
        recursos=[e for e in elegidos(cat,args) if (acciones(e['policy'])['download'] or acciones(e['policy'])['update']) and e['id'] not in errores_metadata]
        if informe['over_budget']:print('Aviso: despliegue previsto excede '+', '.join(informe['over_budget'])+'; revisar antes de deploy.',file=sys.stderr)
        from .policy24 import orden_prioridad
        recursos.sort(key=lambda e:orden_prioridad(e,cat.get('planning',{}).get('presets',[])))
        allowance=informe['budget_bytes']['ssd'];used=0;admitted=[]
        for ent in recursos:
            size=ent.get('size_bytes') or 0
            if used+size>allowance:errores_metadata[ent['id']]='Presupuesto de imágenes SSD excedido; ajustar la selección o el límite.'
            else:used+=size;admitted.append(ent)
        recursos=admitted
        from .transfer_events import evento
        resultados=[{'id':rid,'status':'error','stage':'budget' if msg.startswith('Presupuesto de imágenes') else 'resolve','error':msg} for rid,msg in errores_metadata.items()]
        with ThreadPoolExecutor(max_workers=cfg.get('jobs',4)) as exe:
            tareas={exe.submit(descarga,e,cfg,args.refresh or acciones(e['policy'])['update']):e for e in recursos}
            for tarea in as_completed(tareas):
                ent=tareas[tarea]
                try:
                    pth=tarea.result();resultados.append({'id':ent['id'],'status':'ok','stage':'verify','bytes':pth.stat().st_size,'sha256':ent['sha256']})
                    evento(ent['id'],'DONE','Descarga e integridad correctas')
                except Exception as exc:
                    resultados.append({'id':ent['id'],'status':'error','stage':'download','error':str(exc)})
                    evento(ent['id'],'ERROR',str(exc)+' · continuar con el lote')
        reporte={'schema':'aux-download-report-v1','version':VERSION,'finished_at':ahora(),
                 'ok':sum(r['status']=='ok' for r in resultados),'failed':sum(r['status']=='error' for r in resultados),'entries':resultados}
        pth=ruta_cfg(cfg,'status_file','state/status.json').parent/'download-report.json'
        guarda_json(pth,reporte,0o600)
        print(json.dumps(reporte,ensure_ascii=False,indent=2) if args.json else
              'DOWNLOAD terminado: '+str(reporte['ok'])+' correctas; '+str(reporte['failed'])+' errores. Informe: '+str(pth))
        if not args.json:
            for r in resultados:
                if r['status']=='error':print('ERROR ['+r['id']+'] '+r['error'])
        return 1 if reporte['failed'] else 0
    from .deploy_prepare import destinos
    from .transfer_events import evento
    resultados=[{'id':rid,'status':'error','stage':'resolve','error':msg} for rid,msg in errores_metadata.items()]
    for ent in elegidos(cat,args):
        if ent['id'] in errores_metadata:continue
        for dest in destinos(ent,args):
            try:
                evento(ent['id'],'DEPLOY',dest)
                despliega(ent,cfg,dest,args)
                resultados.append({'id':ent['id'],'destination':dest,'status':'ok','stage':'deploy'})
                evento(ent['id'],'DONE','Deploy correcto · '+dest)
            except Exception as exc:
                resultados.append({'id':ent['id'],'destination':dest,'status':'error','stage':'deploy','error':str(exc)})
                evento(ent['id'],'ERROR',str(exc)+' · continuar con el lote')
    reporte={'schema':'aux-deploy-report-v1','version':VERSION,'finished_at':ahora(),
             'ok':sum(r['status']=='ok' for r in resultados),'failed':sum(r['status']=='error' for r in resultados),'entries':resultados}
    pth=ruta_cfg(cfg,'status_file','state/status.json').parent/'deploy-report.json'
    guarda_json(pth,reporte,0o600)
    print(json.dumps(reporte,ensure_ascii=False,indent=2) if args.json else
          'DEPLOY terminado: '+str(reporte['ok'])+' destinos correctos; '+str(reporte['failed'])+' errores. Informe: '+str(pth))
    if not args.json:
        for r in resultados:
            if r['status']=='error':print('ERROR ['+r['id']+'] '+r['error'])
        print('Ejecutar aux checkstatus antes de generate.')
    return 1 if reporte['failed'] else 0
