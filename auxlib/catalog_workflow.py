# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Share catalogue state and review URL-list changes before applying them."""
import json
from pathlib import Path
import re
from types import SimpleNamespace

from .common import DIR_APP, atomico


def rutas_catalogo():
    return SimpleNamespace(config=DIR_APP/'config/catalog.sources.json',
                           output=DIR_APP/'state/catalog', cache=DIR_APP/'state/catalog-http')


def archivo_catalogo(explicito=None):
    if explicito:
        return Path(explicito)
    for pth in (rutas_catalogo().output/'current/catalog.json',
                Path('/srv/aux/catalog/current/catalog.json')):
        if pth.is_file():
            return pth
    return None


def lee_catalogo(explicito=None):
    pth = archivo_catalogo(explicito)
    if pth is None:
        return []
    dat = json.loads(pth.read_text())
    if not isinstance(dat, dict) or not isinstance(dat.get('entries'), list):
        raise ValueError('El catálogo requiere una lista entries: '+str(pth))
    return dat['entries']


def plan_listas(config, catalogo, raiz=None):
    """Change only URL slots with an explicit, unique source mapping."""
    dat = json.loads(Path(config).read_text())
    if raiz is None:
        raiz=(Path(config).parent/dat['download_lists']['all']).resolve().parent if dat.get('download_lists',{}).get('all') else DIR_APP
    informe=Path(catalogo).parent.parent/'crawl-report.json'
    if not informe.is_file():informe=Path(catalogo).resolve().parent.parent.parent/'crawl-report.json'
    if dat.get('download_slots') and informe.is_file():
        inf=json.loads(informe.read_text())
        if not inf.get('complete') or inf.get('publication_complete') is False:
            raise ValueError('El último rastreo está incompleto; revisar su informe antes de sincronizar.')
        import hashlib
        if inf.get('configuration_sha256') and inf['configuration_sha256']!=hashlib.sha256(Path(config).read_bytes()).hexdigest():
            raise ValueError('La configuración cambió desde el rastreo; volver a rastrear antes de sincronizar.')
    ents = lee_catalogo(catalogo)
    cambios = []
    for nom in ('url.txt', 'light-url.txt', 'heavy-url.txt'):
        pth = raiz/nom
        txt = pth.read_text()
        lineas = txt.splitlines(keepends=True)
        for regla in dat.get('sync_rules', []):
            from .catalog_downloads import coincide
            if not any(coincide(lin.strip(),regla) for lin in lineas):continue
            candidatos = [ent for ent in ents if ent.get('source_id') == regla['source_id']]
            if not candidatos:
                raise ValueError('Rastrear primero la fuente: '+regla['source_id'])
            if len(candidatos) != 1:
                raise ValueError('La fuente no identifica una única imagen: '+regla['source_id'])
            from .catalog import url_segura
            url = url_segura(candidatos[0]['original_url'], candidatos[0].get('allowed_hosts'))
            lineas = [url+('\n' if lin.endswith('\n') else '') if coincide(lin.strip(),regla) else lin
                      for lin in lineas]
        nuevo = ''.join(lineas)
        if nuevo != txt:
            cambios.append((pth, txt, nuevo))
    return cambios


def aplica_listas(cambios):
    # Refuse to overwrite edits made after plan review. Keep an adjacent recovery copy.
    for pth, anterior, nuevo in cambios:
        if pth.read_text() != anterior:
            raise ValueError('La lista cambió desde la revisión: '+str(pth))
    for pth, anterior, nuevo in cambios:
        atomico(pth.with_name(pth.name+'.before-crawl'), anterior)
    aplicadas=[]
    try:
        for pth, anterior, nuevo in cambios:
            atomico(pth, nuevo)
            aplicadas.append((pth,anterior))
    except OSError:
        for pth,anterior in reversed(aplicadas):atomico(pth,anterior)
        raise


def lineas_informe(pth):
    dat=json.loads(Path(pth).read_text())
    res=[f'{dat["resolved"]}/{dat["total"]} descargas resueltas | HTTP: {dat["http_passed"]}/{dat["total"]}',
         'Versión resuelta y disponibilidad HTTP son comprobaciones distintas.']
    for ent in dat['resources']:
        http=ent.get('http',{});tam=ent.get('size_bytes')
        res.append(ent.get('slot_id',ent['previous_url'])+' | '+ent['status']+' | '+str(ent.get('release','?'))+
                   ' | '+(f'{tam/1024**2:.1f} MiB' if isinstance(tam,int) and tam>0 else 'tamaño desconocido')+
                   ' | HTTP '+http.get('http','sin comprobar'))
        if ent.get('error') or http.get('error'):res.append('  '+str(ent.get('error') or http['error']))
        for anterior in ent.get('unavailable_newer_versions',[]):
            res.append('  Versión anunciada no disponible: '+anterior['release']+' | '+anterior['error'])
    if dat.get('catalog_source_error'):res.append(str(dat['catalog_source_error']))
    return res


def muestra_informe(output=None):
    from .console_ui import aplicacion,campo
    pth=Path(output or rutas_catalogo().output)/'crawl-report.json'
    with aplicacion('AUX CATALOG / INFORME','configuracion'):
        campo('Resultado por descarga; Enter vuelve',resumen=lineas_informe(pth) if pth.is_file() else ['Todavía no hay un informe de rastreo.'])


def rastreo_interactivo(config=None, output=None, cache=None, url_file=None):
    from .catalog import actualiza
    from .console_ui import aplicacion, campo
    rutas = rutas_catalogo()
    with aplicacion('AUX CATALOG / RASTREAR', 'configuracion'):
        cfg = SimpleNamespace(config=Path(campo('Configuración de fuentes',config or rutas.config)).expanduser(),
                              output=Path(campo('Publicación de metadatos',output or rutas.output)).expanduser(),
                              cache=Path(campo('Caché HTTP',cache or rutas.cache)).expanduser(),
                              select=None,evidence=None,download=False)
        dat = json.loads(cfg.config.read_text())
        defecto=cfg.config.parent/dat.get('download_lists',{}).get('all','../url.txt')
        cfg.url_file=Path(campo('Lista de URL que se va a descargar',url_file or defecto)).expanduser().resolve() if dat.get('download_slots') else None
        cfg.succeeded=False
        resumen = ['Consultar índices y checksums; sin descargar imágenes.',
                   'Salida: '+str(cfg.output)] + [str(ent['id'])+' | '+ent['url'] for ent in dat.get('sources', [])]
        if campo('Escribir RASTREAR para consultar las fuentes',resumen=resumen) != 'RASTREAR':
            return None
        print('Rastreando fuentes oficiales; se conserva current si alguna falla.',flush=True)
        try:final = actualiza(cfg)
        except ValueError as exc:
            if (cfg.output/'crawl-report.json').is_file():
                campo('Rastreo incompleto; se conserva el catálogo anterior. Enter vuelve',resumen=[str(exc)]+lineas_informe(cfg.output/'crawl-report.json'))
                return cfg
            raise
        print('Catálogo actualizado:',final)
        resumen=lineas_informe(cfg.output/'crawl-report.json') if (cfg.output/'crawl-report.json').is_file() else [str(final)]
        campo('Rastreo terminado. Enter para volver',resumen=resumen)
        cfg.succeeded=True
        return cfg


def sincroniza_interactivo(config=None, catalogo=None):
    from .console_ui import aplicacion, campo
    config = Path(config or rutas_catalogo().config)
    catalogo = archivo_catalogo(catalogo)
    if catalogo is None:
        raise ValueError('Rastrear las fuentes antes de sincronizar las listas.')
    cambios = plan_listas(config,catalogo)
    import difflib
    resumen = [lin.rstrip('\n') for pth,ant,nue in cambios
               for lin in difflib.unified_diff(ant.splitlines(True),nue.splitlines(True),
                                               fromfile=str(pth),tofile=str(pth))]
    with aplicacion('AUX CATALOG / LISTAS','configuracion'):
        if not cambios:
            campo('Las listas ya coinciden. Enter para volver')
            return
        if campo('Escribir APLICAR para actualizar las listas',resumen=resumen) == 'APLICAR':
            aplica_listas(cambios)
