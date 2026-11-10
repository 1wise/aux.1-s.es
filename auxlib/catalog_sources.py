# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author & Credits: https://www.alawise.es/1-s
"""Read release metadata and upstream netboot menus without mirroring payloads."""
import hashlib
import json
import re
from urllib.parse import urlsplit


def clave(pref, *vals):
    return pref + '-' + hashlib.sha256('|'.join(map(str,vals)).encode()).hexdigest()[:20]


def fedora(fuente, byt):
    dat = json.loads(byt)
    if not isinstance(dat,list) or len(dat)>20000:
        raise ValueError('Metadatos Fedora inválidos.')
    nums = [int(ent['version']) for ent in dat if re.fullmatch(r'[0-9]+',str(ent.get('version','')))]
    if not nums:
        raise ValueError('No se ha encontrado una versión Fedora publicada.')
    version = str(max(nums))
    sal = []
    for ent in dat:
        if str(ent.get('version')) != version:
            continue
        url = ent.get('link','')
        nom = urlsplit(url).path.rsplit('/',1)[-1]
        if not re.fullmatch(fuente.get('pattern',r'.*\.iso'),nom):
            continue
        if fuente.get('architectures') and ent.get('arch') not in fuente['architectures']:
            continue
        clase = fuente.get('defaults',{}).get('download_class','heavy')
        for regla in fuente.get('class_rules',[]):
            if re.fullmatch(regla['pattern'],nom):
                clase = regla['download_class']
                break
        sal.append({'id':clave(fuente['id'],url),'family':'fedora','release':version,
                    'name':'Fedora '+version+' · '+str(ent.get('subvariant',ent.get('variant',''))),
                    'architecture':ent['arch'],'kind':'installer' if 'netinst' in nom else 'image',
                    'download_class':clase,'original_url':url,'sha256':ent.get('sha256'),
                    'size_bytes':int(ent['size']) if ent.get('size') else None,
                    'channel':'released','source_index':fuente['url'],
                    'source_metadata_sha256':hashlib.sha256(byt).hexdigest(),
                    'allowed_hosts':fuente['allowed_hosts']})
    if not sal:
        raise ValueError('La fuente Fedora no produjo imágenes para la selección declarada.')
    return sal


def versiones(dat, nivel=0, canal=''):
    if nivel>8:
        raise ValueError('Estructura de versiones netboot demasiado profunda.')
    if isinstance(dat,list):
        for ent in dat:
            yield from versiones(ent,nivel+1,canal)
    elif isinstance(dat,dict):
        if 'code_name' in dat:
            yield str(dat.get('name',dat['code_name'])),canal,str(dat.get('arch','upstream')),str(dat['code_name'])
        else:
            for nom,ent in dat.items():
                yield from versiones(ent,nivel+1,str(nom))


def netboot(fuente, byt, indice, readme=b''):
    try:
        import yaml
    except ImportError as exc:
        raise ValueError('El rastreador netboot necesita python3-pyyaml (Fedora) o python3-yaml (Debian).') from exc
    dat = yaml.safe_load(byt)
    menus = json.loads(indice)
    if not isinstance(dat,dict) or not isinstance(menus,list) or len(menus)>2000:
        raise ValueError('Metadatos netboot inválidos.')
    proyectos = {}
    for lin in readme.decode('utf-8').splitlines():
        cols = [val.strip() for val in lin.strip().strip('|').split('|')]
        if len(cols)>=2:
            mat = re.fullmatch(r'(https?://[^\s|]+)',cols[1])
            if mat:
                proyectos[re.sub(r'[^a-z0-9]','',cols[0].lower())] = mat[1]
    conocidos = {}
    for nom,ent in dat.get('releases',{}).items():
        if isinstance(ent,dict) and ent.get('enabled',True):
            conocidos[nom] = dict(ent,kind='netboot-install')
    for grupo in ('utilitiesarm','utilitiesefi','utilitiespcbios32','utilitiespcbios64'):
        for nom,ent in dat.get(grupo,{}).items():
            if isinstance(ent,dict) and ent.get('enabled',True) and nom not in conocidos:
                conocidos[nom] = dict(ent,kind='netboot-utility')
    sal = []
    for menu in menus:
        nom = menu.get('name','')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.ipxe(?:\.j2)?',nom):
            continue
        arch = nom.removesuffix('.j2')
        cod = arch.removesuffix('.ipxe')
        ent = conocidos.get(cod,{})
        rot = str(ent.get('name',cod.replace('live-','').replace('-',' ').title()))
        kind = 'netboot-live' if cod.startswith('live-') else ent.get('kind','netboot-menu')
        vers = list(versiones(ent.get('versions'))) or [('según menú del proveedor','upstream','upstream',cod)]
        for ver,canal,arqu,cod_ver in vers:
            url = fuente.get('boot_url','https://boot.netboot.xyz').rstrip('/')+'/'+arch
            sal.append({'id':clave(fuente['id'],cod,cod_ver,canal,arqu),'family':cod.removeprefix('live-'),
                        'name':rot,'release':ver[:120],'architecture':arqu,'kind':kind,
                        'download_class':'light','original_url':url,'remote_only':True,
                        'netboot_provider':'netboot.xyz','channel':canal,
                        'project_url':proyectos.get(re.sub(r'[^a-z0-9]','',rot.lower())),
                        'source_index':menu.get('html_url',fuente['url']),
                        'source_metadata_sha256':hashlib.sha256(byt+indice).hexdigest(),
                        'verification':{'http':'not-checked','download_hash':'not-applicable','source_signature':'not-checked',
                                        'bios_boot':'upstream-not-tested-by-aux','uefi_boot':'upstream-not-tested-by-aux'}})
    if not sal:
        raise ValueError('El índice netboot no contiene menús; se conserva el catálogo anterior.')
    return sal
