# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Render the same profile model into public and offline workspace applications."""
import html
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlsplit, quote

from . import VERSION
from .common import DIR_APP, atomico
from .profiles import ROLES, ROTULOS
from . import software

def recursos_iniciales():
    spec = importlib.util.spec_from_file_location('aux_catalog_metadata', DIR_APP / 'src/common.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.obt_catalog((DIR_APP / 'url.txt').read_text())


def modelo(recursos=None, aux='https://aux.1-s.es', tec='https://tec.1-s.es', catalog_file=None, profile_file=None):
    clases = {}
    for clase in ('light', 'heavy'):
        for lin in (DIR_APP / (clase + '-url.txt')).read_text().splitlines():
            url = lin.strip()
            if url and not url.startswith('#'):
                clases[url] = clase
    ents = []
    mapa = {rec.get('url'):rec for rec in recursos_iniciales()}
    remoto = DIR_APP/'config/catalog.remote.snapshot.json'
    iniciales = json.loads(remoto.read_text()).get('entries',[]) if remoto.is_file() else []
    from .catalog_workflow import lee_catalogo
    actuales=lee_catalogo(catalog_file)
    from .catalog_profile import carga_perfil
    perfil=carga_perfil(profile_file)
    if perfil:
        por_url={e['original_url']:e for e in actuales}
        personales=[]
        for ent in perfil['entries']:
            vigente=por_url.get(ent['original_url'],{})
            personales.append({**ent,**vigente,'id':ent['id'],'name':ent['name'],'selection_mode':ent['selection_mode']})
        actuales=actuales+personales
    ids_fuentes={ent.get('source_id') for ent in actuales if ent.get('source_id')}
    iniciales=[ent for ent in iniciales if ent.get('source_id') not in ids_fuentes]
    for rec in iniciales + actuales + list(recursos or []):
        clave = rec['id'] if rec.get('remote_only') else rec.get('original_url',rec.get('url'))
        mapa[clave] = rec
    for rec in mapa.values():
        url = rec.get('original_url', rec.get('url', ''))
        if urlsplit(url).scheme not in ('http', 'https'):
            continue
        ent = {'id':rec['id'], 'family':rec.get('family','other'),
               'release':str(rec.get('release') or rec.get('version') or 'sin versión declarada'),
               'architecture':rec.get('architecture',rec.get('arch','unknown')),
               'kind':str(rec.get('kind',rec.get('format','image'))).lower(),
               'download_class':rec.get('download_class',clases.get(url,'unclassified')),
               'original_url':url, 'sha256':rec.get('sha256'),
               'size_bytes':rec.get('size_bytes',rec.get('size')),
               'name':rec.get('name',rec.get('filename',rec['id'])),
               'download_urls':rec.get('download_urls',{}),
               'remote_only':rec.get('remote_only',False),'project_url':rec.get('project_url'),
               'source_index':rec.get('source_index'),'cached_previous':rec.get('cached_previous',False),
               'verification':rec.get('verification',{'download_hash':'not-checked','bios_boot':'not-tested','uefi_boot':'not-tested'})}
        if rec.get('local_path') and ent['verification'].get('download_hash') == 'passed':
            rel = Path(rec['local_path'])
            if not rel.is_absolute() and '..' not in rel.parts and rel.parts[0]=='downloads':
                ent['download_urls']['Copia local'] = aux.rstrip('/')+'/catalog/'+quote(str(rel),safe='/')
        ents.append(ent)
    return {'version':VERSION, 'aux_url':aux.rstrip('/'), 'tec_url':tec.rstrip('/'),
            'roles':{nom:{'label':ROTULOS[nom], **vals} for nom, vals in ROLES.items()},
            'software':{dis:software.carga(dis) for dis in ('debian','fedora')},
            'native_defaults':{dis:software.defecto(dis) for dis in ('debian','fedora')},
            'templates':{'fedora':(DIR_APP/'profiles/fedora/installed.ks').read_text(),
                         'debian':(DIR_APP/'profiles/debian/preseed.cfg').read_text()},
            'entries':ents}


def pagina(nom, dat):
    from .branding import meta_html,pie_imagen
    cuerpos = {
        'workspace':'''<section class="hero"><p class="eyebrow">SISTEMA INSTALADO · CATÁLOGO · ASISTENCIA</p><h1>Preparar. Instalar. Intervenir.</h1><p>Dos selectores, una instalación estándar y acceso guiado al sistema de destino.</p></section>
<section class="cards"><a class="card" href="installer.html"><span>01 / INSTALACIÓN</span><h2>Componer la suite</h2><p>Elegir Debian o Fedora, preparar una ISO o una base nueva y seleccionar las herramientas, incluido aux-assist.</p><strong>Abrir selector →</strong></a>
<a class="card" href="catalogue.html"><span>02 / CATÁLOGO</span><h2>Elegir las descargas</h2><p>Filtrar distribuciones y arquitecturas. Exportar la selección y las listas light/heavy.</p><strong>Abrir catálogo →</strong></a>
<a class="card" href="systems.html"><span>03 / SISTEMAS</span><h2>Entrar en una instalación</h2><p>Detección local, desbloqueo, inspección y chroot de reparación desde AUX Assist.</p><strong>Abrir herramientas →</strong></a>
<a class="card" href="@@TEC@@/"><span>04 / ASISTENCIA</span><h2>Trabajar con un técnico</h2><p>Cuenta, clave pública, segundo factor y dos terminales para la intervención autorizada.</p><strong>Abrir TEC →</strong></a></section>
<section class="panel"><h2>En el equipo de trabajo</h2><p>AUX Assist incorpora las opciones <b>B · Instalar</b>, <b>L · Catálogo</b>, <b>S · Sistemas</b> y <b>O · Cockpit</b>.</p><pre>sudo aux-assist</pre><p>La base conserva su gestor de paquetes y sus datos. La ISO es un instalador; la raíz nueva necesita completar la instalación del disco.</p></section>''',
        'installer':'''<section class="hero"><p class="eyebrow">SELECTOR DE LA EDICIÓN</p><h1>Componer la instalación.</h1><p>La misma selección sirve para instalar una base, ampliar un sistema o preparar el instalador ISO.</p></section>
<div class="columns"><form id="setup-form" class="panel"><h2>1. Distribución y destino</h2><label>Distribución<select id="distribution"><option value="debian">Debian · amd64</option><option value="fedora">Fedora 45 · x86_64</option></select></label>
<label>Operación<select id="install-mode"><option value="iso">Preparar un instalador ISO</option><option value="root">Preparar una base nueva en un directorio vacío</option><option value="existing">Instalar SOBRE EL SISTEMA ACTUAL · modifica ese equipo</option></select></label>
<p id="target-description" class="notice" role="status">Preparar una ISO oficial personalizada para instalar en el equipo de destino.</p>
<label id="root-field" hidden>Raíz nueva<input id="root-path" value="/mnt/aux-root" spellcheck="false"></label>
<div id="iso-fields" hidden><label>ISO oficial de entrada<input id="iso-path" placeholder="/srv/iso/instalador.iso" spellcheck="false"></label><label>SHA-256 del medio comprobado<input id="iso-sha" maxlength="64" spellcheck="false"></label><label>ISO de salida<input id="iso-output" value="/srv/build/aux.iso" spellcheck="false"></label></div>
<h2>2. Software de la distribución</h2><p id="software-source" class="muted"></p>
<label id="environment-field" hidden>Entorno base<select id="native-environment"></select></label><p id="environment-description" class="muted" hidden></p>
<label>Buscar tareas y grupos<input id="software-search" type="search" placeholder="Escritorio, servidor, idioma o identificador"></label>
<label class="check"><input id="software-advanced" type="checkbox"><span id="advanced-label">Mostrar tareas de idiomas</span></label>
<p id="software-count" role="status"></p><fieldset id="native-options" class="software-options"><legend>Tareas y grupos nativos</legend></fieldset>
<h2>3. Herramientas adicionales AUX</h2><fieldset id="role-options"><legend>Complementos de la suite</legend></fieldset><p class="muted">aux-assist instala el cliente, su lanzador y los servicios de asistencia con apertura manual. Desmarcar una herramienta conserva cualquier instalación anterior.</p></form>
<noscript><section class="panel"><h2>Instalación desde Links o Lynx</h2><p>Desde la carpeta de las fuentes, abrir el selector de consola:</p><pre>python3 aux-setup --interactive</pre><ol><li>Preparar un instalador ISO.</li><li>Preparar una base nueva en un directorio vacío.</li><li>Instalar sobre el sistema actual: modifica los paquetes y la configuración del equipo donde se ejecuta.</li></ol><p>aux-assist figura entre las herramientas adicionales seleccionables.</p></section></noscript>
<section class="panel summary"><h2>4. Revisar y continuar</h2><p id="selection-summary" role="status"></p><p id="setup-error" class="notice" hidden></p><p>El catálogo incluido es una instantánea de Debian Testing y Fedora 45. La disponibilidad y las dependencias se resuelven con el gestor de la distribución elegida.</p>
<div class="actions"><button id="download-selection" type="button">Descargar selección</button><button id="download-profile" type="button" class="secondary">Descargar perfil nativo</button></div>
<p class="muted">El perfil nativo selecciona software. El modo ISO añade también las aplicaciones AUX al instalador oficial.</p>
<h3>Mostrar el plan en el destino</h3><pre id="setup-plan"></pre><button type="button" data-copy-id="setup-plan" class="secondary">Copiar comando</button>
<h3 id="apply-heading">Aplicar la selección revisada</h3><pre id="setup-apply"></pre><p>Los comandos se ejecutan en el equipo donde se va a instalar. La web prepara los archivos de selección.</p>
<details><summary>Paquetes y grupos solicitados</summary><pre id="selected-packages"></pre></details></section></div>''',
        'catalogue':'''<section class="hero"><p class="eyebrow">CATÁLOGO REMOTO · ALMACENAMIENTO LOCAL LIMITADO</p><h1>Explorar todo. Alojar lo elegido.</h1><p>Menús netboot, versiones y enlaces de origen. Las imágenes locales requieren selección y presupuesto explícitos.</p><div class="actions"><a class="button" href="https://netboot.xyz/">Abrir netboot.xyz</a><a class="button secondary" href="https://netboot.xyz/downloads/">Cargadores de arranque del proveedor</a></div><p>Los menús externos se mantienen en origen; las pruebas de arranque AUX se registran por separado.</p></section>
<section class="panel"><div class="filters"><label>Buscar<input id="catalog-search" type="search" placeholder="Distribución, versión o herramienta"></label><label>Familia<select id="catalog-family"><option value="all">Todas</option></select></label><label>Arquitectura<select id="catalog-arch"><option value="all">Todas</option></select></label><label>Formato<select id="catalog-format"><option value="all">Todos</option></select></label></div>
<div class="actions"><label class="check"><input id="select-visible" type="checkbox"> Elegir los resultados visibles</label><span id="catalog-count" role="status"></span></div>
<div class="table-scroll"><table><thead><tr><th>Elegir</th><th>Recurso</th><th>Arquitectura</th><th>Formato</th><th>Clase</th><th>Procedencia</th></tr></thead><tbody id="catalog-rows">@@CATALOG_ROWS@@</tbody></table></div>
<noscript><p>Los enlaces de origen funcionan desde Links o Lynx. Para seleccionar una publicación desde consola: <code>aux-catalog --interactive</code>.</p></noscript>
<div class="actions"><button id="export-catalog" disabled>Descargar selección JSON</button><button id="export-light" class="secondary" disabled>Exportar light-url.txt</button><button id="export-heavy" class="secondary" disabled>Exportar heavy-url.txt</button></div>
<details><summary>Leer el catálogo actualizado del servidor</summary><label>URL JSON<input id="catalog-live-url" value="@@AUX@@/catalog/catalog.json" spellcheck="false"></label><button id="load-live" type="button" class="secondary">Leer actualización</button><p id="catalog-live-status" role="status">La selección inicial conserva las URL conocidas; no declara sus imágenes verificadas.</p></details></section>''',
        'systems':'''<section class="hero"><p class="eyebrow">SISTEMAS Y ASISTENCIA</p><h1>Trabajar sobre el destino elegido.</h1><p>La detección y los montajes se realizan en el equipo intervenido.</p></section>
<section class="cards"><section class="panel"><h2>Entrada guiada a una instalación</h2><p>En AUX Assist: <b>S · Sistemas</b>. El asistente presenta los dispositivos y permite elegir inspección o reparación.</p><pre id="systems-command">aux-enter --interactive</pre><button class="secondary" data-copy-id="systems-command">Copiar comando para la terminal autorizada</button><p>La reparación identifica la raíz y solicita confirmación antes de abrirla con escritura.</p></section>
<section class="panel"><h2>Cockpit del equipo</h2><p>En AUX Assist: <b>O · Cockpit</b>. Se muestra la dirección del equipo y se puede iniciar el servicio local.</p><label>Dirección HTTPS de Cockpit<input id="cockpit-url" type="url" placeholder="https://equipo:9090" spellcheck="false"></label><button id="open-cockpit">Abrir Cockpit</button><p>Se utiliza una cuenta del sistema de destino.</p><p id="cockpit-status" role="status"></p></section></section>
<section class="panel"><h2>Instalación y catálogo en la misma sesión</h2><div class="actions"><a class="button" href="installer.html">Componer la suite</a><a class="button secondary" href="catalogue.html">Elegir descargas</a><a class="button secondary" href="@@TEC@@/">Abrir asistencia TEC</a></div><p>Las terminales autorizadas pueden ejecutar los asistentes locales. Los comandos copiados no se envían automáticamente a una shell que ya esté ocupada.</p></section>''',
    }
    cuerpo = cuerpos[nom].replace('@@AUX@@',html.escape(dat['aux_url'],quote=True)).replace('@@TEC@@',html.escape(dat['tec_url'],quote=True))
    if nom == 'catalogue':
        filas = []
        for ent in dat['entries']:
            link = '<a href="'+html.escape(ent['original_url'],quote=True)+'">'+('Menú remoto' if ent.get('remote_only') else 'Origen')+'</a>'
            if ent.get('project_url') and urlsplit(ent['project_url']).scheme in ('http','https'):
                link += ' · <a href="'+html.escape(ent['project_url'],quote=True)+'">Sitio original</a>'
            filas.append('<tr><td>'+('Sólo origen' if ent.get('remote_only') else '')+'</td><td>'+html.escape(ent['name'])+'<small>'+html.escape(ent['release'])+'</small></td>'+''.join('<td>'+html.escape(str(ent[campo]))+'</td>' for campo in ('architecture','kind','download_class'))+'<td>'+link+'</td></tr>')
        cuerpo = cuerpo.replace('@@CATALOG_ROWS@@',''.join(filas))
    tit = {'workspace':'Área de trabajo','installer':'Instalar y personalizar','catalogue':'Catálogo y selección','systems':'Sistemas y Cockpit'}[nom]
    nav = ''.join('<a '+('aria-current="page" ' if nom==pag else '')+'href="'+pag+'.html">'+rot+'</a>' for pag,rot in [('workspace','Inicio'),('installer','Instalar'),('catalogue','Catálogo'),('systems','Sistemas')])
    emb = json.dumps(dat,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    social=meta_html(dat['aux_url'],dat['aux_url']+'/'+nom+'.html','AUX · '+tit)
    destacada=pie_imagen()
    return f'''<!doctype html>
<!-- Timestamp: 2026-11-10 | Version: {VERSION} | Author & Credits: https://www.alawise.es/1-s -->
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AUX · {tit}</title>{social}<link rel="icon" href="assets/favicon.png"><link rel="stylesheet" href="assets/workspace.css?v={VERSION}"><script src="assets/workspace.js?v={VERSION}" defer></script></head>
<body data-app="{nom}"><header class="app-header"><a class="brand" href="workspace.html">aux<span>.</span><i>/</i></a><span class="version">{VERSION}</span><nav aria-label="Aplicaciones AUX">{nav}<a href="{html.escape(dat['tec_url'],quote=True)}/">Asistencia TEC ↗</a><a href="index.html">Repositorio ↗</a></nav></header><main>{cuerpo}</main><footer class="project-footer">{destacada}<div>Créditos, concepto y arquitectura · <a href="https://www.alawise.es/1-s">alawise.es/1-s</a></div></footer><p id="app-status" class="toast" role="status" hidden></p><script id="workspace-data" type="application/json">{emb}</script></body></html>'''


def publica_paginas(destino, recursos=None, aux='https://aux.1-s.es', tec='https://tec.1-s.es', catalog_file=None, profile_file=None):
    destino = Path(destino)
    dat = modelo(recursos,aux,tec,catalog_file,profile_file)
    for nom in ('workspace','installer','catalogue','systems'):
        atomico(destino/(nom+'.html'),pagina(nom,dat))
    for nom in ('workspace.css','workspace.js'):
        atomico(destino/'assets'/nom,(DIR_APP/'ui'/nom).read_bytes())
    if (DIR_APP/'assets/favicon.png').is_file():
        atomico(destino/'assets/favicon.png',(DIR_APP/'assets/favicon.png').read_bytes())
    atomico(destino/'assets/aux-featured.png',(DIR_APP/'assets/aux-featured.png').read_bytes())
    return dat
