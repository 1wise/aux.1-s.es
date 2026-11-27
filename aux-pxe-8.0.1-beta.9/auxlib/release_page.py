# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Render download links from the files actually served by this installation."""
from pathlib import Path
import re

from .branding import aplica_metadata
from .common import DIR_APP, atomico, suma
from .release_bundle import nombres

PAGINA = 'release-8.html'
ANTIGUAS = ('release-7.html', 'readme-7.html')


def publica_descargas(pth_web, url_base):
    pth_web = Path(pth_web)
    txt = (DIR_APP / 'src' / PAGINA).read_text()
    propuesta = 'proposals-ei.html'
    atomico(pth_web / propuesta, (DIR_APP / 'src' / propuesta).read_text())
    archivos = nombres()
    for clave, marca in [('sources', 'PACKAGE'), ('aux-pxe', 'AUX_PXE'), ('tec-cli', 'TEC_CLI')]:
        arc = pth_web / 'downloads' / archivos[clave]
        tam = f'{arc.stat().st_size / 1_000_000:.2f} MB' if arc.is_file() else 'Pendiente de subir a esta réplica'
        txt = txt.replace('@@' + marca + '_SIZE@@', tam)
        if clave == 'sources':
            txt = txt.replace('@@PACKAGE_SHA256@@', suma(arc) if arc.is_file() else 'Pendiente de publicación')

    # A replica may carry only one module. Keep its page readable offline.
    def enlace(coincidencia):
        rel = coincidencia.group(1)
        return coincidencia.group() if (pth_web / rel).is_file() else ''

    txt = re.sub(r'<a\b[^>]*href="(downloads/[^"]+|proposals-ei\.html)"[^>]*>.*?</a>', enlace, txt, flags=re.S)
    canon = url_base.rstrip('/') + '/' + PAGINA
    atomico(pth_web / PAGINA, aplica_metadata(txt, url_base, canon, 'Descargar la suite AUX'))
    for nom in ANTIGUAS:
        # The ordinary link also works in text browsers with redirects disabled.
        alias = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
                 '<meta http-equiv="refresh" content="0; url=release-8.html">'
                 '<title>Descargas AUX</title></head><body><a href="release-8.html">'
                 'Abrir las descargas de AUX 8</a></body></html>')
        atomico(pth_web / nom, aplica_metadata(alias, url_base, canon, 'Descargas AUX'))
