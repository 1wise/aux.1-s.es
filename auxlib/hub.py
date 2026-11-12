# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Dispatch a persistent menu to existing applications without duplicating their logic."""
import argparse
import socket
import subprocess
import sys

from . import VERSION
from .common import DIR_APP
from .console_ui import aplicacion
from .interactive import elige

APLICACIONES = {
    'images': ('Imágenes y medios', 'aux-images', ('--interactive',)),
    'catalogue': ('Catálogo y recetas iPXE', 'aux-catalog', ('--interactive',)),
    'download': ('Descargar', 'download.sh', ('--interactive',)),
    'deploy': ('Desplegar', 'deploy.sh', ('--interactive',)),
    'generate': ('Generar índices web y menu.ipxe', 'generate.sh', ('--interactive',)),
    'systems': ('Sistemas y chroot', 'aux-enter', ('--interactive',)),
    'assist': ('Asistencia local · controles VT6', 'aux-assist', ()),
    'profiles': ('Perfiles de software', 'aux-profile', ('--interactive',)),
    'cockpit': ('Cockpit del equipo', 'aux-tools', ('--tool', 'cockpit')),
    'desktop': ('Área de trabajo web local', 'aux-tools', ('--gui',)),
    'installer': ('Instalar y personalizar', 'aux-setup', ('--interactive',)),
}
MENUS = {
    'root': ('Menú principal', (
        ('Preparar imágenes y medios --->', 'images'),
        ('Catálogo, selección y recetas iPXE --->', 'catalogue'),
        ('Servidor: descargar, desplegar y publicar --->', 'server'),
        ('Sistemas y chroot --->', 'systems'),
        ('Asistencia local · abrir controles VT6', 'assist'),
        ('Herramientas del equipo --->', 'tools'),
        ('Perfiles de software --->', 'profiles'),
        ('Instalar y personalizar · sistema actual al final --->', 'installer'),
        ('Salir', 'exit'),
    )),
    'server': ('Servidor AUX / PXE', (
        ('Descargar recursos --->', 'download'),
        ('Desplegar en RAM, disco o réplica --->', 'deploy'),
        ('Generar índices web y menu.ipxe --->', 'generate'),
        ('Volver al menú principal', 'back'),
    )),
    'tools': ('Herramientas del equipo', (
        ('Cockpit del equipo', 'cockpit'),
        ('Área de trabajo web local', 'desktop'),
        ('Volver al menú principal', 'back'),
    )),
}


def comando(nom):
    if nom not in APLICACIONES:
        raise ValueError('Aplicación AUX desconocida: ' + str(nom))
    _, archivo, args = APLICACIONES[nom]
    pth = DIR_APP / archivo
    if not pth.is_file():
        raise ValueError('Aplicación no disponible: ' + archivo + '. Revisar los componentes instalados.')
    # Use the installed source tree, never a same-named executable from another PATH.
    return (['bash'] if archivo.endswith('.sh') else [sys.executable]) + [str(pth), *args]


def abre(nom):
    try:
        return subprocess.run(comando(nom), check=False).returncode
    except KeyboardInterrupt:
        return 130


def navega():
    menu = 'root'
    posiciones = {}
    while True:
        titulo, opciones = MENUS[menu]
        try:
            with aplicacion('AUX ' + VERSION + ' | ' + socket.gethostname(), 'configuracion'):
                nom = elige(titulo, opciones, posiciones.get(menu, 1))
        except KeyboardInterrupt:
            if menu == 'root':
                return 0
            menu = 'root'
            continue
        posiciones[menu] = next(idx for idx, (_, val) in enumerate(opciones, 1) if val == nom)
        if nom == 'exit':
            return 0
        if nom == 'back':
            menu = 'root'
            continue
        if nom in MENUS:
            menu = nom
            continue
        try:
            cod = abre(nom)
            print('\n' + APLICACIONES[nom][0] + ' | ' +
                  ('Finalizado' if cod == 0 else 'Cancelado' if cod == 130 else 'Salida ' + str(cod)))
        except (OSError, ValueError, RuntimeError) as exc:
            print('\nAplicación detenida: ' + str(exc))
        try:
            input('Enter para volver al menú AUX: ')
        except KeyboardInterrupt:
            continue
        except EOFError:
            return 0


def main(argv=None):
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('-i', '--interactive', action='store_true', help='Open the unified menuconfig console')
    par.add_argument('--version', action='version', version='aux ' + VERSION)
    cfg = par.parse_args(argv)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        if cfg.interactive:
            par.error('El menú AUX requiere una terminal interactiva.')
        par.print_help()
        return 0
    return navega()
