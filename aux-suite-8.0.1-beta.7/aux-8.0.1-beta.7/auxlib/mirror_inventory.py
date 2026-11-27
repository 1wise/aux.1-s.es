# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Inventory public bytes without copying payloads or filtering by RAM/SSD class."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import os
import stat

from .common import suma, guarda_json

PAYLOADS = ('.iso','.img','.img.xz','.qcow2','.zip','.tar.gz','.efi','.kpxe','.pxe','.lkrn','.bin','.bzi')
PRIVADOS = {'.env','.ssh','.git','credentials.json','tecnicos.json','usuarios.json',
            'solicitudes.json','manage.php','bastion-manifest.json'}


def ruta_rel(txt):
    pth = PurePosixPath(txt)
    if not txt or pth.is_absolute() or str(pth) != txt or any(p in ('.','..') for p in pth.parts) or any(ord(c)<32 or ord(c)==127 for c in txt):
        raise ValueError('Ruta pública inválida: '+repr(txt))
    return txt


def privado(rel):
    partes = PurePosixPath(rel).parts
    return (rel == 'fast-boot.json' or any(p in PRIVADOS for p in partes) or partes[0] in ('tec','assist','cli','private','sessions','logs')
            or rel.lower().endswith(('.php','.phtml','.phar','.key','.secret')))


def sello(pth):
    st = Path(pth).stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def elemento(pth, rel):
    ruta_rel(rel)
    pth = Path(pth).resolve(strict=True)
    if not stat.S_ISREG(pth.stat().st_mode): raise ValueError('Archivo no regular: '+rel)
    antes = sello(pth)
    sha = suma(pth)
    if sello(pth) != antes: raise ValueError('Archivo modificado durante el inventario: '+rel)
    return {'relative':rel,'source':str(pth),'size':antes[2],'sha256':sha,'stat':antes}


def huella(items):
    dat = [{k:e[k] for k in ('relative','size','sha256')} for e in sorted(items,key=lambda e:e['relative'])]
    return hashlib.sha256(json.dumps(dat,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def comprueba_local(items, hashes=False):
    for ent in items:
        pth = Path(ent['source'])
        if sello(pth) != ent['stat'] or hashes and suma(pth) != ent['sha256']:
            raise ValueError('INPUT cambió; crear un inventario nuevo: '+ent['relative'])


def inventario(raiz, cache, ram, checksums=None):
    raiz, cache, ram = (Path(p).expanduser().resolve() for p in (raiz,cache,ram))
    if not raiz.is_dir() or not cache.is_dir(): raise ValueError('Falta el INPUT público o la caché original.')
    permitidas = (raiz,cache,ram)
    archivos, omitidos = {}, []
    def valida(pth):
        real = pth.resolve(strict=True)
        if not any(real.is_relative_to(r) for r in permitidas):
            raise ValueError('Enlace fuera de INPUT/caché/RAM: '+str(pth))
        return real
    def agrega(pth, rel):
        ent = elemento(valida(pth), rel)
        if rel in archivos and (ent['size'],ent['sha256']) != (archivos[rel]['size'],archivos[rel]['sha256']):
            raise ValueError('Colisión entre web y caché: '+rel)
        archivos.setdefault(rel,ent)
    def recorre(pth, rel='', antecesores=frozenset()):
        real = valida(pth)
        if real in antecesores: raise ValueError('Ciclo de enlaces en '+rel)
        for arc in sorted(pth.iterdir()):
            sub = (rel+'/' if rel else '')+arc.name
            ruta_rel(sub)
            if privado(sub) or arc.name.endswith(('.part','.tmp')) or arc.name == '.aux-rsync-partial':
                omitidos.append(sub); continue
            real_arc = valida(arc)
            if real_arc.is_dir(): recorre(arc,sub,antecesores|{real})
            elif real_arc.is_file(): agrega(arc,sub)
            else: raise ValueError('Entrada pública irregular: '+sub)
    recorre(raiz)
    # Cache metadata and selection classes never decide which existing image survives.
    for arc in sorted(cache.iterdir()):
        if arc.name.lower().endswith(PAYLOADS): agrega(arc,arc.name)
    esperados = {}
    if checksums:
        for linea in Path(checksums).read_text().splitlines():
            if not linea.strip() or linea.startswith('#'): continue
            sha, nom = linea.split(maxsplit=1)
            nom = nom.lstrip('* ')
            if len(sha)!=64 or any(c not in '0123456789abcdefABCDEF' for c in sha):
                raise ValueError('SHA-256 de proveedor inválido: '+nom)
            esperados[nom]=sha.lower()
    for nom, ent in archivos.items():
        sha = esperados.get(nom)
        if sha and sha != ent['sha256']: raise ValueError('Checksum de referencia no coincide: '+nom)
        ent['integrity'] = 'matches-configured-sha256' if sha else 'local-sha256-only'
    for arc in (cache/'tree-state').rglob('*.json') if (cache/'tree-state').is_dir() else []:
        est = json.loads(arc.read_text())
        if not est.get('tree') or not est.get('sha256'): continue
        pth = Path(est['tree'])
        if not pth.is_relative_to(raiz) or not pth.is_dir(): continue
        for ent in archivos.values():
            if Path(ent['source']).name == Path(est.get('source','')).name and ent['sha256'] != est['sha256']:
                raise ValueError('Árbol desplegado de otra imagen: '+str(pth))
    # A previously published local image must still exist, even if current lists omit it.
    cat = raiz/'catalog.json'
    if cat.is_file():
        for ent in json.loads(cat.read_text()).get('resources',[]):
            rel = ent.get('path') or ent.get('filename')
            if rel and rel.lower().endswith(PAYLOADS) and ent.get('published') and rel not in archivos:
                raise ValueError('Imagen anunciada pero ausente del INPUT y caché: '+rel)
    vals = sorted(archivos.values(),key=lambda e:e['relative'])
    return {'schema':'aux-mirror-v1','files':vals,'excluded_private':omitidos,
            'files_count':len(vals),'bytes':sum(e['size'] for e in vals),
            'iso_count':sum(e['relative'].lower().endswith('.iso') for e in vals),
            'sha256':huella(vals)}


def vista(items, destino):
    """Create pathname aliases only; rsync dereferences them into physical remote files."""
    destino = Path(destino)
    if destino.exists(): raise ValueError('La vista ya existe; utilizar otro identificador.')
    comprueba_local(items)
    destino.mkdir(parents=True)
    for ent in items:
        arc = destino/ruta_rel(ent['relative'])
        arc.parent.mkdir(parents=True,exist_ok=True)
        arc.symlink_to(ent['source'])


def valida_vista(items, destino):
    esperado = {e['relative']:e['source'] for e in items}
    vistos = set()
    for raiz, dirs, noms in os.walk(destino,followlinks=False):
        for nom in dirs:
            if (Path(raiz)/nom).is_symlink(): raise ValueError('Directorio enlazado inesperado en la vista.')
        for nom in noms:
            arc = Path(raiz)/nom
            rel = arc.relative_to(destino).as_posix()
            if rel not in esperado or not arc.is_symlink() or str(arc.resolve(strict=True)) != esperado[rel]:
                raise ValueError('Vista modificada: '+rel)
            vistos.add(rel)
    if vistos != set(esperado): raise ValueError('Vista incompleta.')


def compara_catalogos(anterior, nuevo):
    """Refuse a generated catalog that silently loses any resource or origin URL."""
    def claves(dat, incluir_locales=False):
        sal = set()
        for ent in dat.get('resources',[]):
            if ent.get('published'): sal.add(('local',ent.get('path') or ent.get('filename')))
        for ent in (dat.get('resources',[]) if incluir_locales else []) + dat.get('origin_resources',[]):
            url = ent.get('original_url') or ent.get('url')
            if url: sal.add(('origin',url))
        return sal
    faltan = claves(anterior)-claves(nuevo,True)
    if faltan: raise ValueError('La generación perdería entradas del catálogo: '+str(sorted(faltan)[:12]))
