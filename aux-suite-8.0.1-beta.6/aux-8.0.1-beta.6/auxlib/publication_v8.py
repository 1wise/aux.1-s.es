# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
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
    for ent in cat['entries']:
        obs=mapa.get(ent['id'],{})
        # Only observations for these exact bytes may introduce replica URLs.
        ent=valida(ent)
        if obs.get('identity')!=ent['identity']:obs={}
        locations={nom:lugar for nom,lugar in obs.get('locations',{}).items()
                   if nom in ('ram','ssd','bastion') and lugar.get('status')=='present' and lugar.get('public_url')}
        from .catalog_v8 import ruta_publicada
        discovered=[r for r in recursos if r.get('filename')==ent['filename'] and
                    (len(por_archivo.get(ent['filename'],[]))==1 or r.get('sha256')==ent.get('sha256') or
                     r.get('path') in [ruta_publicada(ent,k) for k in ('ram','ssd')])]
        if not locations and not discovered:continue
        local=[r for r in discovered if r.get('published')]
        if not locations and not local:local=discovered[:1]
        rec=dict(local[0]) if local else metadata(ent['original_url'])
        downloads={nom:url_publica(lugar['public_url']) for nom,lugar in locations.items()}
        preferred=locations.get('bastion') or locations.get('ssd') or locations.get('ram',{})
        rec.update(id=ent['id'],catalog_id=ent['id'],url=ent['original_url'],policy=ent['policy'],
                   word24=obs.get('word24'),
                   size=ent.get('size_bytes') or preferred.get('size'),sha256=ent.get('sha256'))
        if downloads:rec['observed_downloads']=downloads
        if not local:
            from urllib.parse import urlsplit,unquote
            relative=preferred.get('relative') or unquote(urlsplit(preferred['public_url']).path).lstrip('/')
            rec.update(path=relative,published=True,remote_published=True,contents_ready=False,
                       status='remote-observed',pxe_ready=False,
                       pxe_reason='Replica observed; a separate boot recipe is required.')
        sal.append(rec)
        encontrados.update(id(r) for r in discovered)
    # Discovery itself supplies independent local-file evidence when no status match exists.
    sal.extend(r for r in recursos if id(r) not in encontrados)
    return sal


def menu_componentes(cat):
    from .catalog_profile import valida_receta
    from .remote_menu import rotulo
    lin=['#!ipxe','# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6',
         '# Author & Credits: https://www.alawise.es/1-s','isset ${menu_arch} || set menu_arch ${buildarch}',
         'iseq ${menu_arch} i386 && cpuid --ext 29 && set menu_arch x86_64 ||',':start','menu AUX / Components / exact origins']
    recetas=[]
    for ent in cat['entries']:
        raw=ent.get('recipe')
        if not raw or not raw.get('approved'):continue
        rec=valida_receta({k:v for k,v in raw.items() if k!='approved'})
        label='component_'+ent['id'].replace('.','_').replace('-','_')
        gate='iseq ${menu_arch} '+rec['architecture']
        if rec['firmware']!='any':gate+=' && iseq ${platform} '+('efi' if rec['firmware']=='uefi' else 'pcbios')
        lin.append(gate+' && item '+label+' '+rotulo(ent.get('name',ent['id'])+' / '+ent['release'])+' ||')
        recetas.append((label,rec,ent))
    lin+=['item exit Exit','choose target && goto ${target} || exit']
    for label,rec,ent in recetas:
        lin+=['',':'+label,'echo Origin: '+url_publica(ent['original_url'])]
        if rec['type']=='linux':
            lin+=['kernel '+rec['kernel_url']+' '+' '.join(rec['kernel_args'])+' || goto error',
                  'initrd '+rec['initrd_url']+' || goto error','boot || goto error']
        else:lin+=['chain --autofree '+rec['menu_url']+' || goto error']
        lin+=['goto start']
    lin+=[':exit','exit',':error','echo Component boot failed. Check the pinned recipe and network.','prompt Press a key to return...','goto start','']
    return '\n'.join(lin)


def extras(cfg):
    arc=Path(getattr(cfg,'catalog_file','') or '')
    if not arc.is_file():return
    cat=json.loads(arc.read_text())
    if cat.get('schema')!='aux-catalog-v8':return
    # Publish only public resource metadata. Full status contains private test log paths.
    (cfg.output/'catalog').mkdir(parents=True,exist_ok=True)
    public=json.loads(json.dumps(cat));links={r.get('catalog_id'):r.get('download_urls',{}) for r in getattr(cfg,'resources',[])}
    for ent in public['entries']:
        if links.get(ent['id']):ent['download_urls']=links[ent['id']]
    (cfg.output/'catalog/catalog.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
    (cfg.output/'components.ipxe').write_text(menu_componentes(cat))
    from .products import datos as productos
    (cfg.output/'products.json').write_text(json.dumps(productos(str(arc)),ensure_ascii=False,indent=2)+'\n')
    audit=arc.parent/'catalog.audit.json'
    if not audit.is_file():audit=Path(__file__).resolve().parents[1]/'config/catalog.audit.json'
    if audit.is_file():shutil.copyfile(audit,cfg.output/'catalog.audit.json')
    # Keep documentation available to text browsers without a JavaScript dependency.
    pth_doc=Path(__file__).resolve().parents[1]/'docs'
    temas=[('REMOTE-AUTH-8.0.1.md','Contraseñas y diagnóstico de Bastion'),('BASTION-CHECKSTATUS-8.0.1.md','Inventario de Bastion'),('DEPLOY-RECOVERY-8.0.1.md','Recuperación de tamaños antes del despliegue'),('BETA2-8.0.1.md','8.0.1-beta.6: tablero y precauciones'),('RED-ROBIN-8.md','Red Robin: precauciones y herramientas sensibles'),('BOARD-8.0.1.md','Tablero común de 24 casillas'),('MATRIOSHKA-8.0.1.md','8.0.1: cuatro entregas junto al Git'),('KERNEL-MODELER-8.md','Kernel Modeler: constructor y laboratorio'),('BETA8-8.md','Kernel Modeler: preset y destinos'),('BETA7-8.md','Conservar prioridad en actualizaciones'),('BETA6-8.md','Lotes, capacidad y enlaces de réplicas'),('BETA5-8.md','Descargas y verificación de integridad'),('BETA4-8.md','Corrección de rutas del catálogo'),('BETA3-8.md','Catálogo, matrioshka y self-assamblers'),('BETA2-8.md','Identidad, productos y GPT/Gemini'),('SCHEMA-8.md','24 bits y catálogo'),('OPERATIONS-8.md','Operación y migración'),
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
