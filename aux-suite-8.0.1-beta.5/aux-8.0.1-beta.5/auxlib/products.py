# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Expose the recipe book, CDE policies and audited origins as AUX's maintained products."""
import argparse
import html
import json
from pathlib import Path
from . import VERSION
from .catalog_v8 import carga
from .common import DIR_APP,atomico,guarda_json
from .status_view import reciente

POLITICAS=[{'id':'netinstall-ram','name':'Netinstall ligero / RAM + origen','policy':'E15','description':'Crawler 2, candidato PXE y resolución; descargar; RAM y origen.'},
           {'id':'installer-ssd','name':'Instalador persistente / SSD + origen','policy':'E16','description':'Crawler 2, candidato PXE y resolución; descargar; SSD y origen.'},
           {'id':'origin-only','name':'Origen / sin almacenamiento local','policy':'E04','description':'Investigar y resolver la fuente; conservar sólo la referencia de origen.'},
           {'id':'bastion-copy','name':'Réplica de descarga / Bastion + origen','policy':'E1C','description':'Descargar y preparar Bastion como destino independiente, conservando el origen.'}]


def datos(catalog_file=None,audit_file=None):
    base=Path(catalog_file).parent if catalog_file else DIR_APP
    raw=json.loads(Path(catalog_file).read_text()) if catalog_file else None
    cat=carga(catalog_file) if raw is None or raw.get('schema')=='aux-catalog-v8' else {'entries':[]}
    pth=Path(audit_file) if audit_file else base/'catalog.audit.json'
    if not pth.is_file():pth=DIR_APP/'config/catalog.audit.json'
    audit=json.loads(pth.read_text()) if pth.is_file() else {};checks={e['id']:e for e in audit.get('entries',[])}
    recetas=[];urls=[]
    for ent in cat['entries']:
        chk=checks.get(ent['id'],{});valid=chk.get('original_url')==ent['original_url'] and chk.get('verified') and reciente(chk.get('checked_at'))
        if valid:urls.append({'id':ent['id'],'name':ent.get('name',ent['id']),'url':ent['original_url'],'final_url':chk.get('final_url'),'release':ent['release'],'architecture':ent['architecture'],'checked_at':chk['checked_at'],'http_status':chk.get('http_status'),'sha256':ent.get('sha256'),'integrity':'not-checked'})
        if ent.get('recipe_owner')!='AUX':continue
        rec=ent.get('recipe');cmd=''
        if rec:
            from .catalog_profile import valida_receta
            r=valida_receta({k:v for k,v in rec.items() if k!='approved'})
            cmd='#!ipxe\nkernel '+r['kernel_url']+' '+' '.join(r['kernel_args'])+'\ninitrd '+r['initrd_url']+'\nboot\n'
        else:cmd='./aux catalog refresh --resource '+ent['id']+' --apply\n./aux catalog set-policy --resource '+ent['id']+' --policy A14 --apply\n./aux download --resource '+ent['id']+' --apply\n'
        recetas.append({'id':ent['id'],'title':ent.get('name',ent['id']),'family':ent['family'],'release':ent['release'],'architecture':ent['architecture'],
                        'method':'ipxe' if rec else 'chroot','menu_ready':bool(rec and rec.get('approved')),'boot_test':'not-tested','notes':ent.get('recipe_notes',''),
                        'commands':cmd,'original_url':ent['original_url'],'procedure_url':ent.get('procedure_url'),'components':ent.get('components',[]),'url_verified':bool(valid),'checked_at':chk.get('checked_at')})
    cfg=json.loads((DIR_APP/'fast-boot.json').read_text());targets=cfg.get('targets',{});mirrors=[]
    for id in ('excalibur','bastion'):
        if id in targets:mirrors.append({'id':id,'url':targets[id]['base_url'],'downloads':targets[id].get('download_url'),'inventory_status':'not-checked','description':'Disponibilidad de cada artefacto según checkstatus; un servidor web accesible no acredita su réplica.'})
    return {'schema':'aux-products-v1','version':VERSION,'updated_at':audit.get('checked_at'),'maintenance':{'cadence':'weekly','next_due':audit.get('next_due'),'scope':'URL, fuentes y metadatos; los arranques requieren pruebas separadas.'},
            'recipes':recetas,'policies':POLITICAS,'urls':urls,'url_summary':audit.get('summary',{}),'mirrors':mirrors}


def publica_fuentes(dat):
    guarda_json(DIR_APP/'config/products.aux.json',dat)
    head='// Timestamp: 2026-11-22 | Version: '+VERSION+'\n// Author & Credits: https://www.alawise.es/1-s\n// Generated from the canonical catalogue and its audit; edit those sources.\n'
    atomico(DIR_APP/'tec/forum/products.mjs',head+'export const products = '+json.dumps(dat,ensure_ascii=False,indent=2)+';\n')
    for folder in ('tec/web','assist/web','iso-assist/tec/web'):
        if (DIR_APP/folder).is_dir():guarda_json(DIR_APP/folder/'products.aux.json',dat)


def contenido(nom,dat):
    esc=lambda s:html.escape(str(s or ''),quote=True)
    intro='<section class="hero"><p class="eyebrow">PRODUCTOS AUX / CONOCIMIENTO REPRODUCIBLE</p><h1>'+('El libro de recetas.' if nom=='recipes' else 'URL comprobadas y mirrors.')+'</h1><p>Recetas propias, catálogo y políticas CDE. Revisión de enlaces semanal con fecha y resultado visibles.</p><div class="actions"><a href="recipes.html">Recetas</a><a href="status.html">Estado / 24 bits / JSON</a><a href="urls.html">URL y mirrors</a><a href="menu.ipxe">menu.ipxe</a></div></section>'
    if nom=='recipes':
        for ent in dat['recipes']:
            intro+='<article class="panel"><h2>'+esc(ent['title'])+'</h2><p>'+esc(ent['release'])+' · '+esc(ent['architecture'])+' · '+esc(ent['method'])+'</p><p>'+esc(ent['notes'])+'</p><p>Prueba de arranque hasta login: pendiente. '+('Publicada en el menú iPXE.' if ent['menu_ready'] else 'Procedimiento o candidato pendiente de arranque.')+'</p><pre>'+esc(ent['commands'])+'</pre><p><a href="'+esc(ent['procedure_url'] or ent['original_url'])+'">Procedimiento oficial</a> · <a href="https://tec.1-s.es/forum.php?board=pxe&amp;new=1&amp;recipe='+esc(ent['id'])+'">Ampliar esta receta en el foro</a></p></article>'
    else:
        intro+='<section class="panel"><h2>Revisión HTTP</h2><p>'+esc(dat.get('updated_at') or 'Sin auditoría publicada')+' · '+str(len(dat['urls']))+' URL comprobadas. Una respuesta HTTP no demuestra un checksum ni un arranque.</p><p><a href="catalog.audit.json">Informe completo de comprobaciones</a> · <a href="products.json">Registro JSON de los tres productos</a></p></section><section class="panel"><h2>Referencias verificadas</h2><table><thead><tr><th>Recurso</th><th>Versión</th><th>Origen</th><th>Fecha HTTP</th></tr></thead><tbody>'
        for e in dat['urls']:intro+='<tr><td>'+esc(e['name'])+'</td><td>'+esc(e['release'])+'</td><td><a href="'+esc(e['url'])+'">'+esc(e['url'])+'</a></td><td>'+esc(e['checked_at'])+'</td></tr>'
        intro+='</tbody></table></section><section class="panel"><h2>Registro de mirrors</h2>'
        for m in dat['mirrors']:intro+='<h3><a href="'+esc(m['url'])+'">'+esc(m['id'])+'</a></h3><p>'+esc(m['description'])+'</p>'
        intro+='</section><section class="panel"><h2>Políticas de partida</h2>'
        for p in dat['policies']:intro+='<p><code>'+esc(p['policy'])+'</code> · '+esc(p['name'])+' · '+esc(p['description'])+'</p>'
        intro+='</section>'
    return intro


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--catalog');par.add_argument('--audit');par.add_argument('--apply',action='store_true');args=par.parse_args(argv)
    dat=datos(args.catalog,args.audit)
    if args.apply:publica_fuentes(dat)
    print(json.dumps({'recipes':len(dat['recipes']),'verified_urls':len(dat['urls']),'write':args.apply}));return 0


if __name__=='__main__':raise SystemExit(main())
