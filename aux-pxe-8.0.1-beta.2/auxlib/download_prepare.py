# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
# Author & Credits: https://www.alawise.es/1-s
"""Resolve permitted, selected downloads before transferring their pinned bytes."""
import copy
from .catalog_v8 import acciones,refresca,ruta_cfg,raiz_artefacto
from .common import suma
from .arch_netboot import admite as arch_admite


def prepara_descargas(cat,cfg,args):
    from .transfer_events import evento,verifica
    nuevo=copy.deepcopy(cat);errores={}
    for i,ent in enumerate(nuevo['entries']):
        act=acciones(ent['policy'])
        if not (act['download'] or act['update']):continue
        if args.resource and ent['id'] not in args.resource:continue
        if args.only and args.only.lower() not in (ent['id']+' '+ent['filename']+' '+ent['family']).lower():continue
        if not act['resolve'] or not act['crawl_level']:continue
        referencias=ent['original_url']+' '+(ent.get('source_index') or '')
        mutable=arch_admite(ent['original_url']) or any(part in referencias for part in ('/current/','/current-','/weekly-builds/','/daily-builds/','/latest/','/latest-','/development/rawhide/','/edge/'))
        if ent.get('sha256') and ent.get('resolved') is not False and not mutable and not args.refresh and not act['update']:continue
        pth=ruta_cfg(cfg,'cache','../isos')/raiz_artefacto(ent)/ent['filename']
        if not args.refresh and not act['update'] and pth.is_file() and ent.get('sha256') and verifica(pth,ent)==ent['sha256']:continue
        evento(ent['id'],'RESOLVE','Consultar origen e integridad')
        try:
            nuevo['entries'][i]=refresca({**cat,'entries':[ent]},cfg,[ent['id']])['entries'][0]
        except Exception as exc:
            errores[ent['id']]='No se pudo resolver '+ent['id']+' antes de descargar: '+str(exc)
            evento(ent['id'],'SKIP',errores[ent['id']]+' · continuar con el lote')
    return nuevo,errores
