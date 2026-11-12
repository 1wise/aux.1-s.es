# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Inspect LVM metadata and temporarily activate one explicitly selected LV."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
import subprocess

CFG_DIS='devices { use_devicesfile=0 }'
TIPOS_SIMPLES={'linear','striped'}


def nombre(txt):
    if not isinstance(txt,str) or not re.fullmatch(r'[A-Za-z0-9+_][A-Za-z0-9+_.-]{0,126}',txt):
        raise ValueError('Nombre LVM inválido.')
    return txt


def identidad(txt):
    if not isinstance(txt,str) or not re.fullmatch(r'[A-Za-z0-9-]{20,64}',txt):
        raise ValueError('UUID LVM inválido.')
    return txt


def dispositivo(txt):
    pth=Path(txt).resolve()
    if not pth.is_relative_to('/dev') or ',' in str(pth) or not pth.is_block_device():
        raise ValueError('PV LVM ausente o inválido: '+str(pth))
    return str(pth)


def orden(cmd):
    res=subprocess.run(cmd,text=True,capture_output=True)
    if res.returncode:
        raise RuntimeError(cmd[0]+': '+(res.stderr or res.stdout)[-3000:])
    return res.stdout


def informe(exe,clave,campos,discos=None,selector=None,segmentos=False):
    cmd=[exe,'--reportformat','json','--units','b','--nosuffix','--options',campos,
         '--nohints','--config',CFG_DIS]
    if discos:cmd+=['--devices',','.join(discos)]
    if selector:cmd+=['--select',selector]
    if segmentos:cmd+=['--segments']
    dat=json.loads(orden(cmd));filas=[]
    if not isinstance(dat,dict) or not isinstance(dat.get('report'),list):raise ValueError('Informe LVM inválido.')
    for bloque in dat['report']:
        if not isinstance(bloque,dict):raise ValueError('Bloque LVM inválido.')
        for key in ((clave,) if isinstance(clave,str) else clave):
            valores=bloque.get(key,[])
            if not isinstance(valores,list):raise ValueError('Lista LVM inválida.')
            for ent in valores:
                if not isinstance(ent,dict):raise ValueError('Fila LVM inválida.')
                filas.append({nom:str(val).strip() if val is not None else '' for nom,val in ent.items()})
    return filas


def grupo(pv):
    pv=dispositivo(pv)
    pvs=informe('pvs','pv','pv_name,pv_uuid,vg_name,vg_uuid')
    sel=[ent for ent in pvs if ent.get('pv_name') and ent['pv_name']!='[unknown]'
         and str(Path(ent['pv_name']).resolve())==pv]
    if len(sel)!=1 or not sel[0].get('vg_uuid'):raise ValueError('El PV elegido no identifica un único grupo LVM.')
    uid=identidad(sel[0]['vg_uuid']);nom=nombre(sel[0]['vg_name'])
    miembros=[ent for ent in pvs if ent.get('vg_uuid')==uid]
    ids=[identidad(ent['pv_uuid']) for ent in miembros]
    if len(ids)!=len(set(ids)):raise ValueError('PVs duplicados: resolver la ambigüedad antes de activar.')
    discos=sorted({dispositivo(ent['pv_name']) for ent in miembros})
    vgs=informe('vgs','vg','vg_uuid,vg_name,vg_missing_pv_count',discos,'vg_uuid='+uid)
    if len(vgs)!=1 or vgs[0].get('vg_uuid')!=uid or vgs[0].get('vg_name')!=nom:
        raise ValueError('El grupo LVM cambió o es ambiguo.')
    if int(vgs[0].get('vg_missing_pv_count','-1'))!=0:
        raise ValueError('Faltan PVs del grupo; no se activa en modo parcial o degradado.')
    filas=informe('lvs',('lv','seg'),'vg_name,vg_uuid,lv_name,lv_uuid,lv_size,lv_active,segtype',
                  discos,'vg_uuid='+uid,True)
    lvs={}
    for ent in filas:
        if ent.get('vg_uuid')!=uid or ent.get('vg_name')!=nom:raise ValueError('LV ajeno al grupo seleccionado.')
        lv=nombre(ent['lv_name']);lid=identidad(ent['lv_uuid']);pth=str(Path('/dev')/nom/lv)
        nuevo={'name':lv,'uuid':lid,'path':pth,'size':ent.get('lv_size','?'),
               'active':ent.get('lv_active') in ('active','1','y','yes'),'segments':[]}
        if lid in lvs and any(lvs[lid][k]!=nuevo[k] for k in ('name','path','active')):
            raise ValueError('Identidad del LV inconsistente.')
        dato=lvs.setdefault(lid,nuevo)
        if ent['segtype'] not in dato['segments']:dato['segments'].append(ent['segtype'])
    return {'name':nom,'uuid':uid,'devices':discos,'volumes':sorted(lvs.values(),key=lambda ent:ent['name'])}


def elige_volumen(cfg,dat):
    valor=getattr(cfg,'lv',None)
    candidatos=dat['volumes']
    if valor:
        candidatos=[ent for ent in candidatos if valor in (ent['uuid'],ent['name'],dat['name']+'/'+ent['name'])]
        if len(candidatos)!=1:raise ValueError('El LV elegido no pertenece de forma única al grupo seleccionado.')
        return candidatos[0]
    if not candidatos:raise ValueError('El grupo no contiene volúmenes lógicos visibles.')
    if getattr(cfg,'interactive',False):
        from .interactive import elige
        return elige('Grupo LVM '+dat['name']+' / elegir volumen lógico',[
            (ent['name']+' | '+ent['size']+' bytes | '+('activo' if ent['active'] else 'inactivo')+
             ' | '+','.join(ent['segments']),ent) for ent in candidatos])
    if len(candidatos)==1:return candidatos[0]
    raise ValueError('Seleccionar --lv: '+', '.join(dat['name']+'/'+ent['name'] for ent in candidatos))


def comando(dat,ent,activar,escritura=False):
    if activar and (not set(ent['segments']) or not set(ent['segments'])<=TIPOS_SIMPLES):
        raise ValueError('La activación automática requiere segmentos linear/striped; seleccionar este LV una vez activado manualmente.')
    cfg=CFG_DIS
    if activar and not escritura:
        # Set device-mapper read-only activation without changing VG permission metadata.
        cfg+=' activation { read_only_volume_list='+json.dumps([dat['name']+'/'+ent['name']])+' }'
    cmd=['lvchange','--activate','y' if activar else 'n','--select','lv_uuid='+identidad(ent['uuid']),
         '--devices',','.join(dat['devices']),'--nohints','--config',cfg]
    if activar:cmd+=['--activationmode','complete','--monitor','n','--poll','n']
    return cmd


def verifica_mapeo(dat,ent,pth):
    # Duplicate VG names must never redirect an operation to another active mapping.
    esperado='LVM-'+dat['uuid'].replace('-','')+ent['uuid'].replace('-','')
    actual=orden(['dmsetup','info','--columns','--noheadings','-o','uuid',str(pth)]).strip()
    if actual!=esperado:raise RuntimeError('El mapeo activo no corresponde al UUID del LV seleccionado.')


@contextmanager
def activa(dat,ent,escritura=False):
    pth=Path(ent['path'])
    if ent['active']:
        if not pth.is_block_device():raise ValueError('LV declarado activo sin dispositivo disponible: '+str(pth))
        verifica_mapeo(dat,ent,pth)
        yield pth
        return
    if pth.exists():raise ValueError('El estado del LV cambió; revisar de nuevo antes de activar.')
    if not set(ent['segments']) or not set(ent['segments'])<=TIPOS_SIMPLES:
        raise ValueError('Activación automática disponible para LV linear/striped. Para '+
                         ','.join(ent['segments'])+' activar y revisar con las herramientas LVM antes de seleccionar el LV activo.')
    creado=False
    try:
        orden(comando(dat,ent,True,escritura));creado=True
        orden(['udevadm','settle','--timeout=10'])
        if not pth.is_block_device():raise RuntimeError('No apareció el dispositivo del LV activado: '+str(pth))
        verifica_mapeo(dat,ent,pth)
        ro=orden(['blockdev','--getro',str(pth)]).strip()
        if ro!=('0' if escritura else '1'):
            raise RuntimeError('El modo del dispositivo LVM no coincide con el solicitado.')
        yield pth
    finally:
        # Only close the selected LV that was inactive before this operation; never an entire VG.
        if creado or pth.is_block_device():orden(comando(dat,ent,False))
