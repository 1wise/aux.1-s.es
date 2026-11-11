# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Review API proposals and export portable replica profiles from the terminal."""
import getpass
import json
import os
from pathlib import Path
import sys
import warnings

from .common import DIR_APP, guarda_json
from .console_ui import aplicacion, campo
from .interactive import elige,marca
from .catalog_profile import (limites_perfil,perfil_desde_seleccion,exporta_perfil,
                               activa_perfil,carga_perfil)
from .catalog_selection import incorpora_catalogo,uso_catalogo


def pide_limites():
    cfg=json.loads((DIR_APP/'fast-boot.json').read_text());previo=carga_perfil()
    defecto=previo['limits'] if previo else {'ram_gib':cfg.get('ram_budget_gib',28),
                'ssd_gib':cfg.get('ssd_budget_gib',100),'reserve_percent':cfg.get('ram_reserve_percent',10)}
    limites=limites_perfil({nom:float(campo(titulo,defecto[nom])) for nom,titulo in
        [('ram_gib','Presupuesto RAM (GiB)'),('ssd_gib','Presupuesto SSD (GiB)'),('reserve_percent','Reserva RAM (%)')]})
    ram=int(limites['ram_gib']*1024**3)
    calculo={'ram':int(ram*(1-limites['reserve_percent']/100)),'ssd':int(limites['ssd_gib']*1024**3)}
    return limites,calculo


def resumen_plan(entradas,recetas,avisos=()):
    uso=uso_catalogo(entradas)
    lineas=[f'{len(entradas)} entradas | RAM de archivos {uso["ram"]/1024**3:.2f} GiB | SSD {uso["ssd"]/1024**3:.2f} GiB',
            'La expansión y el consumo del sistema arrancado requieren espacio adicional.']
    lineas += [e['selection_mode'].upper()+' | '+e['name']+' | '+e['original_url'] for e in entradas]
    for rec in recetas:
        dat=rec['recipe'];lineas+=['RECETA '+dat['label']+' | '+dat['type']+' | HTTP '+rec['http']+' | '+('aprobada' if rec['approved'] else 'sin aprobar')+' | arranque sin probar',
                                  '  '+str(dat['kernel_url'] or dat['menu_url']),
                                  '  initrd: '+str(dat['initrd_url'])+' | args: '+' '.join(dat['kernel_args'])]
    return lineas+list(avisos)


def guarda_plan(entradas,limites,recetas,fuentes,asistente=None,avisos=()):
    nombre=campo('Nombre del perfil de esta réplica','Custom')
    pred=elige('Preset Default de esta réplica',[('Conservar Default de AUX',False),('Usar este perfil como Default',True)])
    elegibles=[r for r in recetas if r['http']=='passed']
    aprobadas=marca('Recetas comprobadas: marcar cuáles incluir en menu.ipxe',
        [(r['recipe']['entry_id'],r['recipe']['label']+' / '+r['recipe']['architecture']+' / '+r['recipe']['firmware']+' / arranque pendiente') for r in elegibles],
        [r['recipe']['entry_id'] for r in elegibles if r['approved']]) if elegibles else []
    recetas=[dict(r,approved=(r['recipe']['entry_id'] in aprobadas)) for r in recetas]
    plan=resumen_plan(entradas,recetas,avisos)
    accion=elige('Perfil revisado',[('Volver sin guardar','cancel'),('Exportar perfil portátil','export'),('Exportar y activar en esta réplica','activate')])
    if accion=='cancel':return None
    frase='ACTIVAR' if accion=='activate' else 'EXPORTAR'
    if campo('Escribir '+frase+' para guardar el plan',resumen=plan)!=frase:return None
    # Each recipe needs its own local checkbox; saving a profile never approves everything.
    perfil=perfil_desde_seleccion(entradas,nombre,limites,pred,recetas,fuentes,asistente)
    destino=Path(campo('Directorio nuevo para el perfil','../aux-catalog-custom')).expanduser()
    base=json.loads((DIR_APP/'config/catalog.sources.json').read_text())
    pth=exporta_perfil(perfil,destino,base)
    if accion=='activate':activa_perfil(perfil)
    campo('Perfil guardado. Enter vuelve',resumen=[str(pth),'Listas: url.txt, light-url.txt, heavy-url.txt, origin-url.txt',
        'Crawler: crawler.sources.json | Recetas revisadas: menu-custom.ipxe',
        'Las fuentes y recetas conservan sus estados de comprobación.'])
    return {'profile':perfil,'directory':pth,'activated':accion=='activate'}


@aplicacion('AUX CATALOG / PERFIL DE RÉPLICA','configuracion')
def perfil_interactivo(seleccion):
    limites,calculo=pide_limites();elegidos={};avisos=[]
    for ent in seleccion:
        copia=dict(ent)
        if copia.get('download_class') not in ('light','heavy'):copia['download_class']='heavy'
        motivo=incorpora_catalogo(copia,elegidos,calculo,copia.get('selection_mode','origin'))
        if motivo:avisos.append(copia['name']+': origen por '+motivo)
    anterior=carga_perfil();ids=set(elegidos)
    recetas=[r for r in anterior['recipes'] if r['recipe']['entry_id'] in ids] if anterior else []
    fuentes=anterior['sources'] if anterior else []
    return guarda_plan(list(elegidos.values()),limites,recetas,fuentes,avisos=avisos)


def _asistencia_interactiva(entradas,propuesta_file=None,taller=None):
    from . import catalog_assist as api
    if taller:
        limites=taller['limits'];ram=int(limites['ram_gib']*1024**3)
        calculo={'ram':int(ram*(1-limites['reserve_percent']/100)),'ssd':int(limites['ssd_gib']*1024**3)}
    else:limites,calculo=pide_limites()
    asistente={}
    if propuesta_file:
        if Path(propuesta_file).stat().st_size>131072:raise ValueError('Propuesta demasiado grande.')
        propuesta=json.loads(Path(propuesta_file).read_text())
    else:
        cfg_path=DIR_APP/'config/catalog.assist.json';cfg=json.loads(cfg_path.read_text())
        comun=json.loads((DIR_APP/'fast-boot.json').read_text()).get('ai',{})
        if comun.get('enabled') is False:raise ValueError('Asistencia API desactivada en fast-boot.json.')
        proveedor=elige('Proveedor para esta consulta',[('GPT / OpenAI','openai'),('Gemini / Google','gemini')])
        modelo=campo('Modelo API disponible en la cuenta',cfg[proveedor].get('model') or comun.get(proveedor,{}).get('model') or '')
        peticion_usr=campo('Objetivo: catálogo, modos o recetas iPXE',
            'Preparar hasta 8 recetas faltantes con los archivos publicados, conservando modos y arquitecturas.' if taller else '')
        reporte=DIR_APP/'state/catalog/crawl-report.json'
        informe=json.loads(reporte.read_text()) if reporte.is_file() else None
        contexto=api.contexto_catalogo(peticion_usr,entradas,limites,informe)
        if taller:
            contexto['deployment']=taller['context']
            while len(json.dumps(contexto).encode())>120000 and contexto['inventory']:contexto['inventory'].pop()
        vista=[proveedor+' / '+modelo,'Sólo se envían la petición, límites, catálogo público y fallos del rastreo.',
               f'Salida máxima: {cfg["max_output_tokens"]} tokens. Una llamada; sin reintentos automáticos.',
               peticion_usr,'El proveedor no ejecuta órdenes ni modifica el catálogo.']
        if taller:vista.append('Incluye inventario público de medios y archivos; se conservan la selección y sus modos.')
        if campo('Escribir CONSULTAR para enviar esta petición',resumen=vista)!='CONSULTAR':return None
        nombre_var='OPENAI_API_KEY' if proveedor=='openai' else 'GEMINI_API_KEY'
        clave=os.environ.get(nombre_var) or (os.environ.get('GOOGLE_API_KEY') if proveedor=='gemini' else '')
        if not clave:
            if not sys.stdin.isatty():raise ValueError('La clave API se introduce en una terminal con entrada oculta.')
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('error',getpass.GetPassWarning)
                    clave=getpass.getpass('Clave API temporal (sin eco): ').strip()
            except getpass.GetPassWarning:raise ValueError('No se puede ocultar la entrada de la clave en esta terminal.') from None
        print('Consultando '+proveedor+'; esperando una propuesta JSON...',flush=True)
        try:propuesta=api.consulta_propuesta(proveedor,modelo,clave,contexto,cfg['timeout_seconds'],cfg['max_output_tokens'])
        finally:clave=None
        asistente={'provider':proveedor,'model':modelo}
    if taller:
        from .recipe_workshop import valida_solo_recetas
        propuesta=valida_solo_recetas(propuesta,entradas)
    else:propuesta=api.valida_propuesta(propuesta,entradas)
    vista=[propuesta['summary']]+[s['mode'].upper()+' | '+s['entry_id']+' | '+s['reason'] for s in propuesta['selection']]
    for src in propuesta['sources']:
        vista += ['FUENTE '+src['label']+' | '+src['mode']+' | '+src['channel']+' | '+src['source_url'],
                  '  patrón: '+src['filename_glob']+' | referencia: '+src['reference_url']]
    for rec in propuesta['recipes']:vista.append('RECETA CANDIDATA '+rec['label']+' | '+rec['kernel_url']+' '+rec['initrd_url']+' '+rec['menu_url'])
    if campo('Escribir VERIFICAR para consultar las fuentes y cabeceras propuestas',resumen=vista)!='VERIFICAR':return None
    print('Verificando las fuentes propuestas; no se descargan imágenes...',flush=True)
    local=None
    if taller:
        from .recipe_workshop import comprueba_local,combina_recetas
        local=lambda rec,url:comprueba_local(taller,rec,url)
    seleccion,fuentes,recetas,avisos=api.verifica_propuesta(propuesta,entradas,calculo,DIR_APP/'state/catalog-assist-http',verifica_local=local,progreso=lambda txt:print(txt,flush=True))
    if taller:
        seleccion=taller['entries'];fuentes=taller['sources'];recetas=combina_recetas(taller['recipes'],recetas)
    return guarda_plan(seleccion,limites,recetas,fuentes,asistente,avisos)


@aplicacion('AUX CATALOG / GPT · GEMINI','configuracion')
def asistencia_interactiva(entradas,propuesta_file=None):
    return _asistencia_interactiva(entradas,propuesta_file)


@aplicacion('AUX RECETAS / MENU.IPXE','configuracion')
def recetas_interactivas(catalogo=None,seleccion=None,propuesta_file=None):
    from .recipe_workshop import carga_taller
    taller=carga_taller(catalogo,seleccion)
    if not taller['entries']:raise ValueError('No hay una selección válida para preparar recetas.')
    return _asistencia_interactiva(taller['entries'],propuesta_file,taller)
