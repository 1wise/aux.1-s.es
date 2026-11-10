# Timestamp: 2026-11-09 | Version: 7.0.0-dev.3
# Author & Credits: https://www.alawise.es/1-s
"""Shared entries for the physical console, desktop and standalone tools."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from . import VERSION
from .common import DIR_APP, guarda_json
from .interactive import elige


def abre(nom):
    if nom in ('installer','systems'):
        exe='aux-setup' if nom=='installer' else 'aux-enter'
        return subprocess.run([sys.executable,str(DIR_APP/exe),'--interactive'],check=False).returncode
    if nom=='cockpit':
        if input('Iniciar Cockpit en este equipo [s/N]: ').strip().lower()=='s':
            subprocess.run(['systemctl','start','cockpit.socket'],check=True)
        rsp=subprocess.run(['hostname','-I'],capture_output=True,text=True,check=True)
        for ip in ['localhost']+rsp.stdout.split():
            print('https://'+('['+ip+']' if ':' in ip else ip)+':9090')
        print('Acceso con una cuenta del sistema de destino.')
        input('Enter para volver: ')
        return 0
    if nom=='catalogue':
        return catalogo()
    if nom=='gui':
        pth=Path('/usr/local/share/aux/workspace.html')
        if not pth.is_file():
            raise ValueError('Instalar las aplicaciones AUX antes de abrir el escritorio.')
        return subprocess.run(['xdg-open',pth.as_uri()],check=False).returncode
    raise ValueError('Aplicación desconocida.')


def catalogo():
    from .webapps import modelo
    print('AUX '+VERSION+' | CATALOGO Y SELECCION')
    pth=Path('/srv/aux/catalog/current/catalog.json')
    ents=json.loads(pth.read_text())['entries'] if pth.is_file() else modelo()['entries']
    bus=input('Filtrar familia, version o arquitectura [todos]: ').strip().lower()
    ents=[ent for ent in ents if not bus or bus in ' '.join(str(ent.get(nom,'')) for nom in ('family','release','architecture','kind','name')).lower()]
    for idx,ent in enumerate(ents,1):
        print(f"{idx:3}. {ent['family']} | {ent['release']} | {ent['architecture']} | {ent['kind']} | {ent['download_class']}")
    if not ents:
        print('Sin coincidencias.')
        return 0
    txt=input('Elegir numeros separados por coma [Enter vuelve]: ').strip()
    if not txt:
        return 0
    nums=[int(val.strip()) for val in txt.split(',')]
    if any(num<1 or num>len(ents) for num in nums):
        raise ValueError('Recurso fuera de rango.')
    sel=[ents[num-1] for num in dict.fromkeys(nums)]
    if any(ent['download_class'] not in ('light','heavy') for ent in sel):
        raise ValueError('Hay recursos sin clase light/heavy declarada.')
    pth=Path(input('Guardar seleccion JSON [/work/aux-catalog-selection.json]: ').strip() or '/work/aux-catalog-selection.json')
    guarda_json(pth,{'metadata':{'version':VERSION},'entries':sel})
    print('Selección guardada:',pth)
    print('Usar aux-catalog --config',pth,'--output DIRECTORIO para publicar y exportar las listas.')
    return 0


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--gui',action='store_true')
    par.add_argument('--tool',choices=('installer','catalogue','systems','cockpit'))
    cfg=par.parse_args(argv)
    if cfg.gui:
        return abre('gui')
    if cfg.tool:
        return abre(cfg.tool)
    nom=elige('AUX '+VERSION+' | APLICACIONES',[
        ('Instalar y personalizar','installer'),('Catalogo y seleccion','catalogue'),
        ('Sistemas y chroot','systems'),('Cockpit del equipo','cockpit')])
    return abre(nom)
