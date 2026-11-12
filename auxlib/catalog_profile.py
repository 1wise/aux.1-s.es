# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Keep replica choices and reviewed boot recipes separate from AUX defaults."""
import copy
import hashlib
import datetime
import json
from pathlib import Path
import re
import tempfile
import os
from urllib.parse import urlsplit,parse_qsl

from .common import DIR_APP, guarda_json, identificador

RUTA_PERFIL=DIR_APP/'state/catalog-profile.json'
MODOS=('light','heavy','origin')


def url_perfil(txt, vacia=False):
    if vacia and txt=='':return txt
    from .catalog import url_segura
    if not isinstance(txt,str) or len(txt)>2048:raise ValueError('URL de perfil inválida.')
    url_segura(txt)
    if re.search(r'[$<>"\\\s]',txt):raise ValueError('La URL no es apta para un perfil de catálogo.')
    if any(k.lower() in ('key','api_key','token','access_token','password') for k,_ in parse_qsl(urlsplit(txt).query)):
        raise ValueError('No guardar credenciales en URL del catálogo.')
    return txt


def limites_perfil(dat):
    if not isinstance(dat,dict) or set(dat)!={'ram_gib','ssd_gib','reserve_percent'}:
        raise ValueError('Límites de perfil inválidos.')
    for nom,maximo in [('ram_gib',1024),('ssd_gib',1048576)]:
        val=dat[nom]
        if type(val) not in (int,float) or not 0<val<=maximo:raise ValueError('Presupuesto inválido: '+nom)
    if type(dat['reserve_percent']) not in (int,float) or not 0<=dat['reserve_percent']<100:
        raise ValueError('Reserva RAM inválida.')
    return dict(dat)


def url_receta(txt):
    # HTTP is useful for a configured PXE mirror; verification still requires its local inventory.
    if isinstance(txt,str) and txt.startswith('http://'):
        url_perfil('https://'+txt[7:])
    else:
        url_perfil(txt)
    return txt


def valida_receta(dat):
    claves={'entry_id','label','type','architecture','firmware','kernel_url','initrd_url','kernel_args','menu_url'}
    if not isinstance(dat,dict) or set(dat)!=claves:raise ValueError('Receta estructurada inválida.')
    identificador(dat['entry_id'])
    if dat['type'] not in ('linux','provider-menu'):raise ValueError('Tipo de receta desconocido.')
    if dat['architecture'] not in ('x86_64','i386','arm64'):raise ValueError('Arquitectura de receta inválida.')
    if dat['firmware'] not in ('any','bios','uefi'):raise ValueError('Firmware de receta inválido.')
    if not isinstance(dat['label'],str) or not 0<len(dat['label'])<=120 or any(ord(c)<32 for c in dat['label']):
        raise ValueError('Etiqueta de receta inválida.')
    args=dat['kernel_args']
    if not isinstance(args,list) or len(args)>32 or any(not isinstance(x,str) or len(x)>256 or not re.fullmatch(r'[A-Za-z0-9_.,/:?=%+@-]+',x) for x in args):
        raise ValueError('Argumento de kernel no admitido; usar datos, nunca comandos.')
    if dat['type']=='linux':
        url_receta(dat['kernel_url']);url_receta(dat['initrd_url'])
        if '&' in dat['kernel_url'] or '&' in dat['initrd_url']:raise ValueError('Usar URL simples en la receta de arranque.')
        if dat['menu_url']:raise ValueError('Una receta Linux no declara menu_url.')
    else:
        url_perfil(dat['menu_url']);part=urlsplit(dat['menu_url'])
        if part.netloc!='boot.netboot.xyz' or part.query or not re.fullmatch(r'/[A-Za-z0-9_-]+\.ipxe',part.path):
            raise ValueError('El menú externo debe pertenecer a boot.netboot.xyz.')
        if dat['kernel_url'] or dat['initrd_url'] or args:raise ValueError('Una receta de proveedor no declara kernel ni argumentos.')
    return copy.deepcopy(dat)


def valida_perfil(dat):
    def sin_credenciales(valor):
        if isinstance(valor,dict):
            if any(str(k).lower() in ('api_key','apikey','password','authorization','access_token','secret') for k in valor):
                raise ValueError('El perfil no admite credenciales.')
            for item in valor.values():sin_credenciales(item)
        elif isinstance(valor,list):
            for item in valor:sin_credenciales(item)
    sin_credenciales(dat)
    campos={'schema','name','limits','default','entries','recipes','sources','created_at','assist'}
    if not isinstance(dat,dict) or set(dat)!=campos or dat.get('schema')!='aux-catalog-profile-v1':
        raise ValueError('Perfil de catálogo inválido; no admite claves API ni comandos.')
    if not isinstance(dat['name'],str) or not 0<len(dat['name'])<=100:raise ValueError('Nombre de perfil inválido.')
    fecha=dat['created_at']
    if not isinstance(fecha,str) or len(fecha)>64 or any(ord(c)<32 for c in fecha):raise ValueError('Fecha de perfil inválida.')
    try:datetime.datetime.fromisoformat(fecha)
    except ValueError:raise ValueError('La fecha del perfil debe usar ISO 8601.') from None
    limites_perfil(dat['limits'])
    if type(dat['default']) is not bool:raise ValueError('default debe ser booleano.')
    if not isinstance(dat['entries'],list) or len(dat['entries'])>1000:raise ValueError('Demasiadas entradas en el perfil.')
    ids=set();locales={}
    for ent in dat['entries']:
        identificador(ent['id']);url_perfil(ent['original_url'])
        if ent['id'] in ids:raise ValueError('ID de perfil duplicado.')
        ids.add(ent['id'])
        if ent.get('selection_mode') not in MODOS:raise ValueError('Modo de despliegue inválido.')
        if ent.get('download_class') not in ('light','heavy'):raise ValueError('Clase de imagen inválida.')
        for nom in ('family','release','architecture','kind','name'):
            if not isinstance(ent.get(nom),str) or not ent[nom] or len(ent[nom])>200:raise ValueError('Entrada incompleta: '+nom)
        peso=ent.get('size_bytes')
        if peso is not None and (type(peso) is not int or peso<=0):raise ValueError('Tamaño de archivo inválido.')
        if ent['selection_mode']!='origin' and not peso:raise ValueError('Un tamaño desconocido debe permanecer como origen.')
        if ent['selection_mode']!='origin':
            from .catalog_downloads import nombre_archivo
            nom=nombre_archivo(ent['original_url'])
            if nom in locales and locales[nom]!=ent['original_url']:raise ValueError('Dos descargas locales comparten nombre: '+nom)
            locales[nom]=ent['original_url']
    if not isinstance(dat['recipes'],list) or len(dat['recipes'])>64:raise ValueError('Demasiadas recetas.')
    usados=set()
    for receta in dat['recipes']:
        if set(receta)!={'recipe','approved','http','hardware_boot'}:raise ValueError('Registro de receta inválido.')
        rec=valida_receta(receta['recipe'])
        if rec['entry_id'] not in ids or rec['entry_id'] in usados:raise ValueError('La receta necesita una entrada única del perfil.')
        usados.add(rec['entry_id'])
        if type(receta['approved']) is not bool or receta['http'] not in ('passed','failed','not-checked') or receta['hardware_boot']!='not-tested':
            raise ValueError('La aprobación local no es una prueba de arranque.')
        if receta['approved'] and receta['http']!='passed':raise ValueError('Una receta sin comprobar no entra en el menú.')
    if not isinstance(dat['sources'],list) or len(dat['sources'])>32:raise ValueError('Fuentes de perfil inválidas.')
    fuentes=set()
    for item in dat['sources']:
        if not isinstance(item,dict) or set(item)!={'source','slot'}:raise ValueError('Fuente de perfil inválida.')
        src,slot=item['source'],item['slot']
        if set(slot)!={'id','source_id','filename_pattern','family','architecture','kind','label','channel','download_class'}:
            raise ValueError('Selector de fuente inválido.')
        identificador(slot['id'])
        pat=slot['filename_pattern'];token=r'(?P<release>[A-Za-z0-9._+-]+)'
        if not isinstance(pat,str) or len(pat)>400:raise ValueError('Patrón de fuente inválido.')
        glob=re.sub(r'\\(.)',r'\1',pat.replace(token,'*'))
        if not re.fullmatch(r'[A-Za-z0-9._*+-]+',glob) or glob.count('*')>1 or re.escape(glob).replace(r'\*',token)!=pat:
            raise ValueError('El perfil requiere un patrón simple de archivo.')
        if set(src)-{'id','url','format','allowed_hosts','checksums_url'}:raise ValueError('Opciones de fuente no admitidas.')
        identificador(src['id']);url_perfil(src['url'])
        if src['id'] in fuentes or slot.get('source_id')!=src['id']:raise ValueError('Fuente duplicada o sin relación con su selector.')
        fuentes.add(src['id'])
        if src.get('checksums_url'):url_perfil(src['checksums_url'])
        if src.get('format') not in ('artifact-html','artifact-rss','github-assets','alpine-releases'):raise ValueError('Adaptador de perfil no admitido.')
        if not isinstance(src.get('allowed_hosts'),list) or not src['allowed_hosts'] or any(not isinstance(h,str) or not re.fullmatch(r'[A-Za-z0-9.-]+',h) for h in src['allowed_hosts']):
            raise ValueError('Los hosts de una fuente nueva se revisan como nombres exactos.')
    if not isinstance(dat['assist'],dict) or set(dat['assist'])-{'provider','model'}:raise ValueError('No guardar credenciales ni conversaciones en el perfil.')
    if dat['assist']:
        if dat['assist'].get('provider') not in ('openai','gemini') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',str(dat['assist'].get('model',''))):
            raise ValueError('Proveedor o modelo del perfil inválido.')
        if dat['assist']['model'].startswith(('sk-','AIza')):raise ValueError('El modelo del perfil no admite una clave API.')
    from .catalog_selection import cabe_catalogo
    lim=dat['limits'];ram=int(lim['ram_gib']*1024**3)
    if not cabe_catalogo(dat['entries'],{'ram':int(ram*(1-lim['reserve_percent']/100)),'ssd':int(lim['ssd_gib']*1024**3)}):
        raise ValueError('El perfil supera el presupuesto de archivos.')
    return copy.deepcopy(dat)


def carga_perfil(pth=None):
    arc=Path(pth) if pth else RUTA_PERFIL
    if not arc.is_file():
        if pth:raise ValueError('No existe el perfil: '+str(arc))
        return None
    if arc.stat().st_size>2097152:raise ValueError('Perfil demasiado grande.')
    return valida_perfil(json.loads(arc.read_text()))


def perfil_desde_seleccion(entradas,nombre,limites,predeterminado=False,recetas=(),fuentes=(),assist=None):
    return valida_perfil({'schema':'aux-catalog-profile-v1','name':nombre,'limits':dict(limites),
        'default':predeterminado,'entries':copy.deepcopy(list(entradas)),'recipes':copy.deepcopy(list(recetas)),
        'sources':copy.deepcopy(list(fuentes)),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'assist':dict(assist or {})})


def config_desde_perfil(perfil,base):
    from .catalog_downloads import coincide,nombre_archivo
    cfg=copy.deepcopy(base);cfg['entries']=[];cfg['download_slots']=[];cfg['sync_rules']=[]
    fuentes={s['id']:copy.deepcopy(s) for s in base.get('download_sources',[])}
    slots=list(base.get('download_slots',[]))
    for item in perfil['sources']:
        # Only compiled source/slot pairs are accepted; never execute provider-supplied code.
        if set(item)!={'source','slot'}:raise ValueError('Fuente de perfil inválida.')
        fuentes[item['source']['id']]=copy.deepcopy(item['source']);slots.append(copy.deepcopy(item['slot']))
    grupos={};vistos=set()
    for ent in perfil['entries']:
        if ent['selection_mode']=='origin':continue
        candidatos=[s for s in slots if coincide(ent['original_url'],s)]
        if len(candidatos)==1:grupos.setdefault(candidatos[0]['id'],set()).add(ent['original_url'])
    for ent in perfil['entries']:
        if ent['selection_mode']=='origin':cfg['entries'].append(copy.deepcopy(ent));continue
        if ent['original_url'] in vistos:continue
        vistos.add(ent['original_url'])
        candidatos=[s for s in slots if coincide(ent['original_url'],s)]
        if len(candidatos)==1 and len(grupos[candidatos[0]['id']])==1:slot=copy.deepcopy(candidatos[0])
        else:
            sid='profile-'+ent['id'][:40];host=urlsplit(ent['original_url']).hostname
            fuentes[sid]={'id':sid,'url':ent['original_url'],'format':'fixed','allowed_hosts':[host],
                          'artifacts':[{'original_url':ent['original_url'],'release':ent['release']}]}
            slot={'id':sid,'source_id':sid,'filename_pattern':re.escape(nombre_archivo(ent['original_url'])),
                  'family':ent['family'],'architecture':ent['architecture'],'kind':ent['kind'],
                  'channel':'pinned-url','release':ent['release'],'label':ent['name']}
        slot['download_class']=ent['selection_mode'];cfg['download_slots'].append(slot)
        cfg['sync_rules'].append({'source_id':slot['id'],'filename_pattern':slot['filename_pattern']})
    usados={s['source_id'] for s in cfg['download_slots']}
    cfg['download_sources']=[s for nom,s in fuentes.items() if nom in usados]
    cfg['download_lists']={'all':'url.txt','light':'light-url.txt','heavy':'heavy-url.txt'}
    cfg['storage']={'enabled':False,'ids':[],'max_images':0,'max_total_bytes':0}
    return cfg


def exporta_perfil(perfil,destino,base):
    perfil=valida_perfil(perfil);destino=Path(destino).expanduser().absolute()
    if destino.exists():raise ValueError('Elegir un directorio nuevo para el perfil.')
    if not destino.parent.is_dir():raise ValueError('No existe el directorio padre del perfil.')
    with tempfile.TemporaryDirectory(prefix='.aux-profile-',dir=destino.parent) as tmp:
        raiz=Path(tmp);guarda_json(raiz/'aux-catalog-profile.json',perfil)
        guarda_json(raiz/'recipes.manifest.json',registro_recetas(perfil))
        guarda_json(raiz/'crawler.sources.json',config_desde_perfil(perfil,base))
        for modo in MODOS:
            nom='origin' if modo=='origin' else modo
            (raiz/(nom+'-url.txt')).write_text(''.join(url+'\n' for url in dict.fromkeys(e['original_url'] for e in perfil['entries'] if e['selection_mode']==modo)))
        (raiz/'url.txt').write_text(''.join(url+'\n' for url in dict.fromkeys(e['original_url'] for e in perfil['entries'] if e['selection_mode']!='origin')))
        menu=menu_recetas(perfil)
        cab=['#!ipxe','# Timestamp: '+perfil['created_at']+' | Version: aux-catalog-profile-v1',
             '# Author & Credits: https://www.alawise.es/1-s','set menu_arch ${buildarch}',
             'iseq ${buildarch} i386 && cpuid --ext 29 && set menu_arch x86_64 ||',
             'goto custom_recipes' if menu else 'exit']
        (raiz/'menu-custom.ipxe').write_text('\n'.join(cab+menu+[':start','exit','']))
        os.rename(raiz,destino)
    return destino


def activa_perfil(perfil,pth=None):
    dat=valida_perfil(perfil);arc=Path(pth) if pth else RUTA_PERFIL
    if arc.exists():guarda_json(arc.with_name(arc.name+'.before-profile'),json.loads(arc.read_text()))
    guarda_json(arc,dat)


def menu_recetas(perfil):
    from .remote_menu import rotulo
    recetas=[r['recipe'] for r in perfil['recipes'] if r['approved'] and r['http']=='passed']
    if not recetas:return []
    lin=['',':custom_recipes','set menu_back custom_recipes','set auto_timeout 0',
         'menu Custom recipes / reviewed / hardware not tested']
    for rec in recetas:lin.append('item custom_'+rec['entry_id']+' '+rotulo(rec['label']))
    lin+=['item start Back','choose target && goto ${target} || goto start']
    for rec in recetas:
        lin+=['',':custom_'+rec['entry_id'],'iseq ${menu_arch} '+rec['architecture']+' || goto custom_incompatible']
        if rec['firmware']!='any':lin.append('iseq ${platform} '+('efi' if rec['firmware']=='uefi' else 'pcbios')+' || goto custom_incompatible')
        lin+=['echo Reviewed custom recipe. Hardware boot test pending.',
              'prompt Press a key to boot or Esc to return... || goto custom_recipes']
        if rec['type']=='linux':
            lin+=['imgfree','kernel '+rec['kernel_url']+' '+' '.join(rec['kernel_args'])+' initrd=aux-profile-initrd || goto custom_error',
                  'initrd --name aux-profile-initrd '+rec['initrd_url']+' || goto custom_error','boot || goto custom_error']
        else:
            cod=urlsplit(rec['menu_url']).path.rsplit('/',1)[-1].removesuffix('.ipxe')
            lin+=['set arch ${menu_arch}','chain --autofree https://boot.netboot.xyz/boot.cfg || goto custom_error',
                  'set menu '+cod,'chain --autofree '+rec['menu_url']+' || goto custom_error']
        lin+=['goto custom_recipes']
    lin+=['',':custom_incompatible','echo Incompatible architecture or firmware.','prompt Press a key...','goto custom_recipes',
          ':custom_error','echo Custom recipe failed.','prompt Press a key...','goto custom_recipes']
    return lin


def lanzador_receta(perfil,entry_id):
    """Export one locally approved recipe using the same renderer as menu.ipxe."""
    from . import VERSION
    dat=valida_perfil(perfil)
    dat['recipes']=[r for r in dat['recipes'] if r['recipe']['entry_id']==entry_id and r['approved'] and r['http']=='passed']
    if not dat['recipes']:return None
    return '\n'.join(['#!ipxe','# Timestamp: '+dat['created_at']+' | Version: '+VERSION,
        '# Author & Credits: https://www.alawise.es/1-s','set menu_arch ${buildarch}',
        'iseq ${buildarch} i386 && cpuid --ext 29 && set menu_arch x86_64 ||',
        'goto custom_recipes']+menu_recetas(dat)+[':start','exit',''])


def registro_recetas(perfil):
    """Publish reviewed revisions as stable interchange data for a future recipe tracker."""
    from . import VERSION
    salida={'schema':'aux-recipes-v1','version':VERSION,'entries':[]}
    if not perfil:return salida
    dat=valida_perfil(perfil);entradas={e['id']:e for e in dat['entries']}
    for rec in dat['recipes']:
        if not rec['approved'] or rec['http']!='passed':continue
        rcp=rec['recipe'];ent=entradas[rcp['entry_id']]
        medio={k:ent.get(k) for k in ('original_url','family','release','architecture','sha256')}
        revision={'recipe':rcp,'media':medio}
        rid=hashlib.sha256(json.dumps(revision,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        salida['entries'].append({'id':rid,**copy.deepcopy(revision),
            'launcher':'origins/custom_'+hashlib.sha256(rcp['entry_id'].encode()).hexdigest()[:20]+'.ipxe',
            'review':{'http':'passed-on-review','hardware_boot':'not-tested','profile_saved_at':dat['created_at']},
            'profile_assistance':copy.deepcopy(dat['assist'])})
    return salida
