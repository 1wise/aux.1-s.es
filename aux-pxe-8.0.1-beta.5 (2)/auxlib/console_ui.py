# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Shared terminal menuconfig widgets: indigo for configuration, cyan for execution.

Designed in Linux kernel menuconfig spirit: zero external GUI dependencies,
deterministic keyboard navigation, live "/" filtering, and clean fallback
when running on dumb terminals or serial consoles. Built to be hacked and forked!
"""
from contextlib import contextmanager
from contextvars import ContextVar
import curses
import sys
import textwrap

from . import VERSION
from .helptext import ayuda, descripcion, valida

# ContextVar keeps parent and child TUI themes isolated across nested invocations.
CONTEXTO = ContextVar('aux_console_context', default=('AUX', 'configuracion'))


@contextmanager
def aplicacion(nombre, tipo='configuracion'):
    """Bind the active application banner and color semantics for the current scope."""
    if tipo not in ('configuracion', 'ejecucion'):
        raise ValueError('Tipo de interfaz desconocido.')
    ficha = CONTEXTO.set((nombre, tipo))
    try:
        yield
    finally:
        CONTEXTO.reset(ficha)


def paleta(scr, tipo=None):
    """Initialize 256-color or ANSI 8-color pairs; degrade gracefully to monochrome."""
    tipo = tipo or CONTEXTO.get()[1]
    estilos = {
        'normal': 0,
        'titulo': curses.A_BOLD,
        'activo': curses.A_REVERSE,
        'detalle': 0,
        'ayuda': 0,
    }
    try:
        if not curses.has_colors():
            return estilos
        curses.start_color()
        # 256-color xterm indices: 54 = deep indigo, 51 = bright cyan.
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
        estilos.update(
            normal=curses.color_pair(1),
            titulo=curses.color_pair(2) | curses.A_BOLD,
            activo=curses.color_pair(3) | curses.A_BOLD,
            detalle=curses.color_pair(2),
            ayuda=curses.color_pair(2),
        )
    except curses.error:
        # Never crash if the terminal emulator lies about color support.
        pass
    return estilos


def texto(scr, estilos, y, x, txt, ancho, estilo='normal'):
    """Clip and render a single line safely inside the current terminal geometry."""
    h, w = scr.getmaxyx()
    if 0 <= y < h and x < w:
        try:
            scr.addnstr(y, x, str(txt), max(0, min(ancho, w - x - 1)), estilos[estilo])
        except curses.error:
            # Writing to the bottom-right corner can raise in curses; ignore it.
            pass


def cabecera(scr, estilos, titulo):
    """Draw the top identity bar and subtitle, returning current (height, width)."""
    nombre, tipo = CONTEXTO.get()
    h, w = scr.getmaxyx()
    modo_txt = 'INSTALAR / GENERAR' if tipo == 'ejecucion' else 'CONFIGURAR'
    texto(scr, estilos, 0, 0, f'{nombre}'+('' if VERSION in nombre else ' '+VERSION)+f' | {modo_txt}', w, 'titulo')
    texto(scr, estilos, 1, 0, titulo, w, 'detalle')
    return h, w


def ayuda_pantalla(scr, titulo, lineas=None):
    """Show scrollable help without replacing the caller's input or selection."""
    estilos = paleta(scr)
    pos = 0
    while True:
        scr.erase()
        h, w = cabecera(scr, estilos, 'AYUDA | ' + titulo)
        texto_all = []
        for lin in lineas or ayuda(titulo):
            texto_all.extend(textwrap.wrap(str(lin), max(1, w - 4)) or [''])
        alto = max(1, h - 5)
        pos = max(0, min(pos, max(0, len(texto_all) - alto)))
        for n, lin in enumerate(texto_all[pos:pos + alto], 3):
            texto(scr, estilos, n, 1, lin, w - 2)
        texto(scr, estilos, h - 1, 0, 'Flechas/AvPág: desplazar | Enter/Esc/F1: volver al mismo campo', w, 'ayuda')
        scr.refresh()
        tecla = scr.get_wch()
        if tecla in ('\n', '\r', '\x1b', 'q', 'Q', curses.KEY_ENTER, curses.KEY_F1):
            return
        if tecla in (curses.KEY_DOWN, curses.KEY_NPAGE):
            pos += alto if tecla == curses.KEY_NPAGE else 1
        elif tecla in (curses.KEY_UP, curses.KEY_PPAGE):
            pos -= alto if tecla == curses.KEY_PPAGE else 1


def lee_tecla(scr, titulo):
    tecla = scr.get_wch()
    if tecla == curses.KEY_F1:
        ayuda_pantalla(scr, titulo)
        return curses.KEY_RESIZE
    return tecla


def pantalla(scr, titulo, opciones, elegidos=(), multiple=False, categorias=None, detalles=None):
    """Two-panel menuconfig selector with group trees, live search, and detail view.

    Left panel (panel == 0): navigates categories or selectable items.
    Right panel (panel == 1): either scrolls the focused item's technical sheet
    (when `detalles` is provided in single-choice mode) or manages the active
    selection basket (in `multiple` checkbox mode).
    """
    scr.keypad(True)
    estilos = paleta(scr)
    ids = [nom for nom, _ in opciones]
    act = set(elegidos) & set(ids)
    pos = next((n for n, nom in enumerate(ids) if nom in act), 0)
    pos_sel = 0
    panel = 0
    grupo = None
    bus = ''
    categorias = categorias or {}
    if categorias:
        pos = 0
    pos_det = 0
    ult_det = None

    while True:
        scr.erase()
        h, w = cabecera(scr, estilos, titulo)
        # Guard minimum geometry so two-column layouts remain legible.
        if h < 16 or w < 80:
            texto(scr, estilos, 3, 0, 'Ampliar terminal a 80 columnas x 16 filas; Q cancela.', w)
            scr.refresh()
            if scr.get_wch() in ('q', 'Q', '\x1b'):
                raise KeyboardInterrupt
            continue

        # Build visible rows: either top-level category folders or filtered leaf options.
        if categorias and grupo is None:
            filas = [(None, 'Todas las opciones --->', 'todos')]
            filas += [(None, nom + ' --->', nom) for nom in sorted(set(categorias.values()))]
        else:
            filas = [
                (nom, rot, None) for nom, rot in opciones
                if (grupo in (None, 'todos') or categorias.get(nom) == grupo)
                and (not bus or bus.casefold() in (nom + ' ' + rot).casefold())
            ]

        pos = max(0, min(pos, len(filas) - 1))
        alto = h - 7
        mitad = w // 2
        inicio = max(0, pos - alto + 1)
        seleccionadas = [(nom, rot) for nom, rot in opciones if nom in act]
        pos_sel = max(0, min(pos_sel, len(seleccionadas) - 1))

        # Render column headers and vertical divider.
        texto(scr, estilos, 3, 0, ('> ' if panel == 0 else '  ') + 'DISPONIBLES', mitad - 2, 'titulo')
        modo_det = detalles is not None and not multiple
        tit_der = 'DETALLE DEL RECURSO' if modo_det else 'SELECCIONADAS'
        texto(scr, estilos, 3, mitad, ('> ' if panel == 1 else '  ') + tit_der, mitad - 1, 'titulo')
        for y in range(4, h - 3):
            texto(scr, estilos, y, mitad - 1, '|', 1, 'detalle')

        # Left panel: available options or group branches.
        for n, (nom, rot, _) in enumerate(filas[inicio:inicio + alto], inicio):
            marca = ('[' + ('x' if nom in act else ' ') + '] ') if multiple else ('(*) ' if nom in act else '( ) ')
            etq = (marca if nom is not None else '') + rot
            est_fila = 'activo' if panel == 0 and n == pos else 'normal'
            texto(scr, estilos, 4 + n - inicio, 0, etq, mitad - 2, est_fila)

        # Right panel: either scrollable resource details or selected items list.
        inicio_sel = max(0, pos_sel - alto + 1)
        detalle = []
        if modo_det and filas:
            nom_det = filas[pos][0]
            if nom_det != ult_det:
                pos_det = 0
                ult_det = nom_det
            for lin in detalles.get(nom_det, []):
                detalle.extend(textwrap.wrap(str(lin), max(1, mitad - 3), replace_whitespace=False) or [''])
            pos_det = max(0, min(pos_det, max(0, len(detalle) - alto)))
            for n, lin in enumerate(detalle[pos_det:pos_det + alto]):
                texto(scr, estilos, 4 + n, mitad, lin, mitad - 1)

        for n, (nom, rot) in enumerate([] if modo_det else seleccionadas[inicio_sel:inicio_sel + alto], inicio_sel):
            est_der = 'activo' if panel == 1 and n == pos_sel else 'normal'
            texto(scr, estilos, 4 + n - inicio_sel, mitad, rot, mitad - 1, est_der)

        # Bottom status and keybinding hints.
        est_barra = f"Grupo: {grupo or 'raíz'} | {len(act)} seleccionadas" + (f' | {bus}' if bus else '')
        texto(scr, estilos, h - 3, 0, est_barra, w, 'detalle')
        texto(scr, estilos, h - 2, 0, 'Flechas: mover | Enter: abrir/aceptar | Espacio: marcar | Tab: panel | S: guardar', w, 'ayuda')
        texto(scr, estilos, h - 1, 0, 'F1: ayuda | /: buscar | Retroceso: volver | Q/Esc: cancelar', w, 'ayuda')
        scr.refresh()

        tecla = scr.get_wch()
        if tecla == curses.KEY_F1:
            ayuda_pantalla(scr, titulo)
            continue
        if tecla in ('q', 'Q', '\x1b'):
            raise KeyboardInterrupt
        if tecla == '\t':
            panel = 1 - panel
            continue
        if tecla in ('s', 'S', curses.KEY_F10):
            if modo_det and filas:
                return filas[pos][0]
            if multiple:
                return [nom for nom in ids if nom in act]
            if act:
                return next(nom for nom in ids if nom in act)
            continue
        if tecla in (curses.KEY_BACKSPACE, 127, '\b'):
            grupo = None
            bus = ''
            pos = 0
            panel = 0
            continue
        if tecla in (curses.KEY_UP, curses.KEY_DOWN, 'j', 'k', curses.KEY_NPAGE, curses.KEY_PPAGE):
            paso = alto if tecla in (curses.KEY_NPAGE, curses.KEY_PPAGE) else 1
            if tecla in (curses.KEY_UP, 'k', curses.KEY_PPAGE):
                paso = -paso
            if panel and modo_det:
                pos_det = max(0, min(pos_det + paso, max(0, len(detalle) - alto)))
            elif panel:
                pos_sel = max(0, min(pos_sel + paso, len(seleccionadas) - 1))
            else:
                pos = max(0, min(pos + paso, len(filas) - 1))
        elif tecla in ('\n', '\r', curses.KEY_ENTER, ' '):
            if panel:
                if modo_det and filas:
                    return filas[pos][0]
                if seleccionadas and multiple and tecla == ' ':
                    act.remove(seleccionadas[pos_sel][0])
                elif tecla != ' ' and seleccionadas:
                    return [nom for nom in ids if nom in act] if multiple else next(iter(act))
                continue
            if not filas:
                continue
            nom, _, sub = filas[pos]
            if nom is None:
                grupo = sub
                pos = 0
                continue
            if not multiple:
                return nom
            if tecla != ' ':
                return [nom for nom in ids if nom in act]
            if nom in act:
                act.remove(nom)
            else:
                act.add(nom)
        elif tecla == '/':
            bus = campo_pantalla(scr, 'Buscar en las opciones', '')
            if grupo is None:
                grupo = 'todos'
            pos = 0
            panel = 0


def campo_pantalla(scr, titulo, defecto='', resumen=(), validar=None):
    """Single-line input prompt with an optional scrollable execution plan above it."""
    scr.keypad(True)
    estilos = paleta(scr)
    valor = str(defecto)
    inicio = 0
    error = ''
    validar = validar or (lambda val: valida(titulo, val))
    while True:
        scr.erase()
        h, w = cabecera(scr, estilos, titulo)
        alto = max(1, h - 8)
        inicio = max(0, min(inicio, max(0, len(resumen) - alto)))
        for n, lin in enumerate(resumen[inicio:inicio + alto], 3):
            texto(scr, estilos, n, 1, lin, w - 2)
        if not resumen:
            for n, lin in enumerate(textwrap.wrap(descripcion(titulo), max(1, w - 4))[:3], 3):
                texto(scr, estilos, n, 1, lin, w - 2, 'detalle')
        fila_in = h - 4 if resumen else min(h - 5, 7)
        texto(scr, estilos, fila_in, 2, '> ' + valor[-max(1, w - 6):], w - 4, 'activo')
        if resumen:
            texto(scr, estilos, h - 3, 0, 'Flechas / AvPág: desplazar el plan', w, 'detalle')
        texto(scr, estilos, h - 2, 0, 'F1: ayuda | Enter: aceptar | Retroceso: borrar | Ctrl+U: limpiar | Esc: cancelar', w, 'ayuda')
        texto(scr, estilos, h - 1, 0, error, w, 'detalle')
        scr.refresh()

        tecla = scr.get_wch()
        if tecla == curses.KEY_F1:
            ayuda_pantalla(scr, titulo)
            continue
        if tecla in ('\n', '\r', curses.KEY_ENTER):
            try:
                validar(valor.strip())
                return valor.strip()
            except (ValueError, OSError) as exc:
                error = str(exc)
                continue
        if tecla == '\x1b':
            raise KeyboardInterrupt
        if tecla in (curses.KEY_BACKSPACE, 127, '\b', '\x7f'):
            valor = valor[:-1]
        elif tecla == '\x15':
            # Ctrl+U clears the entire input line, matching standard readline behavior.
            valor = ''
        elif tecla in (curses.KEY_DOWN, curses.KEY_NPAGE):
            inicio += alto if tecla == curses.KEY_NPAGE else 1
        elif tecla in (curses.KEY_UP, curses.KEY_PPAGE):
            inicio -= alto if tecla == curses.KEY_PPAGE else 1
        elif isinstance(tecla, str) and tecla.isprintable():
            valor += tecla


def campo(titulo, defecto='', resumen=(), validar=None):
    """Keep invalid fields and plans in place until accepted or explicitly cancelled."""
    validar = validar or (lambda val: valida(titulo, val))
    if sys.stdin.isatty() and sys.stdout.isatty():
        return curses.wrapper(campo_pantalla, titulo, str(defecto), resumen, validar)
    valor = str(defecto)
    print(descripcion(titulo))
    if resumen:
        print('\n'.join(str(lin) for lin in resumen))
    while True:
        txt = input(titulo + (' [' + valor + ']' if valor else '') + ' (?ayuda; :cancelar): ').strip()
        if txt == ':cancelar':
            raise KeyboardInterrupt
        if txt == '?ayuda':
            print('\n'.join(ayuda(titulo)))
            continue
        valor = txt or valor
        try:
            validar(valor)
            return valor
        except (ValueError, OSError) as exc:
            print('Campo pendiente: ' + str(exc))



def selecciona(titulo, opciones, elegidos=(), multiple=False, categorias=None, detalles=None):
    """Launch the two-panel curses selector and return the chosen ID(s)."""
    return curses.wrapper(pantalla, titulo, opciones, elegidos, multiple, categorias, detalles)
