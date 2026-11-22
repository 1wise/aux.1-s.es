# Timestamp: 2026-11-22 | Version: 8.0.0-beta.1
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
from concurrent.futures import ThreadPoolExecutor

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
    if args.command=='deploy': recursos=[e for e in recursos if set(acciones(e['policy'])['locations']) & {'ram','ssd','bastion'}]
    usos={'ram':0,'ssd':0,'bastion':0}; desconocidos=[]
    for ent in recursos:
        for nom in acciones(ent['policy'])['locations']:
            if nom in usos:
                if ent.get('size_bytes'):usos[nom]+=ent['size_bytes']
                else:desconocidos.append(ent['id']+':'+nom)
    limites={'ram':int(cfg.get('ram_budget_gib',28)*1024**3*(1-cfg.get('ram_reserve_percent',10)/100)),
             'ssd':int(cfg.get('ssd_budget_gib',100)*1024**3),
             'bastion':int(cfg.get('ssd_budget_gib',100)*1024**3)}
    return {'operation':args.command,'version':VERSION,'resources':[{'id':e['id'],'policy':e['policy'],
            'original_url':e['original_url'],'actions':acciones(e['policy'])} for e in recursos],
            'selected_bytes':usos,'budget_bytes':limites,'unknown_sizes':desconocidos,
            'over_budget':[n for n in usos if usos[n]>limites[n]],'writes':bool(args.apply and not args.dry_run)}


def descarga(ent,cfg,actualizar=False):
    if ent.get('resolved') is False or ent['artifact_type']=='manifest':raise ValueError('Resolver el artefacto antes de descargar: '+ent['id'])
    pth=ruta_cfg(cfg,'cache','../isos')/raiz_artefacto(ent)/ent['filename']
    pth.parent.mkdir(parents=True,exist_ok=True)
    if pth.is_file() and pth.stat().st_size and not actualizar:
        if ent.get('sha256') and suma(pth)!=ent['sha256']:raise ValueError('Hash de caché incorrecto: '+ent['id'])
        return pth
    if not ent.get('sha256'):
        raise ValueError('Resolver y fijar el checksum oficial antes de descargar: '+ent['id'])
    parcial=pth.with_name(pth.name+'.part'); cab=pth.with_name(pth.name+'.part.headers')
    cmd=['curl','--fail','--location','--show-error','--retry','2','--connect-timeout','20',
         '--proto','=http,https','--proto-redir','=http,https','--output',str(parcial),'--dump-header',str(cab)]
    if parcial.exists() and cab.exists():
        cabs=cab.read_text(errors='replace')
        val=re.findall(r'^(?:etag|last-modified):\s*(.+)$',cabs,re.I|re.M)
        if val:cmd+=['--continue-at','-','--header','If-Range: '+val[-1].strip()]
        else:parcial.unlink()
    elif parcial.exists():parcial.unlink()
    cmd += [ent['original_url']]
    rsp=subprocess.run(cmd,check=False)
    if rsp.returncode:raise ValueError('Transferencia interrumpida; se conserva el parcial para reanudar: '+ent['id'])
    if not parcial.is_file() or not parcial.stat().st_size or suma(parcial)!=ent['sha256']:
        parcial.unlink(missing_ok=True);raise ValueError('Checksum distinto del catálogo: '+ent['id'])
    if ent.get('size_bytes') and parcial.stat().st_size!=ent['size_bytes']:
        raise ValueError('Tamaño distinto del catálogo: '+ent['id'])
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
                        [('Ver recursos y política','show'),('Aplicar presets acumulables','preset'),('Editar política de un recurso','policy'),
                         ('Resolver fuentes/versiones (requiere red)','refresh'),('Asistencia GPT/Gemini','assist'),('Volver','back')]])
                    if opt=='back':return 0
                    if opt=='assist':
                        from .catalog_assist_ui import asistencia_interactiva
                        def guardar_ai(entradas,limites,recetas,fuentes,asistente,avisos):
                            cat=carga(args.catalog,args.config);por_id={e['id']:e for e in cat['entries']}
                            for entrada in entradas:
                                ent={**por_id.get(entrada['id'],{}),**entrada}
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
                    args.action='set-policy' if opt=='policy' else opt
                    if opt=='preset':args.presets=marca('Presets acumulables',[(x,x.title()) for x in ('alpine','fedora','debian','todos')],[])
                    if opt=='policy':
                        ents=carga(args.catalog,args.config)['entries']
                        args.resource=[elige('Recurso',[(e['id']+' | '+e['policy'],e['id']) for e in ents])]
                        args.policy=campo('Política CDE (3 hex); A/S se obtienen de checkstatus','004')
                    args.apply=opt!='show' and campo('Escribir APLICAR para guardar el cambio o consultar fuentes','')=='APLICAR'
                    if opt!='show' and not args.apply:continue
                else:
                    args.apply=False;args.dry_run=True
                    main(argumentos(args))
                    opt=elige('Plan de '+args.command,[('Ejecutar el plan revisado','apply'),('Volver','back')])
                    if opt=='back':return 0
                    args.apply=campo('Escribir EJECUTAR para aplicar','')=='EJECUTAR';args.dry_run=not args.apply
                    if not args.apply:continue
                main(argumentos(args))
                campo('Terminado. Enter vuelve a la misma pantalla')
            except (ValueError,OSError,subprocess.SubprocessError) as exc:
                campo('Acción detenida; corregir y reintentar',resumen=[str(exc)])


def argumentos(args):
    sal=[args.command]
    if args.action:sal.append(args.action)
    for nom in ('config','catalog','policy','output','input_root','target','only','mode','jobs'):
        if getattr(args,nom,None):sal+=['--'+nom.replace('_','-'),str(getattr(args,nom))]
    for nom in args.resource or []:sal+=['--resource',nom]
    for nom in args.presets or []:sal+=['--preset',nom]
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
    par.add_argument('--policy');par.add_argument('--preset',dest='presets',action='append',choices=['alpine','fedora','debian','todos'])
    par.add_argument('--apply',action='store_true');par.add_argument('--dry-run',action='store_true')
    par.add_argument('-i','--interactive',action='store_true');par.add_argument('--json',action='store_true')
    par.add_argument('--refresh',action='store_true');par.add_argument('--version',action='version',version=VERSION)
    par.add_argument('--commit',action='store_true',help='Commit only the updated catalogue and its SHA-256 in the configured local Git repository; never push')
    args=par.parse_args(argv)
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
        if args.action=='validate':print(f"{len(cat['entries'])} recursos válidos; catálogo único.");return 0
        if args.action in ('import','migrate'):
            if not args.input:par.error('import/migrate requiere --input.')
            from .catalog_v8 import importa
            nuevo=importa(args.input,cat)
            print(json.dumps({'before':len(cat['entries']),'after':len(nuevo['entries']),'apply_required':not args.apply}))
            if args.apply and not args.dry_run:guarda(arc,nuevo)
            return 0
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
                for ent in nuevo['entries']:
                    if sel & set(presets(ent)):
                        # Union presets add defaults; they do not reset manual policies.
                        num=int(ent['policy'],16)
                        key='origin_policy_bits' if ent.get('remote_only') else 'heavy_policy_bits' if ent.get('download_class')=='heavy' or ent.get('deploy_method')=='chroot' else 'light_policy_bits'
                        mask=cfg.get('presets',{}).get(key,{'origin_policy_bits':'004','heavy_policy_bits':'016','light_policy_bits':'015'}[key])
                        from .policy24 import politica
                        ent['policy']=f'{num | politica(mask):03X}'
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
        print(json.dumps(informe,ensure_ascii=False,indent=2));return 0
    if args.command=='generate':return genera(cfg,args)
    if informe['over_budget']:raise ValueError('Presupuesto excedido: '+', '.join(informe['over_budget']))
    if args.command=='deploy' and informe['unknown_sizes']:raise ValueError('Resolver tamaños antes de desplegar: '+', '.join(informe['unknown_sizes']))
    if args.command=='download':
        recursos=[e for e in elegidos(cat,args) if acciones(e['policy'])['download'] or acciones(e['policy'])['update']]
        # Each artifact has an isolated partial path; every worker failure is surfaced.
        with ThreadPoolExecutor(max_workers=cfg.get('jobs',4)) as exe:
            tareas=[exe.submit(descarga,e,cfg,args.refresh or acciones(e['policy'])['update']) for e in recursos]
            errores=[]
            for tarea in tareas:
                try:tarea.result()
                except Exception as exc:errores.append(str(exc))
        if errores:raise ValueError('; '.join(errores))
    for ent in elegidos(cat,args):
        act=acciones(ent['policy'])
        if args.command=='deploy':
            for dest in act['locations']:
                if dest=='origin':continue
                if args.action in ('ram','ssd','disk','bastion','ftp') and dest!={'disk':'ssd','ftp':'bastion'}.get(args.action,args.action):continue
                despliega(ent,cfg,dest,args)
    print('Fase terminada. Ejecutar aux checkstatus antes de generate.')
    return 0
