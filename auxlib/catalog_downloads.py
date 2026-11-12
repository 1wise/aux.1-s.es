# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Resolve every selected payload against its declared edition and release channel."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


def nombre_archivo(url):
    ruta=urllib.parse.unquote(urllib.parse.urlsplit(url).path).rstrip('/')
    if ruta.endswith('/download'):ruta=ruta[:-9]
    return ruta.rsplit('/',1)[-1]


def coincide(url, regla):
    if regla.get('filename_pattern'):
        return bool(re.fullmatch(regla['filename_pattern'],nombre_archivo(url)))
    return bool(re.fullmatch(regla['url_pattern'],url))


def orden_version(txt):
    return tuple(int(val) for val in re.findall(r'[0-9]+',str(txt)))


def lee_sumas(txt, algoritmo='sha256'):
    """Respect algorithm sections; BLAKE3 is not SHA-256 despite its hash length."""
    largo={'sha256':64,'sha512':128}[algoritmo]; seccion=None; sal={}
    for lin in txt.splitlines():
        hdr=re.fullmatch(r'[#\s]*(MD5|SHA1|SHA256|SHA512|B2|B3)(?:SUMS?| HASH)?[:\s]*',lin,re.I)
        if hdr:seccion=hdr[1].lower();continue
        bsd=re.fullmatch(r'(SHA256|SHA512) \((.+)\) = ([a-fA-F0-9]+)',lin.strip())
        if bsd:
            if bsd[1].lower()!=algoritmo:continue
            nom,dig=bsd[2],bsd[3].lower()
        else:
            if seccion and seccion!=algoritmo:continue
            mat=re.fullmatch(r'([a-fA-F0-9]{'+str(largo)+r'})\s+\*?(.+)',lin.strip())
            if not mat:continue
            dig,nom=mat[1].lower(),mat[2]
        if len(dig)!=largo:continue
        nom=nom.removeprefix('./')
        if nom in sal and sal[nom]!=dig:raise ValueError('Sumas contradictorias: '+nom)
        sal[nom]=dig
    if not sal:raise ValueError('No hay sumas '+algoritmo+' en el manifiesto.')
    return sal


def enlaces(byt, base, hosts):
    from .catalog import Enlaces, url_segura
    par=Enlaces();txt=byt.decode('utf-8');par.feed(txt)
    vals=par.urls+re.findall(r'https://[^\s<>"\']+',txt)
    sal=[]
    for val in vals:
        url=urllib.parse.urljoin(base,unescape(val))
        part=urllib.parse.urlsplit(url)
        if part.scheme=='http' and part.hostname in hosts:
            url=urllib.parse.urlunsplit(('https',part.netloc,part.path,part.query,part.fragment))
        try:url_segura(url,hosts)
        except ValueError:continue
        if url not in sal:sal.append(url)
    return sal


def candidatos(fuente, cache, traer):
    from .catalog import descubre, url_segura
    tipo=fuente['format'];url=fuente['url'];hosts=fuente['allowed_hosts']
    url_segura(url,hosts)
    if tipo=='fixed':return [dict(x) for x in fuente['artifacts']]
    if tipo=='gentoo-latest':return descubre(fuente,cache,traer)
    byt=traer(url,hosts,cache)
    if b'<title>Site Unavailable</title>' in byt:
        raise ValueError('Fuente inaccesible: el servidor devuelve Site Unavailable en '+url)
    if tipo=='fedora-artifacts':
        dat=json.loads(byt)
        ver=max(int(x['version']) for x in dat if str(x.get('version','')).isdigit())
        return [{'original_url':x['link'],'release':str(ver),'sha256':x.get('sha256'),
                 'size_bytes':int(x['size']) if x.get('size') else None}
                for x in dat if str(x.get('version'))==str(ver)]
    if tipo=='github-assets':
        dat=json.loads(byt)
        if dat.get('draft') or dat.get('prerelease'):raise ValueError('La publicación GitHub no es estable.')
        sal=[]
        for x in dat.get('assets',[]):
            dig=x.get('digest') or ''
            sal.append({'original_url':x['browser_download_url'],'release':dat['tag_name'],
                        'size_bytes':x.get('size'),'sha256':dig[7:] if dig.startswith('sha256:') else None})
        return sal
    if tipo=='alpine-releases':
        try:import yaml
        except ImportError as exc:raise ValueError('Instalar python3-pyyaml (Fedora) o python3-yaml (Debian).') from exc
        dat=yaml.safe_load(byt)
        return [{'original_url':urllib.parse.urljoin(url,x['file']),'release':str(x['version']),
                 'size_bytes':x.get('size'),'sha256':x.get('sha256')}
                for x in dat if isinstance(x,dict) and x.get('file')]
    if tipo=='arch-releases':
        dat=json.loads(byt)
        return [{'original_url':urllib.parse.urljoin(fuente['artifact_base'],x['iso_url']),
                 'release':x['version'],'sha256':x.get('sha256_sum')}
                for x in dat.get('releases',[]) if x.get('available') and x.get('iso_url')]
    if tipo=='checksum-index':
        sums=lee_sumas(byt.decode(),'sha256');sal=[]
        for nom,dig in sums.items():
            mat=re.fullmatch(fuente['filename_pattern'],Path(nom).name)
            if not mat:continue
            campos={**mat.groupdict(),'filename':Path(nom).name}
            dst=urllib.parse.urljoin(fuente['artifact_base'],fuente['artifact_template'].format(**campos))
            sal.append({'original_url':dst,'sha256':dig,'release':campos.get('release'),'checksum_source':url})
        return sal
    if tipo=='html-walk':
        dirs=[val for val in enlaces(byt,url,hosts) if re.fullmatch(fuente['directory_pattern'],
              urllib.parse.urlsplit(val).path.rstrip('/').rsplit('/',1)[-1])]
        if not dirs:raise ValueError('No hay un directorio de la rama solicitada.')
        ultimo=max(dirs,key=lambda val:orden_version(urllib.parse.urlsplit(val).path))
        url=urllib.parse.urljoin(ultimo.rstrip('/')+'/',fuente.get('subdirectory',''))
        byt=traer(url,hosts,cache);tipo='artifact-html'
    if tipo=='artifact-rss':
        arbol=ET.fromstring(byt)
        urls=[]
        for ent in arbol.iter():
            if ent.tag.rsplit('}',1)[-1]=='link' and ent.text:urls.append(ent.text.strip())
            if ent.get('url'):urls.append(ent.get('url'))
    elif tipo=='artifact-html':urls=enlaces(byt,url,hosts)
    else:raise ValueError('Adaptador de descargas desconocido: '+tipo)
    urls=list(dict.fromkeys(urls));sums={};sum_url=fuente.get('checksums_url')
    algoritmo=fuente.get('checksum_algorithm','sha256')
    if sum_url:
        origenes=fuente.get('mirror_redirect_origins',[])
        cuerpo=traer(sum_url,hosts,cache,8388608,origenes) if origenes else traer(sum_url,hosts,cache)
        sums=lee_sumas(cuerpo.decode(),algoritmo)
    sal=[]
    for dst in urls:
        try:url_segura(dst,hosts)
        except ValueError:continue
        nom=nombre_archivo(dst)
        if not re.search(r'\.(?:iso(?:\.zip)?|tar\.gz|qcow2|efi|kpxe|pxe|lkrn)$',nom,re.I):continue
        ent={'original_url':dst,'source_index':url}
        if sums:
            rel=urllib.parse.unquote(urllib.parse.urlsplit(dst).path).removeprefix(urllib.parse.urlsplit(url).path)
            dig=sums.get(nom) or sums.get(rel)
            if not dig:continue
            ent[algoritmo]=dig;ent['checksum_source']=sum_url
        sal.append(ent)
    return sal


def comprueba_enlace(url, hosts, tam_esperado=None, origenes_espejo=()):
    """Read headers only; a bounded range fallback never reads an image body."""
    from .catalog import url_segura
    from .catalog_mirrors import RedireccionDescarga
    url_segura(url,hosts)
    redir=RedireccionDescarga(hosts,url,origenes_espejo)
    abridor=urllib.request.build_opener(redir)
    hdr={'User-Agent':'AUX/7.0 (+https://www.alawise.es/1-s)'}
    try:rsp=abridor.open(urllib.request.Request(url,headers=hdr,method='HEAD'),timeout=20)
    except urllib.error.HTTPError as exc:
        if exc.code not in (405,501):raise
        rsp=abridor.open(urllib.request.Request(url,headers={**hdr,'Range':'bytes=0-0'}),timeout=20)
    with rsp:
        if 'text/html' in rsp.headers.get('Content-Type','').lower():
            raise ValueError('El servidor devolvió HTML en lugar del archivo.')
        rango=re.fullmatch(r'bytes \d+-\d+/(\d+)',rsp.headers.get('Content-Range',''))
        tam=int(rango[1]) if rango else int(rsp.headers.get('Content-Length') or 0)
        if tam_esperado and tam and int(tam_esperado)!=tam:
            raise ValueError('El tamaño HTTP difiere del publicado en los metadatos.')
        # Mirror tickets are temporary; keep only a durable host/path in the public report.
        final=urllib.parse.urlsplit(rsp.url)
        limpio=urllib.parse.urlunsplit((final.scheme,final.netloc,final.path,'',''))
        return {'http':'passed','final_url':limpio,'size_bytes':tam or tam_esperado,
                'etag':rsp.headers.get('ETag'),'modified':rsp.headers.get('Last-Modified'),
                'redirect_policy':'provider-delegated-https' if redir.delegada else 'configured-hosts'}


def resuelve_slot(slot, opciones):
    reg=re.compile(slot['filename_pattern']);validas=[]
    for ent in opciones:
        mat=reg.fullmatch(nombre_archivo(ent['original_url']))
        if not mat:continue
        canal=slot.get('channel');ruta=ent['original_url'].casefold()
        if canal=='stable' and re.search(r'(?:^|[/_.-])(?:alpha|beta|rc|pre|testing|daily|nightly|rawhide|unstable)(?:[0-9/_.-]|$)',ruta):continue
        if canal in ('beta','testing') and not re.search(r'(?:^|[/_.-])'+canal+r'(?:[0-9/_.-]|$)',ruta):continue
        if slot.get('candidate_url_pattern') and not re.search(slot['candidate_url_pattern'],ent['original_url']):continue
        copia=dict(ent)
        copia['release']=mat.groupdict().get('release') or ent.get('release') or slot.get('release','rolling')
        validas.append(copia)
    if not validas:raise ValueError('El índice no ofrece la edición/arquitectura/canal solicitados.')
    ultima=max(orden_version(ent['release']) for ent in validas)
    validas=[ent for ent in validas if orden_version(ent['release'])==ultima]
    # Prefer a direct image over SourceForge's HTML landing page for the same payload.
    validas.sort(key=lambda ent:ent['original_url'].endswith('/download'))
    nombres={nombre_archivo(ent['original_url']) for ent in validas}
    if len(nombres)!=1:raise ValueError('Hay más de una imagen para la misma edición; revisar la regla.')
    return validas[0]


def rastrea_descargas(config, arc_config, cache, traer, comprobar=comprueba_enlace, url_file=None, candidatas=()):
    fuentes={x['id']:x for x in config['download_sources']}
    slots=config['download_slots']; reglas={x['id']:x for x in slots}
    if len(reglas)!=len(slots):raise ValueError('Identificadores de descargas duplicados.')
    listas=config.get('download_lists',{'all':'../url.txt'})
    pth=Path(url_file) if url_file else Path(arc_config).parent/listas['all']
    urls=list(dict.fromkeys(l.strip() for l in pth.read_text().splitlines() if l.strip() and not l.lstrip().startswith('#')))
    elegidos=[]
    for url in urls:
        mats=[x for x in slots if coincide(url,x)]
        if not mats:
            ids={x['slot_id'] for x in candidatas if x['previous_url']==url}
            mats=[reglas[nom] for nom in ids if nom in reglas]
        elegidos.append((url,mats[0] if len(mats)==1 else None))
    requeridas={s['source_id'] for _,s in elegidos if s}
    datos={};fallos={}
    print(f'Rastreo de descargas: {len(urls)} URL | {len(requeridas)} fuentes',flush=True)
    def obtiene(nom):
        if nom not in fuentes:raise ValueError('Fuente no configurada: '+nom)
        return candidatos(fuentes[nom],cache,traer)
    with ThreadPoolExecutor(max_workers=4) as pool:
        trabajos={pool.submit(obtiene,nom):nom for nom in sorted(requeridas)}
        for tarea in as_completed(trabajos):
            nom=trabajos[tarea]
            try:datos[nom]=tarea.result();print('FUENTE OK '+nom,flush=True)
            except (OSError,ValueError,KeyError,TypeError,ET.ParseError) as exc:
                fallos[nom]=str(exc);print('FUENTE ERROR '+nom+': '+str(exc),flush=True)
    entradas=[];filas=[]
    def resuelve(par):
        anterior,slot=par
        fila={'previous_url':anterior,'status':'failed'}
        if slot is None:
            fila.update(status='unmapped',error='La URL no tiene una única regla de actualización.');return fila,None
        fila.update(slot_id=slot['id'],source_id=slot['source_id'],channel=slot.get('channel','released'),
                    source_index=fuentes.get(slot['source_id'],{}).get('url'))
        try:
            from .catalog_repair import opciones_guardadas
            fuente=fuentes[slot['source_id']]
            opciones=list(datos.get(slot['source_id'],[]))
            manuales=opciones_guardadas(candidatas,slot,fuente,opciones)
            opciones+=manuales
            if slot['source_id'] in fallos:
                if not manuales:raise ValueError(fallos[slot['source_id']])
                fila['source_warning']=fallos[slot['source_id']]
            ent=resuelve_slot(slot,opciones)
            from .catalog import url_segura
            hosts=ent.get('allowed_hosts') or fuente['allowed_hosts']
            origenes=fuente.get('mirror_redirect_origins',[])
            url_segura(ent['original_url'],hosts)
            def revisa(actual):
                hosts_actual=actual.get('allowed_hosts') or fuente['allowed_hosts']
                if actual.get('candidate_origin'):
                    from .catalog_mirrors import valida_espejo
                    valida_espejo(actual['original_url'])
                return comprobar(actual['original_url'],hosts_actual,actual.get('size_bytes'),origenes)
            ent.update({k:slot[k] for k in ('family','architecture','kind','download_class')})
            ent.update(id=slot['id']+'-'+hashlib.sha256(ent['original_url'].encode()).hexdigest()[:16],
                       source_id=slot['id'],allowed_hosts=hosts,source_index=fila['source_index'],
                       channel=fila['channel'],name=nombre_archivo(ent['original_url']))
            ver=ent.setdefault('verification',{})
            ver.update(download_hash='not-checked',source_signature='not-checked')
            try:
                http=revisa(ent)
                ver['http']='passed'
                if http.get('size_bytes'):ent['size_bytes']=http['size_bytes']
                fila['http']=http
            except (OSError,ValueError) as exc:
                ver['http']='failed';fila['http']={'http':'failed','error':str(exc)}
                if manuales or slot.get('latest_available') and isinstance(exc,urllib.error.HTTPError) and exc.code in (404,410):
                    omitidas=[{'release':ent['release'],'url':ent['original_url'],'error':str(exc)}]
                    fila['unavailable_newer_versions']=omitidas
                    restantes=list(opciones);actual=ent
                    for intento in range(5+len(manuales)):
                        restantes=[x for x in restantes if x['original_url']!=actual['original_url']]
                        if not restantes:break
                        try:actual=resuelve_slot(slot,restantes)
                        except ValueError:break
                        try:http=revisa(actual)
                        except (OSError,ValueError) as error:
                            omitidas.append({'release':actual['release'],'url':actual['original_url'],'error':str(error)})
                            if not manuales and (not isinstance(error,urllib.error.HTTPError) or error.code not in (404,410)):break
                        else:
                            for nom in ('sha256','sha512','checksum_source','size_bytes','candidate_origin','reference_url'):ent.pop(nom,None)
                            ent.update(actual)
                            ent['allowed_hosts']=actual.get('allowed_hosts') or fuente['allowed_hosts']
                            ent.update(id=slot['id']+'-'+hashlib.sha256(ent['original_url'].encode()).hexdigest()[:16],
                                       name=nombre_archivo(ent['original_url']))
                            if http.get('size_bytes'):ent['size_bytes']=http['size_bytes']
                            ver['http']='passed';fila['http']=http;fila['unavailable_newer_versions']=omitidas
                            break
                    if ver['http']!='passed':raise ValueError('No se ha encontrado una versión disponible en el canal solicitado.')
            fila.update(status='rolling-checked' if fuentes[slot['source_id']]['format']=='fixed' and ver['http']=='passed' else 'resolved',
                        original_url=ent['original_url'],release=ent['release'],size_bytes=ent.get('size_bytes'),
                        sha256=ent.get('sha256'),sha512=ent.get('sha512'))
            if ent.get('candidate_origin'):fila['candidate_origin']=ent['candidate_origin']
            if fuentes[slot['source_id']]['format']=='fixed' and ver['http']!='passed':
                raise ValueError('No se pudo comprobar la URL de contenido variable: '+fila['http']['error'])
            return fila,ent
        except (ValueError,KeyError,TypeError) as exc:
            fila.update(status='failed',error=str(exc));return fila,None
    with ThreadPoolExecutor(max_workers=4) as pool:
        for fila,ent in pool.map(resuelve,elegidos):
            filas.append(fila)
            if ent:entradas.append(ent)
            print('DESCARGA '+fila['status'].upper()+' '+fila.get('slot_id',fila['previous_url']),flush=True)
    informe={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'total':len(urls),
             'resolved':sum(x['status'] in ('resolved','rolling-checked') for x in filas),
             'http_passed':sum(x.get('http',{}).get('http')=='passed' for x in filas),
             'resources':filas}
    informe['complete']=informe['resolved']==informe['total'] and informe['total']>0
    return entradas,informe
