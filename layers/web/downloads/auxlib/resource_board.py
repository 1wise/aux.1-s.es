# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
# Author & Credits: https://www.alawise.es/1-s
"""Coordinate one resource per row without turning observations into policies."""
import copy
import curses
import json
from pathlib import Path
import sys
from .catalog_v8 import carga,guarda,ruta_cfg,valida
from .settings import lee_config,ruta_config
from .status_view import BITS,datos
from .console_ui import aplicacion,cabecera,paleta,texto,ayuda_pantalla,campo

TAREAS={'c':'checkstatus','d':'download','p':'deploy','g':'generate','s':'save','b':'bastion'}


def palabra(ent,obs):
    return f"{(int(obs.get('word24','0'),16)&0xff000)|int(ent['policy'],16)|(int(ent.get('priority','0'),16)<<20):06X}"


def editable(ent,bit):
    return bit in range(24) and not 12<=bit<=19 and not (ent.get('remote_only') and bit in (0,1,3))


def conmuta(ent,bit):
    if not editable(ent,bit):raise ValueError('A/S son observaciones o el destino no admite este artefacto.')
    ent=copy.deepcopy(ent);key='priority' if bit>=20 else 'policy';shift=bit-20 if bit>=20 else bit
    ent[key]=f"{int(ent.get(key,'0'),16)^(1<<shift):0{1 if bit>=20 else 3}X}"
    return valida(ent)


def celdas(ent,obs):
    word=int(palabra(ent,obs),16);known=int(obs.get('known_observation_mask','0'),16)
    return ['?' if b['readonly'] and not known&(1<<b['bit']) else 'x' if word&(1<<b['bit']) else '.' for b in BITS]


def filtra(entries,bus):
    return [e for e in entries if bus.casefold() in ' '.join(str(e.get(k,'')) for k in ('id','name','family','release','architecture','original_url')).casefold()]


def comandos(tarea,config=None,catalog=None,apply=False):
    if tarea not in ('checkstatus','download','deploy','generate'):raise ValueError('Fase desconocida.')
    argv=[tarea]
    if config:argv+=['--config',str(config)]
    if catalog:argv+=['--catalog',str(catalog)]
    if tarea!='checkstatus':argv+=['--apply'] if apply else ['--dry-run']
    return argv


def capacidad(cat,cfg):
    from types import SimpleNamespace
    from .v8 import plan
    dat=plan(cat,cfg,SimpleNamespace(command='catalog',resource=None,only=None,apply=False,dry_run=True,mode=None))
    return ' | '.join(k.upper()+f" {dat['selected_bytes'][k]/1024**3:.1f}/{dat['budget_bytes'][k]/1024**3:.1f} GiB" for k in ('ram','ssd','bastion'))+(' EXCEDIDO' if dat['over_budget'] else '')


def pantalla(scr,cat,estado):
    scr.keypad(True);est=paleta(scr);pos=0;col=0;bus='';buscar=False;aviso=''
    while True:
        rows=filtra(cat['entries'],bus);pos=max(0,min(pos,len(rows)-1));scr.erase();h,w=cabecera(scr,est,'TABLERO PASCDE | '+str(len(rows))+' recursos | / '+bus)
        ancho=max(8,min(42,w-48));inicio=ancho+2;alto=max(1,h-10);prim=max(0,min(pos-alto//2,len(rows)-alto));texto(scr,est,3,0,'Recurso',ancho,'titulo')
        for g,n in enumerate('PASCDE'):texto(scr,est,3,inicio+g*7,n+' 4 bits',7,'titulo')
        for idx,ent in enumerate(rows[prim:prim+alto],prim):
            y=4+idx-prim;cells=celdas(ent,estado['entries'].get(ent['id'],{}));texto(scr,est,y,0,(ent.get('name') or ent['id'])+' '+ent['release']+' '+ent['architecture'],ancho,'activo' if idx==pos else 'normal')
            for g in range(6):
                texto(scr,est,y,inicio+g*7,'['+''.join(cells[g*4:g*4+4])+']',6)
                if idx==pos and col//4==g:texto(scr,est,y,inicio+g*7+1+col%4,cells[col],1,'activo')
        if rows:
            ent=rows[pos];obs=estado['entries'].get(ent['id'],{});bit=BITS[col];texto(scr,est,h-6,0,palabra(ent,obs)+' | '+str(bit['bit'])+' '+bit['group']+' '+bit['label']+' | '+ent['id'],w,'detalle')
        from .bastion_status import resumen as estado_bastion
        texto(scr,est,h-5,0,aviso or (estado_bastion(estado['cfg'])+' | RED ROBIN: carga y escrituras' if estado.get('cfg') else 'RED ROBIN: carga, cuotas y escrituras. x activo | . inactivo | ? desconocido'),w,'detalle')
        if estado.get('cfg'):texto(scr,est,h-4,0,capacidad(cat,estado['cfg']),w,'detalle')
        texto(scr,est,h-3,0,'Flechas: fila/casilla | Espacio: editar | /: buscar | I: ficha | F1: ayuda',w,'ayuda')
        texto(scr,est,h-2,0,'S guardar | B Bastion | C status | D download | P deploy | G generate | Esc',w,'ayuda');scr.refresh();key=scr.get_wch()
        if buscar:
            if key in ('\n','\r',curses.KEY_ENTER):buscar=False
            elif key=='\x1b':buscar=False;bus=''
            elif key in (curses.KEY_BACKSPACE,127,'\x7f','\b'):bus=bus[:-1]
            elif isinstance(key,str) and key.isprintable():bus+=key
            pos=0;continue
        if key in ('\x1b','q','Q'):return 'back',cat
        if key=='/':buscar=True;continue
        if key in (curses.KEY_DOWN,curses.KEY_NPAGE):pos=min(len(rows)-1,pos+(alto if key==curses.KEY_NPAGE else 1))
        elif key in (curses.KEY_UP,curses.KEY_PPAGE):pos=max(0,pos-(alto if key==curses.KEY_PPAGE else 1))
        elif key==curses.KEY_LEFT:col=(col-1)%24
        elif key==curses.KEY_RIGHT:col=(col+1)%24
        elif key==curses.KEY_F1:
            from .precautions import lineas
            ayuda_pantalla(scr,'Tablero PASCDE',['24 casillas, bits 23 a 0. P/CDE editables; A/S solo cambian con observaciones.','/ filtra la vista, no el alcance de las fases. Las fases usan la politica completa.','I abre la ficha. S revisa y guarda. Esc descarta ediciones pendientes.','B activa Bastion con la conexion guardada, tras revisar raiz y URL publica.','Generate necesita checkstatus vigente despues de download/deploy.']+lineas('load','writes','remote'))
        elif isinstance(key,str) and key.lower() in TAREAS:return TAREAS[key.lower()],cat
        elif rows and key in ('i','I','\n','\r',curses.KEY_ENTER):ayuda_pantalla(scr,ent['id'],json.dumps({'resource':ent,'observations':obs},ensure_ascii=False,indent=2).splitlines())
        elif rows and key==' ':
            try:cat['entries'][cat['entries'].index(ent)]=conmuta(ent,BITS[col]['bit']);aviso='Cambio pendiente: S revisa y guarda.'
            except ValueError as exc:aviso=str(exc)


def consola(cat,estado):
    for e in cat['entries']:
        obs=estado['entries'].get(e['id'],{});cells=celdas(e,obs);print(e['id']+' | '+palabra(e,obs)+' | '+' '.join('['+''.join(cells[n:n+4])+']' for n in range(0,24,4)))
    cmd=campo('Tablero: ID BIT, info ID, save, bastion, checkstatus, download, deploy, generate o back','back')
    if cmd.startswith('info '):
        ent=next(e for e in cat['entries'] if e['id']==cmd[5:]);campo('Ficha; Enter vuelve al tablero',resumen=json.dumps(ent,indent=2).splitlines());return 'edit',cat
    if cmd in ('back','save','bastion','checkstatus','download','deploy','generate'):return cmd,cat
    uid,bit=cmd.rsplit(' ',1);idx=next(i for i,e in enumerate(cat['entries']) if e['id']==uid);cat['entries'][idx]=conmuta(cat['entries'][idx],int(bit));return 'edit',cat


def exige(esperado):
    def validar(value):
        if value!=esperado:raise ValueError('Escribir '+esperado+' o cancelar para volver al tablero.')
    return validar


def interactivo(config=None,catalog=None):
    cfg=lee_config(config);pth=Path(catalog) if catalog else ruta_cfg(cfg,'catalog_file','catalog.json',ruta_config(config));original=carga(pth,config);cat=copy.deepcopy(original)
    with aplicacion('AUX TABLERO 24 BITS','configuracion'):
        while True:
            try:
                cfg=lee_config(config);estado=datos(cat['entries'],pth,ruta_cfg(cfg,'status_file','state/status.json',ruta_config(config)));estado['cfg']=cfg
                tarea,cat=curses.wrapper(pantalla,cat,estado) if sys.stdin.isatty() and sys.stdout.isatty() else consola(cat,estado)
                if tarea=='back':return 0
                if tarea=='edit':continue
                if tarea=='bastion':
                    from .bastion_status import configura
                    configura(config);continue
                if cat!=original:
                    campo('Escribir APLICAR para guardar P/CDE',validar=exige('APLICAR'));guarda(pth,cat);original=copy.deepcopy(cat)
                if tarea=='save':continue
                from .v8 import main
                argv=comandos(tarea,config,pth)
                if tarea!='checkstatus':
                    main(argv);campo('Escribir EJECUTAR para aplicar el plan',validar=exige('EJECUTAR'));argv=comandos(tarea,config,pth,True)
                codigo=main(argv);cat=carga(pth,config);original=copy.deepcopy(cat);campo('Fase terminada (código '+str(codigo)+'). Enter vuelve al tablero')
            except KeyboardInterrupt:continue
            except (ValueError,OSError,StopIteration) as exc:campo('Acción pendiente; corregir y reintentar',resumen=[str(exc)])
