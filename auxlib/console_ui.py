# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Shared terminal widgets: indigo configuration, cyan installation/generation."""
from contextlib import contextmanager
from contextvars import ContextVar
import curses
import sys

CONTEXTO = ContextVar('aux_console_context', default=('AUX', 'configuracion'))


@contextmanager
def aplicacion(nombre, tipo='configuracion'):
    if tipo not in ('configuracion', 'ejecucion'):
        raise ValueError('Tipo de interfaz desconocido.')
    ficha = CONTEXTO.set((nombre, tipo))
    try:
        yield
    finally:
        CONTEXTO.reset(ficha)


def paleta(scr, tipo=None):
    tipo = tipo or CONTEXTO.get()[1]
    estilos = {'normal':0, 'titulo':curses.A_BOLD, 'activo':curses.A_REVERSE,
               'detalle':0, 'ayuda':0}
    try:
        if not curses.has_colors():
            return estilos
        curses.start_color()
        indigo = 54 if curses.COLORS >= 256 else curses.COLOR_BLUE
        cyan = 51 if curses.COLORS >= 256 else curses.COLOR_CYAN
        fondo = cyan if tipo == 'ejecucion' else indigo
        tinta = indigo if tipo == 'ejecucion' else curses.COLOR_WHITE
        acento = indigo if tipo == 'ejecucion' else cyan
        curses.init_pair(1, tinta, fondo)
        curses.init_pair(2, acento, fondo)
        curses.init_pair(3, cyan if tipo == 'ejecucion' else indigo,
                         indigo if tipo == 'ejecucion' else cyan)
        scr.bkgdset(' ', curses.color_pair(1))
        estilos.update(normal=curses.color_pair(1), titulo=curses.color_pair(2)|curses.A_BOLD,
                       activo=curses.color_pair(3)|curses.A_BOLD,
                       detalle=curses.color_pair(2), ayuda=curses.color_pair(2))
    except curses.error:
        pass
    return estilos


def texto(scr, estilos, y, x, txt, ancho, estilo='normal'):
    h, w = scr.getmaxyx()
    if 0 <= y < h and x < w:
        try:
            scr.addnstr(y, x, str(txt), max(0, min(ancho, w-x-1)), estilos[estilo])
        except curses.error:
            pass


def cabecera(scr, estilos, titulo):
    nombre, tipo = CONTEXTO.get()
    h, w = scr.getmaxyx()
    texto(scr, estilos, 0, 0, nombre+' | '+('INSTALAR / GENERAR' if tipo=='ejecucion' else 'CONFIGURAR'), w, 'titulo')
    texto(scr, estilos, 1, 0, titulo, w, 'detalle')
    return h, w


def pantalla(scr, titulo, opciones, elegidos=(), multiple=False, categorias=None):
    """Select IDs in a tree while retaining choices across groups and filters."""
    scr.keypad(True)
    estilos = paleta(scr)
    ids = [nom for nom, _ in opciones]
    act = set(elegidos) & set(ids)
    pos = next((n for n, nom in enumerate(ids) if nom in act), 0)
    pos_sel = 0; panel = 0; grupo = None; bus = ''
    categorias = categorias or {}
    if categorias:pos=0
    while True:
        scr.erase();h,w = cabecera(scr, estilos, titulo)
        if h < 16 or w < 80:
            texto(scr, estilos, 3, 0, 'Ampliar terminal a 80 columnas x 16 filas; Q cancela.', w)
            scr.refresh()
            if scr.get_wch() in ('q','Q','\x1b'):
                raise KeyboardInterrupt
            continue
        if categorias and grupo is None:
            filas = [(None, 'Todas las opciones --->', 'todos')]
            filas += [(None, nom+' --->', nom) for nom in sorted(set(categorias.values()))]
        else:
            filas = [(nom, rot, None) for nom,rot in opciones
                     if (grupo in (None,'todos') or categorias.get(nom)==grupo)
                     and (not bus or bus.casefold() in (nom+' '+rot).casefold())]
        pos = max(0,min(pos,len(filas)-1));alto=h-7;mitad=w//2
        inicio=max(0,pos-alto+1)
        seleccionadas=[(nom,rot) for nom,rot in opciones if nom in act]
        pos_sel=max(0,min(pos_sel,len(seleccionadas)-1))
        texto(scr, estilos, 3, 0, ('> ' if panel==0 else '  ')+'DISPONIBLES', mitad-2,'titulo')
        texto(scr, estilos, 3, mitad, ('> ' if panel==1 else '  ')+'SELECCIONADAS', mitad-1,'titulo')
        for y in range(4,h-3):
            texto(scr, estilos, y, mitad-1, '|', 1, 'detalle')
        for n,(nom,rot,_) in enumerate(filas[inicio:inicio+alto],inicio):
            marca=('['+('x' if nom in act else ' ')+'] ') if multiple else ('(*) ' if nom in act else '( ) ')
            texto(scr, estilos, 4+n-inicio, 0, (marca if nom is not None else '')+rot, mitad-2,
                  'activo' if panel==0 and n==pos else 'normal')
        inicio_sel=max(0,pos_sel-alto+1)
        for n,(nom,rot) in enumerate(seleccionadas[inicio_sel:inicio_sel+alto],inicio_sel):
            texto(scr, estilos, 4+n-inicio_sel, mitad, rot, mitad-1,
                  'activo' if panel==1 and n==pos_sel else 'normal')
        texto(scr, estilos, h-3, 0, 'Grupo: '+str(grupo or 'raíz')+' | '+str(len(act))+' seleccionadas'+(' | '+bus if bus else ''), w, 'detalle')
        texto(scr, estilos, h-2, 0, 'Flechas: mover | Enter: abrir/aceptar | Espacio: marcar | Tab: panel | S: guardar', w, 'ayuda')
        texto(scr, estilos, h-1, 0, '/: buscar | Retroceso: volver | Q/Esc: cancelar', w, 'ayuda')
        scr.refresh();tecla=scr.get_wch()
        if tecla in ('q','Q','\x1b'):
            raise KeyboardInterrupt
        if tecla=='\t':panel=1-panel;continue
        if tecla in ('s','S',curses.KEY_F10):
            if multiple:return [nom for nom in ids if nom in act]
            if act:return next(nom for nom in ids if nom in act)
            continue
        if tecla in (curses.KEY_BACKSPACE,127,'\b'):
            grupo=None;bus='';pos=0;panel=0;continue
        if tecla in (curses.KEY_UP,curses.KEY_DOWN,'j','k',curses.KEY_NPAGE,curses.KEY_PPAGE):
            paso=alto if tecla in (curses.KEY_NPAGE,curses.KEY_PPAGE) else 1
            if tecla in (curses.KEY_UP,'k',curses.KEY_PPAGE):paso=-paso
            if panel:pos_sel=max(0,min(pos_sel+paso,len(seleccionadas)-1))
            else:pos=max(0,min(pos+paso,len(filas)-1))
        elif tecla in ('\n','\r',curses.KEY_ENTER,' '):
            if panel:
                if seleccionadas and multiple and tecla==' ':act.remove(seleccionadas[pos_sel][0])
                elif tecla!=' ' and seleccionadas:return [nom for nom in ids if nom in act] if multiple else next(iter(act))
                continue
            if not filas:continue
            nom,_,sub=filas[pos]
            if nom is None:grupo=sub;pos=0;continue
            if not multiple:return nom
            if tecla!=' ':return [nom for nom in ids if nom in act]
            if nom in act:act.remove(nom)
            else:act.add(nom)
        elif tecla=='/':
            bus=campo_pantalla(scr,'Buscar en las opciones','')
            if grupo is None:grupo='todos'
            pos=0;panel=0


def campo_pantalla(scr, titulo, defecto='', resumen=()):
    scr.keypad(True);estilos=paleta(scr);valor=defecto;inicio=0
    while True:
        scr.erase();h,w=cabecera(scr,estilos,titulo)
        alto=max(1,h-8)
        inicio=max(0,min(inicio,max(0,len(resumen)-alto)))
        for n,lin in enumerate(resumen[inicio:inicio+alto],3):
            texto(scr,estilos,n,1,lin,w-2)
        texto(scr,estilos,h-4 if resumen else 4,2,'> '+valor[-max(1,w-6):],w-4,'activo')
        if resumen:texto(scr,estilos,h-3,0,'Flechas / AvPág: desplazar el plan',w,'detalle')
        texto(scr,estilos,h-2,0,'Enter: aceptar | Retroceso: borrar | Ctrl+U: limpiar | Esc: cancelar',w,'ayuda')
        scr.refresh();tecla=scr.get_wch()
        if tecla in ('\n','\r',curses.KEY_ENTER):return valor.strip()
        if tecla=='\x1b':raise KeyboardInterrupt
        if tecla in (curses.KEY_BACKSPACE,127,'\b','\x7f'):valor=valor[:-1]
        elif tecla=='\x15':valor=''
        elif tecla in (curses.KEY_DOWN,curses.KEY_NPAGE):inicio+=alto if tecla==curses.KEY_NPAGE else 1
        elif tecla in (curses.KEY_UP,curses.KEY_PPAGE):inicio-=alto if tecla==curses.KEY_PPAGE else 1
        elif isinstance(tecla,str) and tecla.isprintable():valor+=tecla


def campo(titulo, defecto='', resumen=()):
    if sys.stdin.isatty() and sys.stdout.isatty():
        return curses.wrapper(campo_pantalla,titulo,str(defecto),resumen)
    return input(titulo+(' ['+str(defecto)+']' if defecto else '')+': ').strip() or str(defecto)


def selecciona(titulo, opciones, elegidos=(), multiple=False, categorias=None):
    return curses.wrapper(pantalla,titulo,opciones,elegidos,multiple,categorias)
