# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""One editable catalogue, stable resource IDs, pinned artifacts and explicit policy."""
import argparse
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit, unquote

from .common import DIR_APP, guarda_json, identificador
from .policy24 import politica, acciones
from .settings import lee_config, ruta_config

SCHEMA = 'aux-catalog-v8'


def sin_secretos(dat):
    if isinstance(dat,dict):
        for key,val in dat.items():
            if str(key).lower() in ('password','passwd','api_key','apikey','access_token','authorization','private_key','secret'):
                raise ValueError('Credencial no permitida en el catálogo público: '+str(key))
            sin_secretos(val)
    elif isinstance(dat,list):
        for val in dat:sin_secretos(val)


def ahora():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def ruta_cfg(dat, nom, defecto, arc_cfg=None):
    pth = Path(dat.get(nom) or defecto).expanduser()
    res = pth.resolve() if pth.is_absolute() else (Path(arc_cfg or ruta_config()).parent / pth).resolve()
    if nom == 'catalog_sources_file' and not res.is_file():
        # Shipped resolver rules are immutable inputs, not user runtime state.
        # Honor an existing adjacent override and every custom path; repair only defaults.
        pred = Path('config/catalog.sources.json')
        usr_cfg = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config')).expanduser()/'aux'
        if not dat.get(nom) or pth == pred or res == (usr_cfg/pred).resolve():
            incluido = DIR_APP/pred
            if incluido.is_file():return incluido.resolve()
    return res


def rel_segura(txt):
    pth = PurePosixPath(txt)
    if not isinstance(txt, str) or not txt or pth.is_absolute() or any(x in ('..', '.') for x in txt.split('/')):
        raise ValueError('Ruta relativa inválida: '+str(txt))
    if any(ord(x) < 32 or x in '\\' for x in txt):
        raise ValueError('Ruta con caracteres no permitidos.')
    return pth.as_posix()


def url_publica(txt):
    if not isinstance(txt, str) or re.search(r'[\s\x00-\x1f\x7f<>"\\]', txt):
        raise ValueError('URL pública inválida.')
    part = urlsplit(txt)
    if part.scheme not in ('http', 'https') or not part.hostname or part.username or part.password or part.fragment:
        raise ValueError('URL HTTP(S) sin credenciales requerida.')
    from urllib.parse import parse_qsl
    if any(k.lower() in ('token','access_token','api_key','password','secret') for k, _ in parse_qsl(part.query)):
        raise ValueError('No guardar credenciales en las URL públicas.')
    return txt


def identidad(ent):
    # Availability and policy are mutable; neither may invalidate or forge boot evidence.
    campos = {k: ent.get(k) for k in ('id','release','architecture','original_url','sha256','components','recipe')}
    return hashlib.sha256(json.dumps(campos, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identidad_artefacto(ent):
    dat={k:ent.get(k) for k in ('id','release','architecture','original_url','sha256')}
    return hashlib.sha256(json.dumps(dat,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def ruta_publicada(ent, destino):
    if ent.get('paths',{}).get(destino):return rel_segura(ent['paths'][destino])
    version=re.sub('[^A-Za-z0-9._-]+','-',ent['release']).strip('-')[:60] or 'pinned'
    pin=(ent.get('sha256') or identidad_artefacto(ent))[:12]
    return f"resources/{destino}/{ent['id']}/{version}-{pin}/{ent['filename']}"


def nombre(ent):
    nom = ent.get('filename') or unquote(urlsplit(ent['original_url']).path.rstrip('/').split('/')[-1])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._+-]{0,239}', nom):
        raise ValueError('Nombre de artefacto inválido: '+str(nom))
    return nom


def valida(ent):
    if not isinstance(ent,dict):raise ValueError('Cada recurso debe ser un objeto JSON.')
    sin_secretos(ent)
    if not all(k in ent for k in ('id','original_url','policy')):raise ValueError('El recurso requiere id, original_url y policy.')
    ent = copy.deepcopy(ent)
    identificador(ent['id'])
    url_publica(ent['original_url'])
    politica(ent['policy'])
    ent['policy'] = ent['policy'].upper()
    from .policy24 import numero
    ent['priority']=f"{numero(ent.get('priority','0'),1):X}"
    if not isinstance(ent.get('priority_sectors',[]),list) or any(x not in ('fedora','debian','alpine') for x in ent.get('priority_sectors',[])):raise ValueError('Sector de prioridad inválido.')
    for nom in ('family','release','architecture','kind'):
        if not isinstance(ent.get(nom), str) or not ent[nom] or len(ent[nom]) > 160:
            raise ValueError('Campo requerido: '+nom)
    ent['filename'] = nombre(ent)
    if ent.get('sha256') and not re.fullmatch('[0-9a-fA-F]{64}', ent['sha256']):
        raise ValueError('SHA-256 inválido.')
    if ent.get('size_bytes') is not None and (type(ent['size_bytes']) is not int or ent['size_bytes'] <= 0):
        raise ValueError('Tamaño inválido.')
    ent.setdefault('artifact_type', 'iso' if ent['filename'].endswith('.iso') else 'component')
    if not isinstance(ent.get('paths',{}),dict):raise ValueError('paths debe ser un objeto de ubicaciones.')
    for pth in ent.get('paths', {}).values():
        rel_segura(pth)
    if ent.get('deployment_size_bytes') is not None and (type(ent['deployment_size_bytes']) is not int or ent['deployment_size_bytes']<0):raise ValueError('Tamaño de deploy inválido.')
    for cmp in ent.get('components', []):
        url_publica(cmp['original_url'])
    if ent.get('remote_only') and politica(ent['policy']) & 0xB:
        raise ValueError('Un menú remoto mantiene política de origen; resolver primero sus artefactos.')
    if ent.get('recipe'):
        from .catalog_profile import valida_receta
        rec = dict(ent['recipe'])
        aprobado = rec.pop('approved', False)
        if type(aprobado) is not bool: raise ValueError('recipe.approved debe ser booleano.')
        valida_receta(rec)
        if rec['entry_id'] != ent['id']: raise ValueError('La receta debe pertenecer al recurso.')
        for arg in rec['kernel_args']:
            if '=' in arg and arg.split('=',1)[1].startswith(('http://','https://')):url_publica(arg.split('=',1)[1])
    ent['identity'] = identidad(ent)
    ent['artifact_identity'] = identidad_artefacto(ent)
    return ent


def valida_plan(dat):
    if not isinstance(dat,dict):raise ValueError('planning debe ser un objeto.')
    allowed={'presets','ram_budget_gib','ssd_budget_gib','ram_reserve_percent','preset_ram_gib','preset_ssd_gib','ssd_mode'}
    if set(dat)-allowed:raise ValueError('Campo de previsión desconocido.')
    if not isinstance(dat.get('presets',[]),list) or any(x not in ('alpine','fedora','debian') for x in dat.get('presets',[])):raise ValueError('Presets de previsión inválidos.')
    for key,value in dat.items():
        if key in ('presets','ssd_mode'):continue
        if type(value) not in (int,float) or not 0<=value<=1048576 or (key!='ram_reserve_percent' and not value):raise ValueError('Límite de previsión inválido: '+key)
    if not 0<=dat.get('ram_reserve_percent',0)<100:raise ValueError('Reserva inválida.')
    if dat.get('ssd_mode','extract') not in ('mount','extract'):raise ValueError('Modo SSD inválido.')
    return copy.deepcopy(dat)


def carga(pth=None, config=None):
    cfg = lee_config(config)
    pth = Path(pth) if pth else ruta_cfg(cfg, 'catalog_file', 'catalog.json', ruta_config(config))
    dat = json.loads(pth.read_text())
    sin_secretos(dat)
    if dat.get('schema') != SCHEMA or not isinstance(dat.get('entries'), list):
        raise ValueError('Se requiere un catálogo AUX 8; usar catalog migrate para importar una selección anterior.')
    if 'planning' in dat:dat['planning']=valida_plan(dat['planning'])
    if 'planning' in dat:dat['planning']=valida_plan(dat['planning'])
    dat['entries'] = [valida(ent) for ent in dat['entries']]
    ids = [ent['id'] for ent in dat['entries']]
    if len(ids) != len(set(ids)):
        raise ValueError('El catálogo contiene ID duplicados.')
    return dat


def guarda(pth, dat):
    dat = copy.deepcopy(dat)
    sin_secretos(dat)
    dat['entries'] = [valida(ent) for ent in dat['entries']]
    ids = [e['id'] for e in dat['entries']]
    if len(set(ids)) != len(ids):
        raise ValueError('ID de recurso duplicado.')
    dat['schema'] = SCHEMA
    dat['updated_at'] = ahora()
    guarda_json(pth, dat)
    arc=Path(pth)
    from .common import atomico
    atomico(str(arc)+'.sha256',hashlib.sha256(arc.read_bytes()).hexdigest()+'  '+arc.name+'\n')


def huella(dat):
    return hashlib.sha256(json.dumps(dat['entries'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def raiz_artefacto(ent):
    # Preserve/archive never replace an older artifact behind an unchanged filename.
    return str(Path('artifacts') / ent['id'] / identidad_artefacto(ent))


def presets(ent):
    if ent.get('deploy_method') == 'chroot' and ent.get('procedure_url'):
        return ['alpine','fedora','debian']
    fam = ent['family'].lower()
    return [fam] if fam in ('alpine','fedora','debian') else []


def importa(pth, anterior):
    from importlib.util import spec_from_file_location, module_from_spec
    spec=spec_from_file_location('aux_import_metadata', DIR_APP/'src/common.py')
    mod=module_from_spec(spec);spec.loader.exec_module(mod)
    txt=Path(pth).read_text()
    if txt.lstrip().startswith('{'):
        dat=json.loads(txt)
        filas=dat.get('entries')
        if not isinstance(filas,list):raise ValueError('La importación JSON requiere entries.')
    else:
        filas=[]
        for lin in txt.splitlines():
            lin=lin.strip()
            if not lin or lin.startswith('#'):continue
            url_publica(lin);rec=mod.obt_meta(lin)
            filas.append({'id':re.sub('[^a-z0-9._-]','-',rec['filename'].lower())[:95],
                          'original_url':lin,'family':rec['family'],'release':rec.get('version') or 'pinned-url',
                          'architecture':rec['arch'],'kind':rec['format'].lower(),'policy':'004'})
    mapa={e['id']:copy.deepcopy(e) for e in anterior['entries']}
    for fila in filas:
        ent=copy.deepcopy(fila)
        ent.setdefault('policy',{'light':'115','heavy':'116','origin':'004'}.get(ent.get('selection_mode'),'004'))
        ent.setdefault('release','pinned-url');ent.setdefault('architecture','unknown');ent.setdefault('kind','component')
        ent=valida(ent);mapa[ent['id']]=ent
    planning=valida_plan(dat['planning']) if txt.lstrip().startswith('{') and 'planning' in dat else anterior.get('planning',{})
    return {**anterior,'planning':planning,'entries':list(mapa.values())}


def recursos_legacy(dat, tarea=None, destino=None, solo=None):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location('aux_v8_metadata', DIR_APP/'src/common.py')
    mod = module_from_spec(spec); spec.loader.exec_module(mod)
    sal = []
    for ent in dat['entries']:
        act = acciones(ent['policy'])
        if solo and solo.lower() not in (ent['id']+' '+ent['family']+' '+ent['filename']).lower(): continue
        if tarea == 'download' and not (act['download'] or act['update']): continue
        if destino and destino not in act['locations']: continue
        if ent.get('remote_only'): continue
        rec = mod.obt_meta(ent['original_url'])
        rec.update(catalog_id=ent['id'], policy=ent['policy'], sha256=ent.get('sha256'),
                   family=ent['family'], arch=ent['architecture'], version=ent['release'],
                   paths=ent.get('paths', {}), components=ent.get('components', []),
                   artifact_type=ent['artifact_type'], identity=ent['identity'])
        sal.append(rec)
    return sal


def refresca(dat, cfg, ids=()):
    from .catalog import consulta
    from .catalog_downloads import candidatos, coincide, orden_version
    arc = ruta_cfg(cfg, 'catalog_sources_file', 'config/catalog.sources.json')
    if not arc.is_file():raise ValueError('No existe el archivo de fuentes del catálogo: '+str(arc)+'. Configurar catalog_sources_file con aux-config; se conserva la ruta personalizada.')
    fuentes = json.loads(arc.read_text())
    origenes = {s['id']: s for s in fuentes.get('download_sources', [])}
    slots = fuentes.get('download_slots', [])
    pth_cache = ruta_cfg(cfg, 'metadata_cache', 'state/catalog-http')
    pth_cache.mkdir(parents=True, exist_ok=True)
    consultas, sal = {}, copy.deepcopy(dat)
    for ent in sal['entries']:
        if ids and ent['id'] not in ids: continue
        act = acciones(ent['policy'])
        if not act['crawl_level']: continue
        from .arch_netboot import admite as arch_admite,resuelve as arch_resuelve
        if arch_admite(ent['original_url']):
            ent.update(arch_resuelve(ent,pth_cache),resolved=True,resolved_at=ahora())
            ent['verification']={**ent.get('verification',{}),'source_signature':'passed','download_hash':'not-checked'}
            ent['origin']={**ent.get('origin',{}),'publisher_url':ent['original_url'],'index_url':'https://archlinux.org/releng/netboot/','checksum_url':None,'signature_url':ent['signature_source'],'metadata_observed_at':ahora()}
            continue
        if ent.get('recipe_owner')=='AUX':
            from .seed_recipes import RESOLVERS
            if ent['id'] in RESOLVERS:
                nuevo=RESOLVERS[ent['id']]()
                manual={k:copy.deepcopy(ent[k]) for k in ('policy','priority','priority_sectors') if k in ent}
                ent.clear();ent.update(nuevo,**manual);continue
        if ent.get('deploy_method')=='chroot' and ent.get('source_id')=='gentoo-stage3-amd64-openrc':
            from .catalog import descubre
            src={'id':ent['source_id'],'url':ent.get('source_index') or ent['original_url'],
                 'allowed_hosts':['distfiles.gentoo.org'],'format':'gentoo-latest',
                 'pattern':r'stage3-amd64-openrc-(?P<release>[0-9]{8}T[0-9]{6}Z)\.tar\.xz',
                 'defaults':{'family':'gentoo','release':'unresolved','architecture':'x86_64','kind':'chroot','download_class':'heavy'}}
            nuevo=descubre(src,pth_cache)[0]
            ent.update({k:v for k,v in nuevo.items() if k in ('original_url','release','sha256','size_bytes','checksum_source')})
            ent.update(source_index=src['url'],resolved=True,artifact_type='rootfs',resolved_at=ahora())
            ent['origin']={**ent.get('origin',{}),'publisher_url':ent['original_url'],'index_url':src['url'],'checksum_url':ent.get('checksum_source'),'metadata_observed_at':ent['resolved_at']}
            ent.pop('filename',None)
            continue
        matches = [s for s in slots if s['id'] == ent.get('source_id') or coincide(ent['original_url'], s)]
        if len(matches) != 1:
            raise ValueError('No hay una única regla de resolución para '+ent['id']+'; conservar la versión fijada.')
        slot = matches[0]; src = origenes[slot['source_id']]
        if src['id'].startswith('debian-testing-') and '/weekly-builds/' in src['url'] and not ent['original_url'].startswith(src['url'].rstrip('/')+'/'):
            raise ValueError('La regla de resolución corresponde a otra rama: '+ent['id']+'; configurar su fuente específica.')
        if src['id'] not in consultas:
            consultas[src['id']] = candidatos(src, pth_cache, consulta)
        encontrados = [x for x in consultas[src['id']] if coincide(x['original_url'], slot)]
        if not encontrados: raise ValueError('La fuente no produjo candidatos: '+ent['id'])
        nuevo = max(encontrados, key=lambda x: orden_version(x.get('release') or nombre(x)))
        if not act['resolve'] and nuevo['original_url'] != ent['original_url']:
            continue
        ent.update({k: v for k, v in nuevo.items() if k in ('original_url','sha256','size_bytes','release','checksum_source') and v is not None})
        if re.fullmatch(r'(?:testing|daily|rolling)-[0-9a-f]{12}',ent['release']) and ent.get('sha256'):
            ent['release']=ent['release'].split('-',1)[0]+'-'+ent['sha256'][:12]
        ent['source_index'] = src['url']; ent['resolved_at'] = ahora()
        ent['origin']={**ent.get('origin',{}),'publisher_url':ent['original_url'],'index_url':ent['source_index'],'checksum_url':ent.get('checksum_source'),'metadata_observed_at':ent['resolved_at']}
        ent.pop('filename', None)
        from .catalog_downloads import comprueba_enlace
        # Publisher Metalink already supplies exact size and the matching official sidecar.
        # A HEAD against its random mirror is not required to authenticate metadata.
        http={} if src['format']=='publisher-metalink' else comprueba_enlace(ent['original_url'],src['allowed_hosts'],ent.get('size_bytes'),src.get('mirror_redirect_origins',()))
        if http.get('size_bytes'):ent['size_bytes']=http['size_bytes']
        if ent.get('sha256') and ent.get('size_bytes'):ent['resolved']=True
    sal['entries'] = [valida(e) for e in sal['entries']]
    return sal
