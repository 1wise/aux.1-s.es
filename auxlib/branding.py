# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Keep featured artwork independent from portal wordmarks and favicon assets."""
import html
from pathlib import Path

from . import VERSION

IMG_DST='aux-featured.png'
TXT_ALT='AUX Suite: gnomo y guardián GNU en los Alpes'
DES_DEF='Catálogo netboot, distribuciones Linux y herramientas para instalar, recuperar y administrar sistemas.'


def dimensiones():
    with (Path(__file__).resolve().parents[1]/'assets'/IMG_DST).open('rb') as arc:
        cab=arc.read(24)
    if len(cab)!=24 or cab[:8]!=b'\x89PNG\r\n\x1a\n' or cab[12:16]!=b'IHDR':
        raise ValueError('La imagen destacada debe ser un PNG válido.')
    return int.from_bytes(cab[16:20],'big'),int.from_bytes(cab[20:24],'big')


def meta_html(url_bas,url_can,tit,des=DES_DEF):
    anc,alt=dimensiones();url_img=url_bas.rstrip('/')+'/assets/'+IMG_DST+'?v='+VERSION
    etqs=[('property','og:type','website'),('property','og:site_name','AUX Suite'),
        ('property','og:title',tit),('property','og:description',des),
        ('property','og:url',url_can),('property','og:image',url_img),
        ('property','og:image:type','image/png'),('property','og:image:width',str(anc)),
        ('property','og:image:height',str(alt)),('property','og:image:alt',TXT_ALT),
        ('name','twitter:card','summary_large_image'),('name','twitter:title',tit),
        ('name','twitter:description',des),('name','twitter:image',url_img),('name','twitter:image:alt',TXT_ALT)]
    if url_img.startswith('https://'):etqs.append(('property','og:image:secure_url',url_img))
    return '\n'.join('<meta '+tip+'="'+clv+'" content="'+html.escape(val,quote=True)+'">' for tip,clv,val in etqs)


def pie_imagen(asset_base='assets/'):
    url_img=html.escape(asset_base+IMG_DST+'?v='+VERSION,quote=True)
    anc,alt=dimensiones()
    # Both links use the original bytes; display dimensions never resize the file.
    return ('<figure class="featured-art"><a href="'+url_img+'" target="_blank" rel="noopener" '
            'aria-label="Abrir imagen destacada a resolución completa"><img src="'+url_img+'" '
            'width="144" height="144" loading="lazy" decoding="async" alt="'+html.escape(TXT_ALT,quote=True)+'"></a>'
            '<figcaption><a class="featured-download" href="'+url_img+'" download="'+IMG_DST+'">'
            'Descargar PNG original<span class="featured-size">'+str(anc)+' × '+str(alt)+' píxeles</span></a>'
            '</figcaption></figure>')
