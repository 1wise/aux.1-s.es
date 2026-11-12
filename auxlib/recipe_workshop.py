# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Give recipe proposals bounded public media paths and verify local HTTP assets."""
import copy
import ipaddress
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, quote
from urllib.request import build_opener, HTTPRedirectHandler, Request

from .common import DIR_APP


def lee_json(pth, limite=8388608):
    pth=Path(pth).expanduser()
    if pth.stat().st_size>limite:raise ValueError('JSON demasiado grande: '+str(pth))
    return json.loads(pth.read_text())


def normaliza_entrada(ent):
    from .catalog import url_segura
    url=ent.get('original_url',ent.get('url',''));url_segura(url)
    peso=ent.get('size_bytes',ent.get('size'))
    peso=peso if type(peso) is int and peso>0 else None
    modo=ent.get('selection_mode',ent.get('download_class','origin'))
    if modo not in ('light','heavy','origin') or not peso or ent.get('remote_only'):modo='origin'
    return {'id':ent['id'],'name':str(ent.get('name') or ent.get('filename') or ent['id']),
        'family':str(ent.get('family') or 'other'),'release':str(ent.get('release') or 'upstream'),
        'architecture':str(ent.get('architecture',ent.get('arch','unknown'))),
        'kind':str(ent.get('kind') or 'image'),'original_url':url,
        'download_class':ent.get('download_class') if ent.get('download_class') in ('light','heavy') else 'heavy',
        'selection_mode':modo,'size_bytes':peso,'sha256':ent.get('sha256'),
        'remote_only':bool(ent.get('remote_only'))}


def carga_taller(catalogo=None,seleccion=None):
    from .catalog_profile import carga_perfil,url_receta
    cfg=lee_json(DIR_APP/'fast-boot.json');perfil=carga_perfil()
    raiz=Path(cfg.get('output','/var/www/aux.1-s.es/html')).expanduser()
    if not raiz.is_absolute():raiz=DIR_APP/raiz
    publicado=lee_json(catalogo or raiz/'catalog.json')
    if not isinstance(publicado,dict) or not isinstance(publicado.get('resources'),list):
        raise ValueError('El taller necesita catalog.json generado con resources.')
    pth_sel=Path(seleccion) if seleccion else DIR_APP/'aux-seleccion/aux-catalog-selection.json'
    base=lee_json(pth_sel)['entries'] if seleccion or pth_sel.is_file() else perfil['entries'] if perfil else [r for r in publicado['resources'] if r.get('format')!='TREE' and urlsplit(r.get('url','')).scheme=='https']
    if not isinstance(base,list) or len(base)>1000:raise ValueError('Selección de recetas inválida.')
    entradas=[normaliza_entrada(e) for e in base]
    limites=perfil['limits'] if perfil else {'ram_gib':cfg.get('ram_budget_gib',28),
        'ssd_gib':cfg.get('ssd_budget_gib',100),'reserve_percent':cfg.get('ram_reserve_percent',10)}
    fuentes=perfil['sources'] if perfil else []
    ids={e['id'] for e in entradas}
    recetas=[copy.deepcopy(r) for r in perfil['recipes'] if r['recipe']['entry_id'] in ids] if perfil else []
    # Only public deployment fields leave this process; configuration and server paths stay local.
    locales={r.get('url'):r for r in publicado['resources'] if r.get('published')}
    bases=[url_receta(str(cfg.get('pxe_url','http://pxe.1-s.es'))).rstrip('/')]
    if cfg.get('live_url'):bases.append(url_receta(str(cfg['live_url'])).rstrip('/'))
    live=publicado.get('live_url')
    if isinstance(live,str):
        part=urlsplit(live)
        try:
            ip=ipaddress.ip_address(part.hostname)
            publica=ip.version==4 and ip.is_global and not ip.is_multicast and not ip.is_reserved
        except ValueError:publica=False
        if (part.scheme=='http' and publica and part.port in (None,80) and not part.username
                and not part.password and not part.query and not part.fragment and not part.path.rstrip('/')):
            bases.append(live.rstrip('/'))
    bases=list(dict.fromkeys(bases))
    resumen=[];activos={};directorios={}
    permitidas=[raiz.resolve()]
    for key,defecto in [('ram_dir','/dev/shm/aux-fast-boot'),('cache','/var/www/aux.1-s.es/isos')]:
        pth=Path(cfg.get(key,defecto)).expanduser()
        permitidas.append((pth if pth.is_absolute() else DIR_APP/pth).resolve())
    for ent in sorted(entradas,key=lambda e:bool(locales.get(e['original_url'],{}).get('pxe_ready'))):
        rec=locales.get(ent['original_url'])
        if not rec or len(resumen)>=40:continue
        rel=Path(rec.get('tree',''))
        if not rel.parts or rel.is_absolute() or '..' in rel.parts:continue
        arbol=raiz/rel
        if not arbol.is_dir() or not any(arbol.resolve().is_relative_to(p) for p in permitidas):continue
        archivos=[];revisados=0
        for carpeta,dirs,nombres in os.walk(arbol,followlinks=False):
            dirs[:]=sorted(n for n in dirs if not (Path(carpeta)/n).is_symlink())
            revisados+=len(nombres)+1
            for nom in sorted(nombres):
                if not (re.match(r'(?i)(vmlinuz|linux$|bzimage|kernel|gentoo(?:\.igz)?$|initrd|initram|modloop)',nom)
                        or nom in ('.treeinfo','filesystem.squashfs','squashfs.img','install.img','airootfs.sfs','airootfs.erofs')):continue
                arc=Path(carpeta)/nom
                if arc.is_symlink() or not arc.is_file() or not arc.stat().st_size:continue
                if not arc.resolve().is_relative_to(arbol.resolve()):continue
                ruta=arc.relative_to(raiz).as_posix()
                urls=[b+'/'+quote(ruta,safe='/') for b in bases]
                for url in urls:activos[url]={'entry_id':ent['id'],'size':arc.stat().st_size}
                archivos.append({'url':urls[0],'size_bytes':arc.stat().st_size})
                if len(archivos)>=12:break
            if len(archivos)>=12 or revisados>=5000:break
        for base_url in bases:directorios[base_url+'/'+quote(rel.as_posix(),safe='/')+'/']=ent['id']
        resumen.append({'entry_id':ent['id'],'name':ent['name'],'architecture':ent['architecture'],
            'recipe_files_found':bool(rec.get('pxe_ready')),'reason':str(rec.get('pxe_reason') or '')[:300],
            'files':archivos,'tree_url':bases[0]+'/'+quote(rel.as_posix(),safe='/')+'/'})
    extra={'mode':'recipes','request_rules':'Return recipes only; sources must be empty. Preserve all storage choices. Propose at most 8 recipes. Use the exact entry IDs and media paths. Recipes are candidates, never hardware certifications.',
           'local_media':resumen,'live_url':live if isinstance(live,str) and live.rstrip('/') in bases else None}
    while len(json.dumps(extra).encode())>60000 and extra['local_media']:extra['local_media'].pop()
    return {'entries':entradas,'limits':limites,'sources':fuentes,'recipes':recetas,
            'context':extra,'assets':activos,'directories':directorios,'bases':bases}


class SinRedireccion(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise HTTPError(req.full_url,code,'Recipe HTTP redirect requires review',headers,fp)


def comprueba_local(taller,receta,url,opener=None):
    """Allow HTTP only for known public files of this entry at configured mirror bases."""
    if not any(url.startswith(base+'/') for base in taller['bases']):return False
    dato=taller['assets'].get(url)
    directorio=taller['directories'].get(url)
    if (dato or {}).get('entry_id',directorio)!=receta['entry_id']:
        raise ValueError('La receta mezcla medios o usa una ruta local no inventariada.')
    if not dato and url in (receta['kernel_url'],receta['initrd_url']):
        raise ValueError('Kernel e initrd deben ser archivos del inventario.')
    cliente=opener or build_opener(SinRedireccion())
    try:
        with cliente.open(Request(url,method='HEAD'),timeout=20) as rsp:
            if rsp.status not in (200,206):raise ValueError('Recurso local HTTP no disponible.')
            peso=rsp.headers.get('Content-Length')
            if dato and peso and int(peso)!=dato['size']:raise ValueError('El tamaño HTTP no coincide con el archivo publicado.')
    except (HTTPError,URLError,OSError,ValueError) as exc:
        raise ValueError('Fallo de comprobación del recurso local: '+str(exc)) from None
    return True


def valida_solo_recetas(propuesta,entradas):
    from .catalog_assist import valida_propuesta
    ids={e['id'] for e in entradas}
    if propuesta.get('sources'):raise ValueError('El taller de recetas no añade fuentes ni cambia almacenamiento.')
    nueva=copy.deepcopy(propuesta)
    if len(nueva.get('recipes',[]))>8:raise ValueError('Preparar un máximo de ocho recetas por consulta.')
    modos={e['id']:e['selection_mode'] for e in entradas}
    for ent in nueva.get('selection',[]):
        if ent['entry_id'] not in ids or ent['mode']!=modos[ent['entry_id']]:raise ValueError('La propuesta intentó cambiar la selección de almacenamiento.')
    nueva['selection']=[{'entry_id':e['id'],'mode':e['selection_mode'],'reason':'Existing selection preserved'} for e in entradas]
    return valida_propuesta(nueva,entradas)


def combina_recetas(anteriores,nuevas):
    mapa={r['recipe']['entry_id']:copy.deepcopy(r) for r in anteriores}
    mapa.update({r['recipe']['entry_id']:copy.deepcopy(r) for r in nuevas})
    return list(mapa.values())
