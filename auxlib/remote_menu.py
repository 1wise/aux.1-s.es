# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Expose origin catalogue branches without treating arbitrary images as boot scripts."""
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit


def rotulo(txt):
    txt=unicodedata.normalize('NFKD',str(txt)).encode('ascii','ignore').decode()
    return re.sub(r'[^A-Za-z0-9 .,:/()_+?-]','',txt)[:150]


def es_menu_proveedor(ent):
    url=ent.get('original_url',ent.get('url',''));part=urlsplit(url)
    return bool(ent.get('remote_only',ent.get('format')=='MENU') and part.scheme=='https'
                and part.netloc=='boot.netboot.xyz' and not part.query and not part.fragment
                and re.fullmatch(r'/[A-Za-z0-9_-]+\.ipxe',part.path))


def lanzador_origen(ent):
    """Build a standalone launcher only for an explicitly supported provider menu."""
    if not es_menu_proveedor(ent):return None
    from . import VERSION
    url=ent.get('original_url',ent.get('url'));cod=urlsplit(url).path.rsplit('/',1)[-1][:-5]
    return '\n'.join(['#!ipxe','# Timestamp: 2026-11-10 | Version: '+VERSION,
        '# Author & Credits: https://www.alawise.es/1-s',
        'set arch ${buildarch}',
        'iseq ${buildarch} i386 && cpuid --ext 29 && set arch x86_64 ||',
        'chain --autofree https://boot.netboot.xyz/boot.cfg || goto origin_error',
        'set space:hex 20:20','set space ${space:string}','set menu '+cod,
        'chain --autofree '+url+' || goto origin_error','exit',
        ':origin_error','echo Upstream menu failed. Check network and firmware.',
        'prompt Press a key to return...','exit',''])


def menu_origen(entradas):
    from .localtools import arbol_catalogo
    # One provider menu can advertise several releases; the provider selects the release.
    unicas={}
    for ent in entradas:
        url=ent.get('original_url','')
        part=urlsplit(url)
        if part.scheme!='https' or not part.hostname or part.username or part.password:
            continue
        if re.search(r'[\s\x00-\x1f\x7f;|$<>"\\&]',url):
            continue
        if url not in unicas:
            unicas[url]=dict(ent)
    dis,tools=arbol_catalogo(list(unicas.values()))
    lin=['',':origin_menu','set menu_back origin_menu','set auto_timeout 0',
         'menu Systems and tools / ORIGIN',
         'item origin_distributions Distributions / upstream menus and images',
         'item origin_tools Tools / categories',
         'item origin_provider Full netboot.xyz provider menu',
         'item --gap -- Network access required. Provider recipes are not AUX hardware tests.',
         'item start Back','choose target && goto ${target} || goto start']

    def grupo(nom,grupos,titulo):
        ramas=[]
        for familia,ents in sorted(grupos.items(),key=lambda val:val[0].casefold()):
            clave='origin_g_'+hashlib.sha256((nom+familia).encode()).hexdigest()[:12]
            ramas.append((clave,familia,ents))
        lin.extend(['',':'+nom,'set menu_back '+nom,'menu '+titulo])
        for clave,familia,ents in ramas:
            lin.append('item '+clave+' '+rotulo(familia)+' ('+str(len(ents))+')')
        lin.extend(['item origin_menu Back','choose target && goto ${target} || goto origin_menu'])
        for clave,familia,ents in ramas:
            hojas=[]
            lin.extend(['',':'+clave,'set menu_back '+clave,'menu '+rotulo(titulo+' / '+familia)])
            for ent in ents:
                url=ent['original_url'];part=urlsplit(url)
                rid='origin_r_'+hashlib.sha256(url.encode()).hexdigest()[:16]
                es_menu=es_menu_proveedor(ent)
                nombre=ent.get('name') or familia
                titulo_ent=rotulo(nombre+' / '+str(ent.get('architecture','upstream')))
                if not es_menu:titulo_ent+=' / '+rotulo(ent.get('release',''))
                lin.append('item '+rid+' '+('MENU ' if es_menu else 'URL ')+titulo_ent)
                hojas.append((rid,ent,es_menu))
            lin.extend(['item '+nom+' Back','item start Main menu',
                        'choose target && goto ${target} || goto '+nom])
            for rid,ent,es_menu in hojas:
                lin.extend(['',':'+rid,'set auto_timeout 0','set aux_origin_back '+clave])
                if es_menu:
                    cod=urlsplit(ent['original_url']).path.rsplit('/',1)[-1].removesuffix('.ipxe')
                    # boot.cfg defines the mirrors and menu variables required by leaf scripts.
                    lin.extend(['set arch ${menu_arch}',
                                'chain --autofree https://boot.netboot.xyz/boot.cfg || goto origin_error',
                                'set space:hex 20:20','set space ${space:string}',
                                'set menu '+cod,
                                'echo Loading the upstream menu. Select version and install mode there.',
                                'chain --autofree '+ent['original_url']+' || goto origin_error',
                                'goto '+clave])
                else:
                    lin.extend(['echo Download / import URL. No automatic network boot recipe is declared.',
                                'echo '+ent['original_url'],'prompt Press any key to return...','goto '+clave])
    grupo('origin_distributions',dis,'Origin / distributions')
    grupo('origin_tools',tools,'Origin / tools')
    lin.extend(['',':origin_provider','set aux_origin_back origin_menu','set arch ${menu_arch}',
                'clear menu','chain --autofree https://boot.netboot.xyz || goto origin_error',
                'goto origin_menu',':origin_error','echo Upstream menu failed. Check network, HTTPS support and firmware.',
                'prompt Press any key to return...','goto ${aux_origin_back}'])
    return lin
