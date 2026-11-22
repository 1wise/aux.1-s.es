# Timestamp: 2026-11-22 | Version: 8.0.0-beta.1
# Author & Credits: https://www.alawise.es/1-s
"""Keep featured artwork independent from portal wordmarks and favicon assets."""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from . import VERSION

IMG_DST='aux-featured.png'
TXT_ALT='AUX Suite: gnomo y guardián GNU en los Alpes'
DES_DEF='Perfiles Debian Testing, Fedora Rawhide y Alpine Linux, catálogo netboot y herramientas de instalación, recuperación y administración.'


def registro():
    dat=json.loads((Path(__file__).resolve().parents[1]/'config/platform.metadata.json').read_text())
    dat['version']=VERSION
    dat['seo_meta_tags']['standard']['generator']='AUX Suite '+VERSION
    dat['structured_data_json_ld']['@graph'][0]['softwareVersion']=VERSION
    anc,alt=dimensiones()
    og=dat['seo_meta_tags']['open_graph'];og['og:image:width']=anc;og['og:image:height']=alt
    return dat


def canonica(url):
    partes=urlsplit(url)
    if partes.hostname and partes.hostname.endswith('.chatgpt.site'):
        base=urlsplit(registro()['project']['url'])
        partes=partes._replace(scheme=base.scheme,netloc=base.netloc)
    ruta='/' if partes.path in ('','/index.html','/index.php','/index-aux.php') else partes.path
    return urlunsplit(partes._replace(path=ruta,query='',fragment=''))


def dimensiones():
    with (Path(__file__).resolve().parents[1]/'assets'/IMG_DST).open('rb') as arc:
        cab=arc.read(24)
    if len(cab)!=24 or cab[:8]!=b'\x89PNG\r\n\x1a\n' or cab[12:16]!=b'IHDR':
        raise ValueError('La imagen destacada debe ser un PNG válido.')
    return int.from_bytes(cab[16:20],'big'),int.from_bytes(cab[20:24],'big')


def meta_html(url_bas,url_can,tit,des=DES_DEF):
    dat=registro();seo=dat['seo_meta_tags'];std=seo['standard'];url_can=canonica(url_can)
    principal=urlsplit(url_can).path=='/'
    tit_og=seo['open_graph']['og:title'] if principal else tit
    des_og=seo['open_graph']['og:description'] if principal else des
    tit_tw=seo['twitter_card']['twitter:title'] if principal else tit
    des_tw=seo['twitter_card']['twitter:description'] if principal else des
    anc,alt=dimensiones();url_img=url_bas.rstrip('/')+'/assets/'+IMG_DST+'?v='+VERSION
    etqs=[('property','og:type','website'),('property','og:site_name',seo['open_graph']['og:site_name']),
        ('property','og:title',tit_og),('property','og:description',des_og),
        ('property','og:url',url_can),('property','og:image',url_img),
        ('property','og:image:type','image/png'),('property','og:image:width',str(anc)),
        ('property','og:image:height',str(alt)),('property','og:image:alt',TXT_ALT),
        ('name','twitter:card','summary_large_image'),('name','twitter:title',tit_tw),
        ('name','twitter:description',des_tw),('name','twitter:image',url_img),('name','twitter:image:alt',TXT_ALT)]
    for nom in ('author','generator','robots','googlebot','rating','copyright'):
        etqs.append(('name',nom,std[nom]))
    etqs += [('name','description',std['description'] if urlsplit(url_can).path=='/' else des),
             ('name','keywords',', '.join(std['keywords'])),('name','application-name',std['application_name']),
             ('property','og:locale',seo['open_graph']['og:locale']),
             ('name','twitter:site',seo['twitter_card']['twitter:site']),('name','twitter:creator',seo['twitter_card']['twitter:creator']),
             ('name','fediverse:creator',seo['specialized_networks']['mastodon']['fediverse:creator'])]
    for loc in seo['open_graph']['og:locale:alternate']:etqs.append(('property','og:locale:alternate',loc))
    if url_img.startswith('https://'):etqs.append(('property','og:image:secure_url',url_img))
    ld=json.dumps(dat['structured_data_json_ld'],ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    return ('<link rel="canonical" href="'+html.escape(url_can,quote=True)+'">\n'+
        '\n'.join('<meta '+tip+'="'+clv+'" content="'+html.escape(str(val),quote=True)+'">' for tip,clv,val in etqs)+
        '\n<script type="application/ld+json" data-aux-seo>'+ld+'</script>')


def aplica_metadata(txt,url_bas,url_can,tit):
    # Replace controlled tags so overrides and regenerated guides never duplicate metadata.
    control={'description','keywords','author','generator','robots','googlebot','rating','copyright','application-name','fediverse:creator'}
    def limpia(dat):
        tag=dat.group();nom=re.search(r'(?:name|property)=["\']([^"\']+)',tag,re.I)
        if nom and (nom.group(1).lower() in control or nom.group(1).startswith(('og:','twitter:'))):return ''
        return tag
    txt=re.sub(r'<meta\b[^>]*>',limpia,txt,flags=re.I)
    txt=re.sub(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>','',txt,flags=re.I)
    txt=re.sub(r'<script\b[^>]*data-aux-seo[^>]*>.*?</script>','',txt,flags=re.S)
    if urlsplit(canonica(url_can)).path=='/':
        txt=re.sub(r'<title>.*?</title>','<title>'+html.escape(registro()['seo_meta_tags']['standard']['title'])+'</title>',txt,flags=re.S)
    return txt.replace('</head>',meta_html(url_bas,url_can,tit)+'\n</head>',1)


def robots_txt(base):
    agentes=('GPTBot','ClaudeBot','PerplexityBot','anthropic-ai','ChatGPT-User')
    return 'User-agent: *\nAllow: /\n\n'+''.join('User-agent: '+nom+'\nAllow: /\n\n' for nom in agentes)+'Sitemap: '+base.rstrip('/')+'/sitemaps.xml\n'


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
