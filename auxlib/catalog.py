# Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
# Author & Credits: https://www.alawise.es/1-s
"""Crawl configured official indices and atomically publish a versioned catalogue."""
import argparse
import datetime
import fcntl
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .common import CABECERA, atomico, guarda_json, identificador, suma


def url_segura(txt, hosts=None):
    if not isinstance(txt, str) or re.search(r'[\s\x00-\x1f\x7f;|]', txt):
        raise ValueError('URL con caracteres no permitidos.')
    dat = urllib.parse.urlsplit(txt)
    if (dat.scheme != 'https' or not dat.hostname or dat.username or dat.password or dat.fragment
            or (hosts is not None and dat.hostname not in hosts)):
        raise ValueError('Se requiere HTTPS en un host configurado: ' + txt)
    return txt


class Redireccion(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url_segura(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def consulta(url, hosts, cache, limite=8388608):
    url_segura(url, hosts)
    clave = hashlib.sha256(url.encode()).hexdigest()
    meta = cache / (clave + '.json')
    cuerpo = cache / (clave + '.body')
    dat = json.loads(meta.read_text()) if meta.exists() else {}
    hdr = {'User-Agent': 'AUX/7.0 (+https://www.alawise.es/1-s)'}
    if cuerpo.exists():
        if dat.get('etag'):
            hdr['If-None-Match'] = dat['etag']
        if dat.get('modified'):
            hdr['If-Modified-Since'] = dat['modified']
    req = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.build_opener(Redireccion(hosts)).open(req, timeout=30) as rsp:
            byt = rsp.read(limite + 1)
            if len(byt) > limite:
                raise ValueError('Índice demasiado grande.')
            atomico(cuerpo, byt)
            guarda_json(meta, {'etag': rsp.headers.get('ETag'), 'modified': rsp.headers.get('Last-Modified')})
            return byt
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and cuerpo.exists():
            return cuerpo.read_bytes()
        raise


class Enlaces(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for nom, val in attrs:
                if nom == 'href' and val:
                    self.urls.append(val)


def descubre(fuente, cache, traer=consulta):
    hosts = fuente['allowed_hosts']
    url = url_segura(fuente['url'], hosts)
    byt = traer(url, hosts, cache)
    if fuente['format'] == 'fedora-releases':
        from .catalog_sources import fedora
        return fedora(fuente,byt)
    if fuente['format'] == 'netboot':
        from .catalog_sources import netboot
        indice = traer(url_segura(fuente['menu_index_url'],hosts),hosts,cache)
        readme = traer(url_segura(fuente['project_index_url'],hosts),hosts,cache) if fuente.get('project_index_url') else b''
        return netboot(fuente,byt,indice,readme)
    if fuente['format'] == 'json':
        dat = json.loads(byt)
        if not isinstance(dat, dict) or not isinstance(dat.get('entries'), list):
            raise ValueError('Fuente JSON: objeto con entries requerido.')
        return dat['entries']
    if fuente['format'] != 'html':
        raise ValueError('Adaptador admitido: html o json.')
    reg = re.compile(fuente['pattern'])
    hashes = {}
    if fuente.get('checksums_url'):
        sum_url = url_segura(fuente['checksums_url'], hosts)
        hashes = parsea_sumas(traer(sum_url, hosts, cache).decode('utf-8'))
    par = Enlaces()
    par.feed(byt.decode('utf-8'))
    sal = []
    vistos = set()
    for href in par.urls:
        dst = urllib.parse.urljoin(url, href)
        nom = urllib.parse.unquote(urllib.parse.urlsplit(dst).path.rsplit('/', 1)[-1])
        mat = reg.fullmatch(nom)
        if not mat:
            continue
        # Official listings may link the same artifact from both icon and text.
        if dst in vistos:
            continue
        vistos.add(dst)
        ent = dict(fuente['defaults'])
        ent.update({key: val for key, val in mat.groupdict().items() if val is not None})
        ent['original_url'] = url_segura(dst, hosts)
        ent['id'] = fuente['id'] + '-' + hashlib.sha256(dst.encode()).hexdigest()[:16]
        ent['source_index'] = url
        ent['allowed_hosts'] = hosts
        if fuente.get('checksums_url'):
            if nom not in hashes:
                raise ValueError('La suma publicada no contiene el candidato: ' + nom)
            ent['sha256'] = hashes[nom]
            ent['checksum_source'] = fuente['checksums_url']
            if fuente.get('release_from_checksum'):
                ent['release'] += '-' + hashes[nom][:12]
        sal.append(ent)
    if not sal:
        raise ValueError('El índice no produjo entradas; se conserva la publicación anterior: ' + url)
    return sal


def parsea_sumas(txt):
    hashes = {}
    for lin in txt.splitlines():
        mat = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?(.+)', lin.strip())
        fed = re.fullmatch(r'SHA256 \((.+)\) = ([a-fA-F0-9]{64})', lin.strip())
        if mat:
            nom, dig = mat[2], mat[1].lower()
        elif fed:
            nom, dig = fed[1], fed[2].lower()
        else:
            continue
        if nom in hashes and hashes[nom] != dig:
            raise ValueError('Sumas contradictorias para el mismo archivo: ' + nom)
        hashes[nom] = dig
    if not hashes:
        raise ValueError('El manifiesto no contiene sumas SHA-256 admitidas.')
    return hashes


def valida(ent):
    ent = dict(ent)
    identificador(ent['id'])
    for nom in ('family', 'release', 'architecture', 'kind'):
        if not isinstance(ent.get(nom), str) or not ent[nom] or len(ent[nom]) > 120 or any(ord(car) < 32 for car in ent[nom]):
            raise ValueError('Campo de catálogo inválido: ' + nom)
    if ent.get('download_class') not in ('light', 'heavy'):
        raise ValueError('La clase light/heavy se declara explícitamente por entrada.')
    url_segura(ent['original_url'], ent.get('allowed_hosts'))
    if ent.get('sha256') and not re.fullmatch('[a-fA-F0-9]{64}', ent['sha256']):
        raise ValueError('SHA-256 inválido.')
    ent.setdefault('verification', {})
    ent['verification'].setdefault('download_hash', 'not-checked')
    ent['verification'].setdefault('source_signature', 'not-checked')
    return ent


def identidad(ent):
    dat = {nom: ent.get(nom) for nom in ('id', 'release', 'architecture', 'original_url', 'sha256', 'boot')}
    return hashlib.sha256(json.dumps(dat, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def receta(ent, evidencia):
    pru = evidencia.get(ent['id'], {})
    if (pru.get('identity') != identidad(ent) or pru.get('deployed_urls') != 'passed'
            or not any(pru.get(nom) == 'passed' for nom in ('bios_boot', 'uefi_boot'))):
        return None
    boot = ent.get('boot', {})
    ker = url_segura(boot['kernel_url'])
    ini = url_segura(boot['initrd_url'])
    args = boot.get('kernel_args', [])
    if not isinstance(args, list) or any(not isinstance(val, str) or not re.fullmatch(r'[A-Za-z0-9_.,/:?=%+@-]+', val) for val in args):
        raise ValueError('Argumento de arranque no permitido.')
    return f"kernel {ker} {' '.join(args)}\ninitrd {ini}\nboot\n"


def descarga(ent, dst):
    if not ent.get('sha256'):
        raise ValueError('Descarga publicada requiere SHA-256 fijado: ' + ent['id'])
    hosts = ent.get('allowed_hosts') or [urllib.parse.urlsplit(ent['original_url']).hostname]
    req = urllib.request.Request(url_segura(ent['original_url'], hosts), headers={'User-Agent': 'AUX/7.0'})
    limite = int(ent.get('max_bytes', 17179869184))
    if not 0 < limite <= 68719476736:
        raise ValueError('Límite de descarga inválido.')
    cnt = 0
    dig = hashlib.sha256()
    with urllib.request.build_opener(Redireccion(hosts)).open(req, timeout=60) as rsp, dst.open('xb') as arc:
        if 'text/html' in rsp.headers.get('Content-Type', '').lower():
            raise ValueError('El servidor devolvió HTML en vez de una imagen.')
        for byt in iter(lambda: rsp.read(1048576), b''):
            cnt += len(byt)
            if cnt > limite:
                raise ValueError('Descarga excede su límite.')
            dig.update(byt)
            arc.write(byt)
        arc.flush()
        os.fsync(arc.fileno())
    if not cnt or dig.hexdigest() != ent['sha256'].lower():
        raise ValueError('Descarga incompleta o SHA-256 incorrecto.')
    ent['size_bytes'] = cnt
    ent['verification']['download_hash'] = 'passed'


def pagina(entradas):
    filas = []
    for ent in entradas:
        est = ent['verification'].get('download_hash', 'not-checked')
        cols = [ent[nom] for nom in ('family', 'release', 'architecture', 'kind', 'download_class')]
        filas.append('<tr><td><input type="checkbox" class="sel" data-clase="' + ent['download_class'] + '" value="' + escape(ent['original_url'],quote=True) + '"></td>' + ''.join('<td>' + escape(str(val)) + '</td>' for val in cols) +
                     '<td><a href="' + escape(ent['original_url'], quote=True) + '">Origen</a></td><td>' + escape(est) + '</td></tr>')
    return '''<!doctype html><!-- Timestamp: 2026-11-09 | Version: 7.0.0-beta.0 | Author & Credits: https://www.alawise.es/1-s -->
<html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AUX · Catálogo</title><style>body{font:16px system-ui;margin:2rem;background:#10121a;color:#eee}input{padding:.7rem;width:80%;max-width:40rem}table{border-collapse:collapse;width:100%;margin-top:1rem}td,th{text-align:left;padding:.6rem;border-bottom:1px solid #444}a{color:#8de}small{display:block;margin-top:1rem}</style>
<h1>AUX · Catálogo</h1><label>Filtrar distribución, versión, arquitectura o formato <input id="q" type="search"></label>
<p><button id="exp-light">Exportar selección light</button> <button id="exp-heavy">Exportar selección heavy</button></p>
<table><thead><tr><th>Elegir<th>Familia<th>Versión<th>Arquitectura<th>Formato<th>Clase<th>Descarga<th>SHA-256</thead><tbody>''' + ''.join(filas) + '''</tbody></table>
<small>El estado del hash y la prueba de arranque se registran por separado. Listas: <a href="light-url.txt">light</a> · <a href="heavy-url.txt">heavy</a> · <a href="catalog.json">JSON</a></small>
<script>/* Timestamp: 2026-11-09 | Version: 7.0.0-beta.0 | Author & Credits: https://www.alawise.es/1-s */
document.getElementById('q').addEventListener('input',function(){const bus=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(fil=>{fil.hidden=!fil.textContent.toLowerCase().includes(bus);});});
['light','heavy'].forEach(clase=>document.getElementById('exp-'+clase).addEventListener('click',()=>{const urls=Array.from(document.querySelectorAll('.sel:checked')).filter(ent=>ent.dataset.clase===clase).map(ent=>ent.value);const sys_url=URL.createObjectURL(new Blob([urls.join('\\n')+'\\n'],{type:'text/plain'}));const lnk=document.createElement('a');lnk.href=sys_url;lnk.download=clase+'-url.txt';lnk.click();URL.revokeObjectURL(sys_url);}));</script></html>'''


def politica_local(entradas, politica):
    if not isinstance(politica,dict) or politica.get('enabled') is not True:
        raise ValueError('La descarga local requiere storage.enabled=true y una selección limitada.')
    ids = politica.get('ids')
    cnt = politica.get('max_images')
    tam = politica.get('max_total_bytes')
    if (not isinstance(ids,list) or not ids or any(not isinstance(nom,str) for nom in ids)
            or not isinstance(cnt,int) or isinstance(cnt,bool) or cnt<1
            or not isinstance(tam,int) or isinstance(tam,bool) or tam<1):
        raise ValueError('Declarar storage.ids, max_images y max_total_bytes antes de descargar.')
    ids = set(ids)
    mapa = {ent['id']:ent for ent in entradas}
    if ids-set(mapa) or len(ids)>cnt:
        raise ValueError('Selección local ausente del catálogo o superior al límite de imágenes.')
    if any(mapa[nom].get('remote_only') or not mapa[nom].get('sha256') for nom in ids):
        raise ValueError('La selección local necesita imágenes con SHA-256; los menús externos son sólo enlaces.')
    return ids,cnt,tam


def copias_previas(destino):
    pth = destino/'current/catalog.json'
    sal = {}
    if pth.is_file():
        for ent in json.loads(pth.read_text()).get('entries',[]):
            rel = ent.get('local_path','')
            arc = destino/'current'/rel
            if (rel.startswith('downloads/') and arc.resolve().is_relative_to(destino.resolve())
                    and arc.is_file() and ent.get('sha256') and suma(arc)==ent['sha256']):
                sal[ent['sha256']] = (ent,arc.resolve())
    return sal


def espacio_usado(destino):
    # Hard-linked copies across metadata releases occupy storage only once.
    vistos = set()
    tam = 0
    for arc in (destino/'releases').glob('*/downloads/*'):
        if not arc.is_file():
            continue
        st = arc.stat()
        clave = (st.st_dev,st.st_ino)
        if clave not in vistos:
            vistos.add(clave)
            tam += st.st_size
    return len(vistos),tam


def publica(entradas, destino, evidencia=None, descargar=False, politica=None):
    destino = Path(destino).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    evidencia = evidencia or {}
    entradas = [valida(ent) for ent in entradas]
    if not entradas or len({ent['id'] for ent in entradas}) != len(entradas):
        raise ValueError('Se requieren entradas con identificadores únicos.')
    elegidos,max_img,max_byt = politica_local(entradas,politica) if descargar else (set(),0,0)
    with (destino / '.update.lock').open('a') as bloqueo:
        fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previas = copias_previas(destino)
        ids = {ent['id'] for ent in entradas}
        hashes = {ent.get('sha256') for ent in entradas}
        for sha,(ent,_) in previas.items():
            if sha not in hashes:
                ent = dict(ent,cached_previous=True)
                if ent['id'] in ids:
                    ent['id'] = ent['id'][:60]+'-cache-'+sha[:12]
                ent = valida(ent)
                if ent['id'] in ids:
                    raise ValueError('Identificador de copia local duplicado.')
                ids.add(ent['id'])
                entradas.append(ent)
        cnt_usado,byt_usado = espacio_usado(destino)
        ver = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
        versiones = destino / 'releases'
        versiones.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.staging-', dir=destino) as tmp:
            pth = Path(tmp)
            recetas = []
            for ent in entradas:
                previa = previas.get(ent.get('sha256'))
                if previa or ent['id'] in elegidos:
                    desc = pth / 'downloads' / (ent['id'] + Path(urllib.parse.urlsplit(ent['original_url']).path).suffix)
                    desc.parent.mkdir(exist_ok=True)
                    if previa:
                        os.link(previa[1],desc)
                        ent['verification']['download_hash'] = 'passed'
                    else:
                        restante = max_byt-byt_usado
                        if cnt_usado>=max_img or restante<1 or int(ent.get('size_bytes') or 0)>restante:
                            raise ValueError('El almacenamiento local alcanzó su límite; se conserva la publicación anterior.')
                        ent['max_bytes'] = min(int(ent.get('max_bytes',17179869184)),restante)
                        descarga(ent, desc)
                        cnt_usado += 1
                        byt_usado += desc.stat().st_size
                    ent['local_path'] = str(desc.relative_to(pth))
                else:
                    ent.pop('local_path',None)
                ent['identity'] = identidad(ent)
                txt = receta(ent, evidencia)
                if txt:
                    firm = '/'.join(nom.replace('_boot', '').upper() for nom in ('bios_boot', 'uefi_boot') if evidencia[ent['id']].get(nom) == 'passed')
                    recetas.append((ent['id'], firm, txt))
            menu = '#!ipxe\n# AUX: only explicitly verified boot recipes are emitted.\n'
            if recetas:
                menu += 'menu AUX - tested boot recipes\n'
                menu += ''.join('item ' + nom + ' ' + nom + ' (' + firm + ')\n' for nom, firm, _ in recetas)
                menu += 'item salida Exit\nchoose --default salida seleccion || goto salida\ngoto ${seleccion}\n'
                menu += ''.join(':' + nom + '\n' + txt + 'goto salida\n' for nom, _, txt in recetas)
            menu += ':salida\nexit\n'
            guarda_json(pth / 'catalog.json', {'version': ver, 'metadata_only_update':not descargar,
                                               'local_images':sum(bool(ent.get('local_path')) for ent in entradas),
                                               'entries': entradas})
            for clase in ('light', 'heavy'):
                atomico(pth / (clase + '-url.txt'), CABECERA + ''.join(ent['original_url'] + '\n' for ent in entradas if ent['download_class'] == clase and not ent.get('remote_only')))
            atomico(pth / 'menu.ipxe', menu)
            atomico(pth / 'index.html', pagina(entradas))
            final = versiones / ver
            pth.chmod(0o755)
            os.replace(pth, final)
        enlace = destino / ('.current-' + uuid.uuid4().hex)
        try:
            enlace.symlink_to('releases/' + ver)
            os.replace(enlace, destino / 'current')
        finally:
            enlace.unlink(missing_ok=True)
    return final


def actualiza(cfg):
    cfg.output.mkdir(parents=True, exist_ok=True)
    with (cfg.output / '.update-run.lock').open('a') as bloqueo:
        fcntl.flock(bloqueo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _actualiza(cfg)


def _actualiza(cfg):
    dat = json.loads(cfg.config.read_text())
    entradas = list(dat.get('entries', []))
    cfg.cache.mkdir(parents=True, exist_ok=True)
    # Fetch every configured source before changing the published catalogue.
    for fuente in dat.get('sources', []):
        entradas.extend(descubre(fuente, cfg.cache))
    if cfg.select:
        ids = set(cfg.select.split(','))
        if ids - {ent['id'] for ent in entradas}:
            raise ValueError('La selección contiene identificadores ausentes del catálogo.')
        entradas = [ent for ent in entradas if ent['id'] in ids]
    evidencia = json.loads(cfg.evidence.read_text()) if cfg.evidence else {}
    return publica(entradas, cfg.output, evidencia, cfg.download, dat.get('storage'))


def main(argv=None):
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--config', type=Path)
    par.add_argument('--output', type=Path)
    par.add_argument('--cache', type=Path, default=Path('/var/cache/aux-catalog'))
    par.add_argument('--evidence', type=Path)
    par.add_argument('--download', action='store_true')
    par.add_argument('--select', help='Comma-separated catalogue identifiers; defaults to all selected sources')
    par.add_argument('--interactive',action='store_true')
    from . import VERSION
    par.add_argument('--version',action='version',version='aux-catalog '+VERSION)
    cfg = par.parse_args(argv)
    if cfg.interactive:
        from .localtools import catalogo
        return catalogo()
    if not cfg.config or not cfg.output:
        par.error('Indicar --config y --output, o usar --interactive.')
    print(actualiza(cfg))
