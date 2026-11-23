# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
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
    if (DIR_APP/'catalog.json').is_file():
        return []  # Canonical entries include portals, which are not downloadable filenames.
    return mod.obt_catalog((DIR_APP/'url.txt').read_text())


def modelo(recursos=None, aux='https://aux.1-s.es', tec='https://tec.1-s.es', catalog_file=None, profile_file=None, config=None):
    cfg=config or json.loads((DIR_APP/'fast-boot.json').read_text())
    if not config and cfg.get('status_file') and not Path(cfg['status_file']).is_absolute():cfg['status_file']=str(DIR_APP/cfg['status_file'])
    clases = {}
    if (DIR_APP/'catalog.json').is_file():
        for ent in json.loads((DIR_APP/'catalog.json').read_text())['entries']:
            clases[ent['original_url']] = 'light' if int(ent['policy'],16)&1 else 'heavy'
    else:
        for clase in ('light','heavy'):
            pth=DIR_APP/(clase+'-url.txt')
            for lin in pth.read_text().splitlines() if pth.is_file() else []:
                if lin.startswith('http'):clases[lin]=clase
    ents = []
    mapa = {rec.get('url'):rec for rec in recursos_iniciales()}
    remoto = DIR_APP/'config/catalog.remote.snapshot.json'
    iniciales = json.loads(remoto.read_text()).get('entries',[]) if remoto.is_file() else []
    from .catalog_workflow import lee_catalogo
    actuales=lee_catalogo(catalog_file or (DIR_APP/'catalog.json' if (DIR_APP/'catalog.json').is_file() else None))
    if (DIR_APP/'catalog.json').is_file():
        iniciales=[];mapa={}
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
        clave = rec.get('id') or rec.get('original_url',rec.get('url'))
        previo=mapa.get(clave,{})
        mapa[clave] = {**previo, **rec, 'id':previo['id'] if previo.get('policy') else rec['id']}
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
               'download_urls':{**rec.get('download_urls',{}),**rec.get('observed_downloads',{})},
               'remote_only':rec.get('remote_only',False),'project_url':rec.get('project_url'),
               'priority':rec.get('priority','0'),'priority_sectors':rec.get('priority_sectors',[]),'policy':rec.get('policy','004'),'word24':rec.get('word24'),'identity':__import__('auxlib.catalog_v8',fromlist=['identidad']).identidad(rec),
               'artifact_type':rec.get('artifact_type','iso'),'filename':rec.get('filename'),
               'paths':rec.get('paths',{}),'components':rec.get('components',[]),'recipe':rec.get('recipe'),
               'recipe_owner':rec.get('recipe_owner'),'recipe_notes':rec.get('recipe_notes'),'checksum_source':rec.get('checksum_source'),'mirrors':rec.get('mirrors',[]),'deploy_method':rec.get('deploy_method'),'procedure_url':rec.get('procedure_url'),
               'source_id':rec.get('source_id'),'resolved':rec.get('resolved',True),
               'presets':__import__('auxlib.catalog_v8',fromlist=['presets']).presets(rec) if rec.get('policy') else [],
               'source_index':rec.get('source_index'),'cached_previous':rec.get('cached_previous',False),
               'verification':rec.get('verification',{'download_hash':'not-checked','bios_boot':'not-tested','uefi_boot':'not-tested'})}
        if rec.get('local_path') and ent['verification'].get('download_hash') == 'passed':
            rel = Path(rec['local_path'])
            if not rel.is_absolute() and '..' not in rel.parts and rel.parts[0]=='downloads':
                ent['download_urls']['Copia local'] = aux.rstrip('/')+'/catalog/'+quote(str(rel),safe='/')
        for key in ('architectures','source_artifacts','proposed_boot_method','kernel_params_proposal','worker_queue','ram_min_mb_proposal','notes','provenance','signature_source','signature_verification','hash_origin','deployment_size_bytes'):
            if key in rec:ent[key]=rec[key]
        ents.append(ent)
    from .status_view import datos as datos_estado
    from .products import datos as datos_productos
    return {'custom_recipes':__import__('auxlib.catalog_profile',fromlist=['registro_recetas']).registro_recetas(perfil)['entries'] if perfil else [],'products':datos_productos(catalog_file),'status':datos_estado(actuales,catalog_file,cfg.get('status_file')),'version':VERSION, 'aux_url':aux.rstrip('/'), 'tec_url':tec.rstrip('/'),
            'roles':{nom:{'label':ROTULOS[nom], **vals} for nom, vals in ROLES.items()},
            'software':{dis:software.carga(dis) for dis in ('debian','fedora','alpine')},
            'native_defaults':{dis:software.defecto(dis) for dis in ('debian','fedora','alpine')},
            'kernel_native_defaults':{dis:software.minimo(dis) for dis in ('debian','fedora','alpine')},
            'templates':{'fedora':(DIR_APP/'profiles/fedora/installed.ks').read_text(),
                         'debian':(DIR_APP/'profiles/debian/preseed.cfg').read_text(),
                         'alpine':(DIR_APP/'profiles/alpine/apply-alpine.sh.in').read_text()},
            'catalog_presets':cfg.get('presets',{}),'capacity_defaults':__import__('auxlib.capacity',fromlist=['options']).options(cfg),
            'entries':ents}


def pagina(nom, dat):
    from .branding import meta_html,pie_imagen
    from .status_view import CONTENIDO
    cuerpos = {'status':CONTENIDO,'recipes':'','urls':'','adapt':'''<section class="hero"><p class="eyebrow">SELF-ASSAMBLERS / GPT Y GEMINI</p><h1>Self-assamblers.</h1><p>Autodescripción técnica de módulos, contratos y versiones. Carpeta de trabajo: <code>self-assamble/</code>. La adaptación se revisa como un diff y se guarda en una copia de trabajo nueva.</p></section><section class="panel"><label>Objetivo y uso propuesto<textarea id="evolve-goal" rows="5" maxlength="4000" placeholder="Rescate mínimo, aula de sistemas, instalación de laboratorio o actualización de módulos"></textarea></label><label>Asistente<select id="evolve-provider"><option value="openai">GPT / OpenAI</option><option value="gemini">Gemini</option></select></label><label>Modelo disponible en la cuenta<input id="evolve-model"></label><label>Max tokens<input id="evolve-tokens" type="number" min="512" max="16384" value="4096"></label><button id="evolve-export">Descargar solicitud de adaptación</button><pre>./aux self-assamble --request aux-adaptation-request.json --interactive
./aux evolve --describe
./aux evolve --proposal propuesta.json
./aux evolve --proposal propuesta.json --output /ruta/nueva/aux-adaptado --apply</pre><p>Revisar la solicitud en consola, consultar el proveedor y comprobar la copia generada antes de utilizarla.</p></section>''',
        'workspace':'''<section class="hero"><p class="eyebrow">SISTEMA INSTALADO · CATÁLOGO · ASISTENCIA</p><h1>Preparar. Instalar. Intervenir.</h1><p>Dos selectores, una instalación estándar y acceso guiado al sistema de destino.</p></section>
<section class="cards"><a class="card" href="installer.html"><span>01 / INSTALACIÓN</span><h2>Componer la suite</h2><p>Elegir Debian, Fedora o Alpine, preparar una ISO o una base nueva y seleccionar las herramientas, incluido aux-assist.</p><strong>Abrir selector →</strong></a>
<a class="card" href="catalogue.html"><span>02 / CATÁLOGO</span><h2>Elegir las descargas</h2><p>Filtrar distribuciones y arquitecturas. Editar políticas y exportar un único catalog.json.</p><strong>Abrir catálogo →</strong></a>
<a class="card" href="systems.html"><span>03 / SISTEMAS</span><h2>Entrar en una instalación</h2><p>Detección local, desbloqueo, inspección y chroot de reparación desde AUX Assist.</p><strong>Abrir herramientas →</strong></a>
<a class="card" href="@@TEC@@/"><span>04 / ASISTENCIA</span><h2>Trabajar con un técnico</h2><p>Cuenta, clave pública, segundo factor y dos terminales para la intervención autorizada.</p><strong>Abrir TEC →</strong></a></section>
<section class="panel"><h2>En el equipo de trabajo</h2><p>AUX Assist incorpora las opciones <b>B · Instalar</b>, <b>L · Catálogo</b>, <b>S · Sistemas</b> y <b>O · Cockpit</b>.</p><pre>sudo aux-assist</pre><p>La base conserva su gestor de paquetes y sus datos. La ISO es un instalador; la raíz nueva necesita completar la instalación del disco.</p></section>''',
        'installer':'''<section class="hero"><p class="eyebrow">SELECTOR DE LA EDICIÓN</p><h1>Componer la instalación.</h1><p>La misma selección sirve para instalar una base, ampliar un sistema o preparar el instalador ISO. Kernel Modeler prepara un banco de trabajo para configurar y construir núcleos.</p></section>
<div class="columns"><form id="setup-form" class="panel"><h2>1. Distribución y destino</h2><label>Distribución<select id="distribution"><option value="debian">Debian Testing · amd64</option><option value="fedora">Fedora Rawhide · x86_64</option><option value="alpine">Alpine edge · x86_64</option></select></label>
<label>Operación<select id="install-mode"><option value="iso">Preparar un instalador ISO</option><option value="root">Preparar una base nueva en un directorio vacío</option><option value="kernel-modeler">Kernel Modeler · banco de trabajo de núcleos</option><option value="existing">Instalar SOBRE EL SISTEMA ACTUAL · modifica ese equipo</option></select></label>
<div id="kernel-modeler-fields" hidden><label>Destino de Kernel Modeler<select id="kernel-target-mode"><option value="root">Raíz nueva en directorio vacío</option><option value="iso">Instalador ISO personalizado</option><option value="existing">SISTEMA ACTUAL · instala paquetes en este equipo</option></select></label><p>Preset de compilación, configuración Kconfig, ELF/BTF, initramfs, firma y laboratorio QEMU/OVMF. La base inicial es de consola y los complementos son ajustables. <a href="documentation.html#KERNEL-MODELER-8.md">Guía y límites</a>.</p></div><p id="target-description" class="notice" role="status">Preparar una ISO oficial personalizada para instalar en el equipo de destino.</p>
<label id="root-field" hidden>Raíz nueva<input id="root-path" value="/mnt/aux-root" spellcheck="false"></label>
<div id="iso-fields" hidden><label>ISO oficial de entrada<input id="iso-path" placeholder="/srv/iso/instalador.iso" spellcheck="false"></label><label>SHA-256 del medio comprobado<input id="iso-sha" maxlength="64" spellcheck="false"></label><label>ISO de salida<input id="iso-output" value="/srv/build/aux.iso" spellcheck="false"></label></div>
<fieldset class="identity-fields"><legend>Identidad del equipo de destino</legend><label class="check"><input id="identity-apply" type="checkbox">Personalizar hostname, locales, timezone y usuario</label><label>Hostname estable y único<input id="identity-hostname" placeholder="equipo-01" spellcheck="false"></label><label>Locale principal<input id="identity-locale" value="es_ES.UTF-8" spellcheck="false"></label><label>Zona horaria IANA<input id="identity-timezone" value="Europe/Andorra" spellcheck="false"></label><label>Usuario personal<input id="identity-user" placeholder="operador" spellcheck="false"></label><p>La contraseña se define localmente. La cuenta nueva de Fedora/Alpine queda bloqueada hasta asignarla; Debian la solicita en el instalador. osctrl puede usar el hostname como identificador.</p></fieldset><h2>2. Software de la distribución</h2><p id="software-source" class="muted"></p>
<label id="environment-field" hidden>Entorno base<select id="native-environment"></select></label><p id="environment-description" class="muted" hidden></p>
<label>Buscar tareas y grupos<input id="software-search" type="search" placeholder="Escritorio, servidor, idioma o identificador"></label>
<label class="check"><input id="software-advanced" type="checkbox"><span id="advanced-label">Mostrar tareas de idiomas</span></label>
<p id="software-count" role="status"></p><fieldset id="native-options" class="software-options"><legend>Tareas y grupos nativos</legend></fieldset>
<h2>3. Herramientas adicionales AUX</h2><fieldset id="role-options"><legend>Complementos de la suite</legend></fieldset><p class="muted">RED TEAM / Red Robin: aux-assist y administración remota son opcionales. aux-assist instala el cliente y su lanzador. En Debian/Fedora incluye servicios systemd de activación manual; en Alpine la ejecución es manual, sin unidades systemd. Desmarcar una herramienta conserva cualquier instalación anterior.</p></form>
<noscript><section class="panel"><h2>Instalación desde Links o Lynx</h2><p>Desde la carpeta de las fuentes, abrir el selector de consola:</p><pre>python3 aux-setup --interactive</pre><ol><li>Preparar un instalador ISO.</li><li>Preparar una base nueva en un directorio vacío.</li><li>Instalar sobre el sistema actual: modifica los paquetes y la configuración del equipo donde se ejecuta.</li></ol><p>aux-assist figura entre las herramientas adicionales seleccionables.</p></section></noscript>
<section class="panel summary"><h2>4. Revisar y continuar</h2><p id="selection-summary" role="status"></p><p id="setup-error" class="notice" hidden></p><p>El catálogo incluido es una instantánea de Debian Testing, Fedora Rawhide y Alpine edge. La disponibilidad y las dependencias se resuelven con el gestor de la distribución elegida.</p>
<div class="actions"><button id="download-selection" type="button">Descargar selección</button><button id="download-profile" type="button" class="secondary">Descargar perfil nativo</button></div>
<p class="muted">El perfil nativo selecciona software. El modo ISO añade también las aplicaciones AUX al instalador oficial.</p>
<h3>Mostrar el plan en el destino</h3><pre id="setup-plan"></pre><button type="button" data-copy-id="setup-plan" class="secondary">Copiar comando</button>
<h3 id="apply-heading">Aplicar la selección revisada</h3><pre id="setup-apply"></pre><p>Los comandos se ejecutan en el equipo donde se va a instalar. La web prepara los archivos de selección.</p>
<details><summary>Paquetes y grupos solicitados</summary><pre id="selected-packages"></pre></details></section></div>''',
        'catalogue':'''<section class="hero"><p class="eyebrow">CATÁLOGO REMOTO · ALMACENAMIENTO LOCAL LIMITADO</p><h1>Catálogo propio. Orígenes comprobados.</h1><p>Recetas propias, políticas CDE y referencias con fecha y resultado de auditoría. Elegir qué alojar y conservar los registros pendientes para corregirlos.</p><div class="actions"><a class="button" href="recipes.html">Libro de recetas AUX</a><a class="button secondary" href="status.html">Estado, 24 bits y JSON</a><a class="button secondary" href="urls.html">URL y mirrors comprobados</a></div><p>Los menús externos se mantienen en origen; las pruebas de arranque AUX se registran por separado.</p><p>Consultar a la comunidad: <a href="@@TEC@@/forum.php?board=urls">Encontrar URL y mirrors</a> · <a href="@@TEC@@/forum.php?board=deploy">Elegir despliegue</a> · <a href="@@TEC@@/forum.php?board=pxe">Recetas PXE</a>.</p></section>
<section class="panel"><div class="filters"><label>Buscar<input id="catalog-search" type="search" placeholder="Distribución, versión o herramienta"></label><label>Familia<select id="catalog-family"><option value="all">Todas</option></select></label><label>Arquitectura<select id="catalog-arch"><option value="all">Todas</option></select></label><label>Formato<select id="catalog-format"><option value="all">Todos</option></select></label></div>
<fieldset id="catalog-presets"><legend>Presets acumulables · autocompletan la selección</legend><label><input type="checkbox" value="alpine"> Alpine</label><label><input type="checkbox" value="fedora"> Fedora</label><label><input type="checkbox" value="debian"> Debian</label><label><input type="checkbox" value="todos"> Todos</label><p>Gentoo chroot y los procedimientos compartidos se incluyen en los tres.</p></fieldset>
<details class="capacity-panel" aria-labelledby="capacity-title"><summary>Previsión RAM / SSD / Bastion y presupuestos</summary><h2 id="capacity-title">Previsión de espacio</h2><p>10 GiB de RAM y 75 GiB de SSD por preset. Bastion tiene el mismo límite que SSD. Tres presets: 30 / 225 / 225 GiB. Los recursos compartidos se cuentan una vez; el margen puede asignarse a nuevas selecciones.</p><div class="capacity-fields"><label>RAM total (GiB)<input id="capacity-ram_budget_gib" type="number" min="1" max="1048576"></label><label>SSD / Bastion total (GiB)<input id="capacity-ssd_budget_gib" type="number" min="1" max="1048576"></label><label>RAM por preset (GiB)<input id="capacity-preset_ram_gib" type="number" min="1" max="1048576"></label><label>SSD / Bastion por preset (GiB)<input id="capacity-preset_ssd_gib" type="number" min="1" max="1048576"></label><label>Despliegue ISO en SSD<select id="capacity-ssd_mode"><option value="extract">Extraer archivos</option><option value="mount">Montar ISO</option></select></label></div><div class="table-scroll"><table><thead><tr><th>Destino</th><th>Imágenes GiB</th><th>Deploys GiB</th><th>Total GiB</th><th>Límite GiB</th><th>Margen GiB</th></tr></thead><tbody id="capacity-rows"></tbody></table></div><p id="capacity-notes" role="status" aria-live="polite"></p><p id="capacity-cache"></p><p id="capacity-deferred" role="status"></p><p>SSD incluye la caché y las copias públicas. Un árbol ISO extraído se estima con el tamaño de la imagen hasta medirlo. Un montaje RAM no duplica el árbol. Bastion recibe las imágenes. La previsión exportada respeta además los límites físicos de fast-boot.json al ejecutar.</p></details>
<section class="workflow-panel"><h2>Operar con la selección</h2><p>Una fila por recurso y 24 casillas, bits 23–0. P/CDE editables; A/S observados. Raya: desconocido. Login requiere una prueba real hasta la pantalla de acceso.</p><p id="audit-summary"></p><p id="workflow-summary" role="status"></p><div class="actions"><button type="button" data-board-task="checkstatus">Checkstatus</button><button type="button" data-board-task="download">Download</button><button type="button" data-board-task="deploy">Deploy</button><button type="button" data-board-task="generate">Generate</button></div><pre id="workflow-command">Elegir recursos y fase para mostrar los comandos.</pre><button type="button" class="secondary" data-copy-id="workflow-command">Copiar comandos</button><p>Descargar la selección como catalog.json. La web prepara comandos; se ejecutan en el equipo configurado. Después de download/deploy, actualizar checkstatus antes de generate.</p>@@ROBIN_LOAD@@</section><div class="actions"><label class="check"><input id="select-visible" type="checkbox"> Elegir los resultados visibles</label><span id="catalog-count" role="status"></span></div>
<div class="table-scroll"><table class="resource-board"><thead id="board-head"><tr><th>Elegir</th><th>Recurso</th><th>PASCDE</th><th>24 casillas</th><th>Ficha</th></tr></thead><tbody id="catalog-rows">@@CATALOG_ROWS@@</tbody></table></div>
<noscript><p>Los enlaces de origen funcionan desde Links o Lynx. Para seleccionar una publicación desde consola: <code>aux-catalog --interactive</code>.</p></noscript>
<div class="actions"><button id="export-catalog" disabled>Descargar selección catalog.json</button><button id="status-export" type="button" class="secondary">Descargar catálogo completo</button><button id="status-snapshot" type="button" class="secondary">Descargar observaciones JSON</button><label class="button secondary">Cargar estado de checkstatus<input id="status-import" type="file" accept=".json,application/json"></label></div><p>Política CDE editable. Estado A/S observado por checkstatus. RAM, SSD, origen y Bastion admiten selección conjunta.</p>
<details><summary>Leer el catálogo actualizado del servidor</summary><label>URL JSON<input id="catalog-live-url" value="@@AUX@@/catalog/catalog.json" spellcheck="false"></label><button id="load-live" type="button" class="secondary">Leer actualización</button><p id="catalog-live-status" role="status">La selección inicial conserva las URL conocidas; no declara sus imágenes verificadas.</p></details></section>''',
        'systems':'''<section class="hero"><p class="eyebrow">SISTEMAS Y ASISTENCIA</p><h1>Trabajar sobre el destino elegido.</h1><p>La detección y los montajes se realizan en el equipo intervenido.</p></section>
<section class="cards"><section class="panel"><h2>Entrada guiada a una instalación</h2><p>En AUX Assist: <b>S · Sistemas</b>. El asistente presenta los dispositivos y permite elegir inspección o reparación.</p><pre id="systems-command">aux-enter --interactive</pre><button class="secondary" data-copy-id="systems-command">Copiar comando para la terminal autorizada</button><p>La reparación identifica la raíz y solicita confirmación antes de abrirla con escritura.</p></section>
<section class="panel"><h2>Cockpit del equipo</h2><p>En AUX Assist: <b>O · Cockpit</b>. Se muestra la dirección del equipo y se puede iniciar el servicio local.</p><label>Dirección HTTPS de Cockpit<input id="cockpit-url" type="url" placeholder="https://equipo:9090" spellcheck="false"></label><button id="open-cockpit">Abrir Cockpit</button><p>Se utiliza una cuenta del sistema de destino.</p><p id="cockpit-status" role="status"></p></section></section>
<section class="panel"><h2>Instalación y catálogo en la misma sesión</h2><div class="actions"><a class="button" href="installer.html">Componer la suite</a><a class="button secondary" href="catalogue.html">Elegir descargas</a><a class="button secondary" href="@@TEC@@/">Abrir asistencia TEC</a></div><p>Las terminales autorizadas pueden ejecutar los asistentes locales. Los comandos copiados no se envían automáticamente a una shell que ya esté ocupada.</p></section>''',
    }
    if nom=='status':cuerpos[nom]=cuerpos['catalogue'].replace('Catálogo propio. Orígenes comprobados.','Estado y política. Un recurso por fila.')
    cuerpo = cuerpos[nom]
    if nom in ('recipes','urls'):
        from .products import contenido
        cuerpo=contenido(nom,dat['products'])
    if nom=='recipes':
        for rec in dat.get('custom_recipes',[]):
            cuerpo+='<article class="panel"><h2>'+html.escape(rec['recipe']['label'])+'</h2><p>Receta propia del perfil · HTTP revisado; arranque pendiente.</p><p>Revisión: <code>'+html.escape(rec['id'])+'</code></p><a href="'+html.escape(rec['launcher'],quote=True)+'">Lanzador iPXE</a></article>'
    from .precautions import html as precaucion
    cuerpo=cuerpo.replace('@@ROBIN_LOAD@@',precaucion('load'))
    if nom in ('installer','systems'):cuerpo=precaucion('remote')+precaucion('writes')+cuerpo
    cuerpo=cuerpo.replace('@@AUX@@',html.escape(dat['aux_url'],quote=True)).replace('@@TEC@@',html.escape(dat['tec_url'],quote=True))
    if nom in ('catalogue','status'):
        filas = []
        for ent in dat['entries']:
            link = '<a href="'+html.escape(ent['original_url'],quote=True)+'">'+('Menú remoto' if ent.get('remote_only') else 'Origen')+'</a>'
            copia = ent.get('download_urls',{}).get('bastion')
            if copia and urlsplit(copia).scheme in ('http','https'):
                link = '<a href="'+html.escape(copia,quote=True)+'">Bastion · France</a> · '+link
            if ent.get('project_url') and urlsplit(ent['project_url']).scheme in ('http','https'):
                link += ' · <a href="'+html.escape(ent['project_url'],quote=True)+'">Sitio original</a>'
            filas.append('<tr><td>'+('Sólo origen' if ent.get('remote_only') else '')+'</td><td>'+html.escape(ent['name'])+'<small>'+html.escape(ent['release'])+'</small></td>'+''.join('<td>'+html.escape(str(ent.get(campo,'004' if campo=='policy' else 'unknown')))+'</td>' for campo in ('policy',))+'<td><code>'+html.escape(dat['status']['entries'].get(ent['id'],{}).get('word24','000000'))+'</code></td><td>'+link+'</td></tr>')
        cuerpo = cuerpo.replace('@@CATALOG_ROWS@@',''.join(filas))
    tit = {'workspace':'Área de trabajo','installer':'Instalar y personalizar','catalogue':'Catálogo y selección','systems':'Sistemas y Cockpit','status':'Estado y 24 bits','recipes':'Libro de recetas','urls':'URL y mirrors','adapt':'Self-assamblers'}[nom]
    nav = ''.join('<a '+('aria-current="page" ' if nom==pag else '')+'href="'+pag+'.html">'+rot+'</a>' for pag,rot in [('workspace','Inicio'),('installer','Instalar'),('catalogue','Catálogo'),('status','Estado / JSON'),('recipes','Recetas'),('urls','URL / mirrors'),('adapt','Self-assamblers'),('systems','Sistemas')])
    emb = json.dumps(dat,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    social=meta_html(dat['aux_url'],dat['aux_url']+'/'+nom+'.html','AUX · '+tit)
    destacada=pie_imagen()
    return f'''<!doctype html>
<!-- Timestamp: 2026-11-10 | Version: {VERSION} | Author & Credits: https://www.alawise.es/1-s -->
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AUX · {tit}</title>{social}<link rel="icon" href="assets/favicon.png"><link rel="stylesheet" href="assets/workspace.css?v={VERSION}"><script src="assets/status.js?v={VERSION}" defer></script><script src="assets/workspace.js?v={VERSION}" defer></script></head>
<body data-app="{nom}"><header class="app-header"><a class="brand" href="workspace.html"><span>./</span>aux</a><span class="version">{VERSION}</span><nav aria-label="Aplicaciones AUX"><a href="installer.html">ISO y medios</a><a href="observability.html">Asistencia / osquery</a><a href="operations.html">Despliegue</a>{nav}<a href="{html.escape(dat['tec_url'],quote=True)}/forum.php">Foros AUX / TEC</a><a href="{html.escape(dat['tec_url'],quote=True)}/">Asistencia TEC ↗</a><a href="index.html">Repositorio ↗</a></nav></header><main>{cuerpo}</main><footer class="project-footer">{destacada}<div>Créditos, concepto y arquitectura · <a href="https://www.alawise.es/1-s">alawise.es/1-s</a></div></footer><p id="app-status" class="toast" role="status" hidden></p><script id="workspace-data" type="application/json">{emb}</script></body></html>'''


def publica_paginas(destino, recursos=None, aux='https://aux.1-s.es', tec='https://tec.1-s.es', catalog_file=None, profile_file=None, config=None):
    destino = Path(destino)
    dat = modelo(recursos,aux,tec,catalog_file,profile_file,config)
    from .precautions import guia
    atomico(destino/'precautions.html',guia())
    for nom in ('workspace','installer','catalogue','systems','status','recipes','urls','adapt'):
        atomico(destino/(nom+'.html'),pagina(nom,dat))
    for nom in ('red-robin.webp','blue-hibou.svg'):
        atomico(destino/'assets'/nom,(DIR_APP/'assets'/nom).read_bytes())
    for nom in ('workspace.css','workspace.js','status.js'):
        atomico(destino/'assets'/nom,(DIR_APP/'ui'/nom).read_bytes())
    if (DIR_APP/'assets/favicon.png').is_file():
        atomico(destino/'assets/favicon.png',(DIR_APP/'assets/favicon.png').read_bytes())
    atomico(destino/'assets/aux-featured.webp',(DIR_APP/'assets/aux-featured.webp').read_bytes())
    atomico(destino/'products.json',json.dumps(dat['products'],ensure_ascii=False,indent=2)+'\n')
    atomico(destino/'status-public.json',json.dumps(dat['status'],ensure_ascii=False,indent=2)+'\n')
    return dat
