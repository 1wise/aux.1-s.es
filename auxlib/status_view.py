# Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Project canonical policies and sanitized observations onto the same 20-bit view."""
import datetime
import json
from pathlib import Path
from .common import DIR_APP
from .catalog_v8 import identidad

GRUPOS=[('A','Disponibilidad',('Bastion','Origen','SSD','RAM')),('S','Estado',('Login','Receta','Deploy','Fuente')),
        ('C','Crawler',('Resolver','PXE','Crawl 2','Crawl 1')),('D','Descarga',('Archivar','Conservar','Actualizar','Descargar')),
        ('E','Destinos',('Bastion','Origen','SSD','RAM'))]
BITS=[{'bit':19-i*4-j,'group':g,'label':label,'readonly':i<2} for i,(g,_,labels) in enumerate(GRUPOS) for j,label in enumerate(labels)]


def reciente(fecha,dias=7):
    try:
        val=datetime.datetime.fromisoformat(fecha);age=(datetime.datetime.now(datetime.timezone.utc)-val).total_seconds()
        return 0<=age<=dias*86400
    except (ValueError,TypeError):return False


def datos(entradas,catalog_file=None):
    base=Path(catalog_file).parent if catalog_file else DIR_APP
    pth=base/'catalog.audit.json'
    if not pth.is_file():pth=DIR_APP/'config/catalog.audit.json'
    audit=json.loads(pth.read_text()) if pth.is_file() else {}
    checks={e['id']:e for e in audit.get('entries',[])}
    pth=base/'state/status.json';snap=json.loads(pth.read_text()) if pth.is_file() else {}
    prev={e['id']:e for e in snap.get('entries',[])};filas={}
    for ent in entradas:
        obs=prev.get(ent['id'],{});known=0;word=0
        if obs.get('identity')==identidad(ent) and reciente(snap.get('checked_at'),1/24):
            known=0xff000;word=(int(obs.get('availability',0))<<16)|(int(obs.get('state',0))<<12)
        # A recipe's existence is metadata; HTTP evidence never certifies an installer login.
        known|=1<<14
        if ent.get('recipe'):word|=1<<14
        check=checks.get(ent['id'],{})
        if check.get('original_url')==ent['original_url'] and reciente(check.get('checked_at')) and check.get('status') in ('reachable','missing','metadata-mismatch','unexpected-html'):
            known|=1<<18
            if check.get('verified'):word|=1<<18
            else:word&=~(1<<18)
        else:check={**check,'fresh':False}
        filas[ent['id']]={'word24':f"{word|int(ent.get('policy','004'),16):06X}",'known_observation_mask':f'{known:05X}',
                         'checked_at':obs.get('checked_at'),'url_check':check,
                         'locations':{k:{p:v for p,v in d.items() if p in ('status','public_url','relative','size','integrity','served_from')} for k,d in obs.get('locations',{}).items()},
                         'boot_test':{'status':obs.get('boot_test',{}).get('status','not-tested')}}
    return {'schema':'aux-status-public-v1','groups':[{'id':g,'label':label} for g,label,_ in GRUPOS],'bits':BITS,
            'audit':{k:audit.get(k) for k in ('checked_at','next_due','cadence','summary')},'entries':filas}


CONTENIDO='''<section class="hero"><p class="eyebrow">CATÁLOGO JSON / ESTADO / POLÍTICA</p><h1>Leer los bits. Revisar cada recurso.</h1><p>20 bits visibles: A y S describen observaciones; C, D y E definen la política editable. Los cuatro bits reservados permanecen en cero.</p><p>Una casilla con raya significa dato desconocido. «Login» necesita una prueba real del instalador hasta la pantalla de acceso.</p></section>
<section class="panel"><div class="actions"><a href="recipes.html" class="button">Libro de recetas</a><a href="urls.html" class="button secondary">URL y mirrors</a><a href="catalogue.html" class="button secondary">Presets del catálogo</a></div><p id="audit-summary"></p><label>Buscar un recurso<input id="status-search" type="search" placeholder="Distribución, versión, arquitectura o URL"></label><div class="actions"><button id="status-export" type="button">Descargar catalog.json</button><button id="status-snapshot" type="button" class="secondary">Descargar estado JSON</button><label class="button secondary">Cargar estado de checkstatus<input id="status-import" type="file" accept=".json,application/json"></label></div><p>El catálogo exportado contiene recursos y políticas. La instantánea conserva las observaciones por separado.</p></section>
<section id="status-rows" aria-label="Recursos y 20 bits"></section><button id="status-more" type="button">Mostrar más recursos</button>
<noscript><section class="panel"><p>La lectura de JSON y la edición de casillas requieren JavaScript. En consola: <code>aux checkstatus --show --json</code>. El contrato y la tabla completa de bits están en <a href="docs/SCHEMA-8.md">SCHEMA-8.md</a>.</p></section></noscript>'''
