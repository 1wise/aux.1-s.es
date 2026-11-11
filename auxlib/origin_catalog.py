# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Adapt upstream references to the portal without inventing local payloads."""
import hashlib
from urllib.parse import urlsplit, unquote


def recursos_origen(entradas, locales):
    from .catalog_profile import url_perfil
    from .localtools import arbol_catalogo
    from .remote_menu import es_menu_proveedor
    vistas = {r.get('url') for r in locales}
    salida = []
    for ent in entradas:
        url = ent.get('original_url', '')
        if url in vistas:
            continue
        try:
            url_perfil(url)
        except ValueError:
            continue
        vistas.add(url)
        rid = 'origin_' + hashlib.sha256(url.encode()).hexdigest()[:20]
        path = urlsplit(url).path.rstrip('/')
        if path.endswith('/download'):
            path = path[:-9]
        nom = unquote(path.rsplit('/', 1)[-1]) or rid
        dis, tools = arbol_catalogo([ent])
        menu = es_menu_proveedor(ent)
        salida.append({'id': rid, 'name': str(ent.get('name') or nom),
            'family': str(ent.get('family') or 'other').lower(),
            'category': 'tools' if tools else 'distribution',
            'kind': str(ent.get('kind') or 'image'),
            'release': str(ent.get('release') or 'upstream'),
            'arch': str(ent.get('architecture') or 'upstream'),
            'filename': nom, 'tree': '', 'format': 'MENU' if menu else 'URL',
            'url': url, 'status': 'origin-only', 'published': False,
            'size': None, 'source_size': ent.get('size_bytes'), 'sha256': None,
            'contents_ready': False, 'pxe_ready': False, 'origin_only': True,
            'origin_launcher': 'origins/'+rid+'.ipxe' if menu else None,
            'download_urls': {'source': url},
            'description': 'Upstream menu; choose the release at the provider.' if menu else 'Origin URL; image hosting and a boot recipe are separate choices.',
            'pxe_reason': 'Provider menu available; hardware boot test pending.' if menu else 'Origin URL only; no automatic boot recipe declared.'})
    return salida
