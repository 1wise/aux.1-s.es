# Timestamp: 2026-11-22 | Version: 8.0.0-beta.1
# Author & Credits: https://www.alawise.es/1-s
"""Join an observed remote inventory to the existing publisher without remote crawling."""
import json
from pathlib import Path
import re
import html
import shutil

from .catalog_v8 import carga, ruta_cfg, valida, url_publica


def une(recursos,cfg,metadata):
    arc=Path(getattr(cfg,'catalog_file','') or '')
    if not arc.is_file():return recursos
    cat=json.loads(arc.read_text())
    if cat.get('schema')!='aux-catalog-v8':return recursos
    pth=Path(getattr(cfg,'status_file','') or arc.parent/'state/status.json')
    est=json.loads(pth.read_text()) if pth.is_file() else {'entries':[]}
    mapa={e['id']:e for e in est['entries']}
    por_archivo={}
    for ent in cat['entries']:
        por_archivo.setdefault(ent['filename'],[]).append(ent)
    encontrados=set();sal=[]
    # A resource may have both RAM and SSD copies, but keeps one catalogue identity.
    recursos=sorted(recursos,key=lambda r:not r.get('contents_ready',False))
    for rec in recursos:
        candidatos=por_archivo.get(rec['filename'],[])
        if len(candidatos)!=1:
            sal.append(rec);continue
        ent=valida(candidatos[0])
        if ent['id'] in encontrados:continue
        encontrados.add(ent['id']);sal.append(rec)
        rec.update(id=ent['id'],catalog_id=ent['id'],url=ent['original_url'],policy=ent['policy'])
        obs=mapa.get(ent['id'],{})
        rec['word24']=obs.get('word24');rec['observed_downloads']={}
        for nom, lugar in obs.get('locations',{}).items():
            if nom in ('ram','ssd','bastion') and lugar.get('status')=='present' and lugar.get('public_url'):rec['observed_downloads'][nom]=lugar['public_url']
    for ent in cat['entries']:
        if ent['id'] in encontrados:continue
        obs=mapa.get(ent['id'],{});lugar=obs.get('locations',{}).get('bastion',{})
        if lugar.get('status')!='present':continue
        rec=metadata(ent['original_url'])
        rec.update(id=ent['id'],catalog_id=ent['id'],policy=ent['policy'],word24=obs['word24'],
                   path=lugar['relative'],published=True,remote_published=True,contents_ready=False,
                   size=lugar['size'],sha256=ent.get('sha256'),status='remote-observed',
                   observed_downloads={'bastion':url_publica(lugar['public_url'])},
                   pxe_ready=False,pxe_reason='Bastion inventory observed; a separate boot recipe is required.')
        sal.append(rec)
    return sal


def menu_componentes(cat):
    from .catalog_profile import valida_receta
    from .remote_menu import rotulo
    lin=['#!ipxe','# Timestamp: 2026-11-22 | Version: 8.0.0-beta.1',
         '# Author & Credits: https://www.alawise.es/1-s',':start','menu AUX / Components / exact origins']
    recetas=[]
    for ent in cat['entries']:
        raw=ent.get('recipe')
        if not raw or not raw.get('approved'):continue
        rec=valida_receta({k:v for k,v in raw.items() if k!='approved'})
        label='component_'+ent['id'].replace('.','_').replace('-','_')
        lin.append('item '+label+' '+rotulo(ent.get('name',ent['id'])+' / '+ent['release']))
        recetas.append((label,rec,ent))
    lin+=['item exit Exit','choose target && goto ${target} || exit']
    for label,rec,ent in recetas:
        lin+=['',':'+label,'echo Origin: '+url_publica(ent['original_url'])]
        if rec['type']=='linux':
            lin+=['kernel '+rec['kernel_url']+' '+' '.join(rec['kernel_args'])+' || goto error',
                  'initrd '+rec['initrd_url']+' || goto error','boot || goto error']
        else:lin+=['chain --autofree '+rec['menu_url']+' || goto error']
        lin+=['goto start']
    lin+=[':error','echo Component boot failed. Check the pinned recipe and network.','prompt Press a key to return...','goto start','']
    return '\n'.join(lin)


def extras(cfg):
    arc=Path(getattr(cfg,'catalog_file','') or '')
    if not arc.is_file():return
    cat=json.loads(arc.read_text())
    if cat.get('schema')!='aux-catalog-v8':return
    # Publish only public resource metadata. Full status contains private test log paths.
    (cfg.output/'catalog').mkdir(parents=True,exist_ok=True)
    (cfg.output/'catalog/catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
    (cfg.output/'components.ipxe').write_text(menu_componentes(cat))
    # Keep documentation available to text browsers without a JavaScript dependency.
    pth_doc=Path(__file__).resolve().parents[1]/'docs'
    temas=[('SCHEMA-8.md','24 bits y catálogo'),('OPERATIONS-8.md','Operación y migración'),
           ('NAVIGATION-8.md','Mapa de navegación y diagramas'),('CHECKLIST-8.md','Checklist de aceptación'),
           ('TESTING-8.md','Validación de la beta'),('CDN-8.md','Piloto CDN')]
    cuerpo=['<!doctype html><html lang="es"><meta charset="utf-8"><title>AUX 8 / Documentación</title>',
            '<h1>AUX 8 / Documentación</h1><nav><a href="index.html">AUX</a> | <a href="catalogue.html">Catálogo</a> | <a href="components.ipxe">Componentes iPXE</a></nav><ul>']
    (cfg.output/'docs').mkdir(exist_ok=True)
    for nom,tit in temas:
        if not (pth_doc/nom).is_file():continue
        shutil.copyfile(pth_doc/nom,cfg.output/'docs'/nom)
        cuerpo.append('<li><a href="#'+nom+'">'+tit+'</a> (<a href="docs/'+nom+'">Markdown</a>)</li>')
    cuerpo.append('</ul>')
    for nom,tit in temas:
        if not (pth_doc/nom).is_file():continue
        cuerpo.append('<section id="'+nom+'"><h2>'+tit+'</h2><pre style="white-space:pre-wrap">'+html.escape((pth_doc/nom).read_text())+'</pre></section>')
    cuerpo.append('</html>')
    (cfg.output/'documentation.html').write_text('\n'.join(cuerpo)+'\n')
    menu=cfg.output/'menu.ipxe'
    if menu.is_file():
        txt=menu.read_text()
        # Add a reachable entry without replacing the existing hierarchical menu.
        txt=txt.replace('item origin_menu ', 'item aux_components Components / pinned origins\nitem origin_menu ',1)
        txt+='\n:aux_components\nchain components.ipxe || goto error\ngoto start\n'
        menu.write_text(txt)
