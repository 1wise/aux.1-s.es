# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Route image preparation through named cyan console applications."""
import argparse
from pathlib import Path
import subprocess
import sys
from . import VERSION
from .common import DIR_APP
from .console_ui import aplicacion, campo
from .interactive import elige


def parametros_live(cfg):
    with aplicacion('AUX LIVE RECIPE', 'ejecucion'):
        cfg.output = cfg.output or Path(campo('Directorio NUEVO de salida de la receta Live'))
        if campo('Generar receta y fuentes (no compila una ISO). Escribir GENERAR',resumen=['Salida: '+str(cfg.output)]) != 'GENERAR':
            raise KeyboardInterrupt
    return cfg


def parametros_usb(cfg):
    with aplicacion('AUX USB IMAGE', 'ejecucion'):
        cfg.iso = cfg.iso or Path(campo('ISO Live de entrada'))
        cfg.sha256 = cfg.sha256 or campo('SHA-256 comprobado de la ISO')
        cfg.output = cfg.output or Path(campo('Archivo NUEVO de imagen de salida; nunca /dev'))
        if cfg.capacity_bytes is None:
            cfg.capacity_bytes = int(campo('Capacidad de la imagen en bytes; múltiplo de 512'))
        cfg.build = elige('Acción para la imagen USB', [('Revisar el plan', False),
                                                      ('Generar un archivo de imagen nuevo', True)])
    return cfg


def confirma_usb(plan):
    with aplicacion('AUX USB IMAGE', 'ejecucion'):
        return campo('Revisar y escribir GENERAR para crear el archivo',resumen=plan) == 'GENERAR'


def main(argv=None):
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--interactive', action='store_true')
    par.add_argument('--version', action='version', version='aux-images '+VERSION)
    cfg = par.parse_args(argv)
    if not cfg.interactive:
        par.print_help()
        return 0
    with aplicacion('AUX IMAGES', 'ejecucion'):
        modo = elige('Generador de imágenes y perfiles', [
            ('Personalizar un instalador ISO oficial', 'iso'),
            ('Generar perfil Kickstart / preseed', 'profile'),
            ('Preparar receta Live de asistencia (no compila ISO)', 'live'),
            ('Construir Live Fedora 45 en VM KVM', 'live_build'),
            ('Generar archivo de imagen USB (no graba dispositivos)', 'usb')])
    if modo == 'iso':
        from .setup import main as instala
        return instala(['--interactive', '--mode', 'iso'])
    if modo == 'profile':
        from .profiles import main as perfil
        return perfil(['--interactive'])
    rutas={'live':'iso-assist/prepare.py','live_build':'iso-assist/build.py','usb':'usb/portable/build.py'}
    ruta=DIR_APP/rutas[modo]
    return subprocess.run([sys.executable, str(ruta), '--interactive'], check=False).returncode
