# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author & Credits: https://www.alawise.es/1-s
"""Read installation choices without allowing a manifest to grant execution."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

from . import VERSION
from .profiles import ROLES, ROTULOS, seleccion
from . import software


def lee_seleccion(pth):
    if pth.stat().st_size > 131072:
        raise ValueError('Selección demasiado grande.')
    dat = json.loads(pth.read_text())
    campos = {'schema','distribution','roles','native','mode','root','iso','iso_sha256','output','release'}
    if not isinstance(dat,dict) or set(dat)-campos or dat.get('schema')!='aux-install-v1':
        raise ValueError('Selección AUX inválida: no admite permisos, comandos ni opciones adicionales.')
    if dat.get('mode') not in ('existing','root','iso'):
        raise ValueError('Modo de instalación inválido.')
    if not isinstance(dat.get('roles'),list) or any(not isinstance(val,str) for val in dat['roles']):
        raise ValueError('La selección debe declarar una lista de perfiles.')
    sel = seleccion(dat.get('distribution'),dat['roles'],dat.get('native'))
    for nom in ('root','iso','iso_sha256','output','release'):
        if nom in dat and (not isinstance(dat[nom],str) or len(dat[nom])>4096 or any(ord(car)<32 for car in dat[nom])):
            raise ValueError('Campo inválido en selección: '+nom)
    sal = {'distro':dat['distribution'],'mode':dat['mode'],'roles':','.join(dat['roles'])}
    if 'native' in sel:
        sal['native'] = sel['native']
    for nom in ('root','iso','iso_sha256','output','release'):
        if nom in dat:
            sal[nom] = dat[nom]
    return sal


def elige(rot, opciones, defecto=1):
    print('\n'+rot)
    for idx,(nom,_) in enumerate(opciones,1):
        print(f'  {idx}. {nom}')
    txt = input(f'Opcion [{defecto}; 0 cancela]: ').strip() or str(defecto)
    if txt=='0':
        raise KeyboardInterrupt
    if not txt.isdigit() or not 1<=int(txt)<=len(opciones):
        raise ValueError('Opción fuera de rango.')
    return opciones[int(txt)-1][1]


def marca(rot, opciones, elegidos=()):
    """Use real checkboxes when dialog is installed; keep a searchable TTY fallback."""
    ids = [nom for nom, _ in opciones]
    act = set(elegidos)
    if shutil.which('dialog') and sys.stdin.isatty() and sys.stdout.isatty():
        cmd = ['dialog', '--stdout', '--separate-output', '--checklist', rot, '24', '90', '16']
        for nom, des in opciones:
            cmd += [nom, des.replace('\n', ' ')[:180], 'on' if nom in act else 'off']
        res = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, check=False)
        if res.returncode:
            raise KeyboardInterrupt
        lista = res.stdout.splitlines()
        if any(nom not in ids for nom in lista):
            raise ValueError('Selección de casillas inválida.')
        return lista
    bus = ''
    while True:
        print('\n' + rot + ' | ' + str(len(act)) + ' seleccionados')
        for idx, (nom, des) in enumerate(opciones, 1):
            if (bus and bus.lower() in (nom + ' ' + des).lower()) or (not bus and (len(opciones) < 40 or nom in act)):
                print(f'  {idx:3}. [{"x" if nom in act else " "}] {des} ({nom})')
        txt = input('Números para alternar; ?texto busca todos; Enter acepta; 0 cancela: ').strip()
        if not txt:
            return [nom for nom in ids if nom in act]
        if txt == '0':
            raise KeyboardInterrupt
        if txt.startswith('?'):
            bus = txt[1:]
            continue
        for val in txt.split(','):
            if not val.strip().isdigit() or not 1 <= int(val) <= len(ids):
                raise ValueError('Casilla fuera de rango.')
            nom = ids[int(val) - 1]
            if nom in act:
                act.remove(nom)
            else:
                act.add(nom)


def software_nativo(dis):
    dat = software.carga(dis)
    nat = software.defecto(dis)
    lista = dat['groups']
    if dis == 'fedora':
        nat['environment'] = elige('Entorno base de Fedora',
            [('Solo grupos', '')] + [(ent['label'], ent['id']) for ent in dat['environments']],
            1 + next(idx for idx, ent in enumerate(dat['environments'], 1) if ent['id'] == nat['environment']))
        ent = next((ent for ent in dat['environments'] if ent['id'] == nat['environment']), None)
        req = ent['required'] if ent else []
        nat['groups'] = marca('Complementos y grupos nativos de Fedora',
            [(ent['id'], ent['label']) for ent in lista if ent['id'] not in req], ent['default'] if ent else [])
        print('Grupos requeridos por el entorno:', ', '.join(req) or 'ninguno')
    else:
        nat['tasks'] = marca('Tareas nativas de Debian: escritorios, servicios e idiomas',
            [(ent['id'], ent['label']) for ent in lista], nat['tasks'])
    return software.resuelve(dis, nat)['native']


def prepara(cfg):
    print('AUX '+VERSION+' | INSTALAR Y PERSONALIZAR')
    cfg.mode = elige('Destino de la instalación',[
        ('Preparar un instalador ISO','iso'),
        ('Preparar una base nueva en un directorio vacío','root'),
        ('Portal AUX / TEC / gateway: instala servicios en este equipo','server'),
        ('Solo herramientas AUX: instala archivos en el destino indicado','tools'),
        ('Instalar SOBRE EL SISTEMA ACTUAL: modifica este equipo','existing')])
    if cfg.mode == 'existing':
        cfg.root = Path('/')
        print('\nDESTINO: SISTEMA ACTUAL. Se modificarán paquetes, aplicaciones y configuración de este equipo.')
    if cfg.mode in ('existing','root','iso'):
        cfg.distro = elige('Distribución',[('Debian','debian'),('Fedora','fedora')])
        cfg.native = software_nativo(cfg.distro)
    if cfg.mode in ('existing','root','iso','tools'):
        lista = [nom for nom in ROLES if nom not in ('base', 'desktop')]
        cfg.roles = ','.join(['base'] + marca('Herramientas adicionales AUX', [(nom,ROTULOS[nom]) for nom in lista], lista))
        dat = seleccion(cfg.distro,cfg.roles.split(','),getattr(cfg,'native',None))
        print('\nSelección:',', '.join(dat['roles']),'|',len(dat['packages']),'paquetes/grupos')
    if cfg.mode=='root':
        cfg.root=Path(input('Raiz nueva absoluta [/mnt/aux-root]: ').strip() or '/mnt/aux-root')
    elif cfg.mode=='iso':
        cfg.iso=Path(input('ISO oficial de entrada: ').strip())
        cfg.iso_sha256=input('SHA-256 del medio comprobado: ').strip()
        cfg.output=Path(input('ISO nueva de salida: ').strip())
        cfg.check_packages=True
    elif cfg.mode=='server':
        cfg.root=Path(input('Directorio del proyecto [/var/www/aux.1-s.es]: ').strip() or '/var/www/aux.1-s.es')
        cfg.nginx=input('Instalar los vhosts revisados [s/N]: ').strip().lower()=='s'
    cfg.apply=False
    return cfg
