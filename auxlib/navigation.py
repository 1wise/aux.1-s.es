# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Keep one static navigation across generated pages and offline mirrors."""
import html
import posixpath
import re
from pathlib import Path
from urllib.parse import urlsplit

from .common import DIR_APP


def publica_navegacion(pth_web):
    """Reuse the portal menu without requiring JavaScript or a live server."""
    pth_web = Path(pth_web)
    txt_ind = (pth_web / 'index.html').read_text()
    nav_tpl = re.search(r'<aside\b[^>]*class="sidebar"[^>]*>.*?</aside>', txt_ind, re.S)
    if not nav_tpl:
        raise ValueError('The portal sidebar is missing.')
    nav_tpl = nav_tpl.group()
    pth_css = pth_web / 'assets/navigation.css'
    pth_css.write_text((DIR_APP / 'src/navigation.css').read_text())
    for pth in sorted(pth_web.rglob('*')):
        rel = pth.relative_to(pth_web)
        # Source downloads and mounted ISO contents must retain their original bytes.
        if not pth.is_file() or pth.suffix not in ('.html', '.php') or rel.parts[0] in ('downloads', 'isos', 'pxe', 'files', 'contents'):
            continue
        if rel.as_posix() in ('index-pxe.html', 'cli.html', 'cli-all.html', 'contents.html', 'chroot-all.html'):
            continue
        txt = pth.read_text()
        if 'data-aux-navigation="shared"' in txt or '</head>' not in txt:
            continue
        cab = re.search(r'<body\b[^>]*>', txt)
        if not cab:
            continue
        pref = '../' * (len(rel.parts) - 1)
        nom_pag = rel.as_posix()

        def enlace(dat):
            atr, url = dat.groups()
            uri = urlsplit(html.unescape(url))
            if uri.scheme or uri.netloc or url.startswith('/'):
                return dat.group()
            if url.startswith('#'):
                url = 'index.html' + url
            return atr + '="' + pref + url + '"'

        nav = re.sub(r'(href|src)="([^"]*)"', enlace, nav_tpl)
        nom_dest = posixpath.relpath(nom_pag, rel.parent.as_posix())
        nav = nav.replace('href="' + nom_dest + '"', 'aria-current="page" href="' + nom_dest + '"')
        nav = nav.replace('<aside class="sidebar">', '<aside class="sidebar" aria-label="Navegación AUX">')
        txt = txt.replace('</head>', '<link rel="stylesheet" href="' + pref + 'assets/navigation.css">\n</head>', 1)
        # Preserve each page's existing forms, scripts, anchors, and content layout.
        if 'class="sidebar"' in txt:
            txt = re.sub(r'<aside\b[^>]*class="sidebar"[^>]*>.*?</aside>', lambda _: nav, txt, count=1, flags=re.S)
        else:
            txt = txt.replace(cab.group(), cab.group() + nav + '<div class="aux-page-content" id="aux-section">', 1)
            pos_fin = txt.rfind('</body>')
            txt = txt[:pos_fin] + '</div>' + txt[pos_fin:]
        cab = re.search(r'<body\b[^>]*>', txt)
        eti = cab.group()
        if 'class="' in eti:
            eti = eti.replace('class="', 'class="aux-navigation ', 1)
        else:
            eti = eti[:-1] + ' class="aux-navigation">'
        eti = eti[:-1] + ' data-aux-navigation="shared">'
        txt = txt.replace(cab.group(), eti, 1)
        pth.write_text(txt)
