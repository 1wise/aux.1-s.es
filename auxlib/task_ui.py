# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Configure one task, run its real dry-run, then explicitly choose execution."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys

from . import VERSION
from .console_ui import aplicacion, campo
from .interactive import elige
from .catalog_workflow import archivo_catalogo


def prepara_tarea(tarea, raiz, argv):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError('-i / --interactive requiere una terminal; usar --dry-run para el plan por CLI.')
    par = argparse.ArgumentParser(add_help=False)
    campos = ('config','target','output','cache','ram-dir','catalog-file','catalog-profile','url-file','list',
              'light-url-file','heavy-url-file','only','mode','jobs','ftp-host','ftp-user','ftp-port','ftp-root')
    for nom in campos:
        par.add_argument('--'+nom)
    par.add_argument('--dry-run',action='store_true')
    par.add_argument('--refresh',action='store_true')
    par.add_argument('--ftp-tls',action=argparse.BooleanOptionalAction,default=None)
    val, resto = par.parse_known_args([x for x in argv if x not in ('-i','--interactive')])
    arc_cfg = Path(val.config).expanduser().resolve() if val.config else raiz/'fast-boot.json'
    cfg = json.loads(arc_cfg.read_text()) if arc_cfg.is_file() else {}
    if not isinstance(cfg,dict):
        raise ValueError('La configuración debe ser un objeto JSON.')

    def ruta(nom, defecto):
        valor = getattr(val,nom,None)
        if valor:
            return str(Path(valor).expanduser().resolve())
        pth = Path(cfg.get(nom) or defecto).expanduser()
        return str(pth if pth.is_absolute() else arc_cfg.parent/pth)

    datos = {'target':val.target or cfg.get('target') or '',
             'output':ruta('output','/var/www/aux.1-s.es/html'),
             'cache':ruta('cache','/var/www/aux.1-s.es/isos'),
             'ram_dir':ruta('ram_dir','/dev/shm/aux-fast-boot'),
             'catalog_file':ruta('catalog_file',str(archivo_catalogo() or raiz/'config/catalog.remote.snapshot.json')),
             'catalog_profile':ruta('catalog_profile',str(raiz/'state/catalog-profile.json')) if val.catalog_profile or cfg.get('catalog_profile') or (raiz/'state/catalog-profile.json').is_file() else '',
             'url_file':ruta('url_file',str(raiz/'url.txt')),
             'light_url_file':ruta('light_url_file',str(raiz/'light-url.txt')),
             'heavy_url_file':ruta('heavy_url_file',str(raiz/'heavy-url.txt')),
             'only':val.only or '', 'mode':val.mode or 'extract',
             'jobs':str(val.jobs or cfg.get('jobs',4)), 'refresh':val.refresh,
             'ftp_host':val.ftp_host or cfg.get('ftp_host') or '',
             'ftp_user':val.ftp_user or cfg.get('ftp_user') or '',
             'ftp_port':str(val.ftp_port or cfg.get('ftp_port',21)),
             'ftp_root':val.ftp_root or cfg.get('ftp_root','/'),
             'ftp_tls':val.ftp_tls if val.ftp_tls is not None else cfg.get('ftp_tls',True)}
    dest = next((x for x in resto if x in ('ram','disk','ftp')),'disk') if tarea=='deploy' else None
    if tarea=='deploy' and dest in resto:
        resto.remove(dest)
    seleccion = val.list or ('file' if val.url_file else 'all' if tarea=='download' else 'cache')

    def argumentos():
        res = list(resto)
        if arc_cfg.is_file() or val.config:res += ['--config',str(arc_cfg)]
        if datos['target']:res += ['--target',datos['target']]
        for nom in ('output','cache','ram_dir'):
            res += ['--'+nom.replace('_','-'),datos[nom]]
        if tarea=='generate':
            res += ['--catalog-file',datos['catalog_file']]
            if datos['catalog_profile']:res += ['--catalog-profile',datos['catalog_profile']]
        if datos['only']:res += ['--only',datos['only']]
        if tarea=='deploy':
            res.append(dest)
            if dest=='disk':res += ['--mode',datos['mode']]
            if dest=='ftp':
                for nom in ('ftp_host','ftp_user','ftp_port','ftp_root'):
                    if datos[nom]:res += ['--'+nom.replace('_','-'),datos[nom]]
                res.append('--ftp-tls' if datos['ftp_tls'] else '--no-ftp-tls')
                return res
        if tarea in ('download','deploy'):
            if seleccion in ('light','heavy'):
                res += ['--list',seleccion,'--'+seleccion+'-url-file',datos[seleccion+'_url_file']]
            elif seleccion in ('all','file'):
                res += ['--url-file',datos['url_file'] if seleccion=='file' else str(raiz/'url.txt')]
        if tarea=='download':
            res += ['--jobs',datos['jobs']]
            if datos['refresh']:res.append('--refresh')
        return res

    with aplicacion('AUX '+tarea.upper()+' '+VERSION,'ejecucion'):
        while True:
            opciones = [('Revisar el plan antes de ejecutar','review'),
                        ('Perfil de URLs: '+(datos['target'] or 'configuración actual'),'target'),
                        ('Directorios y catálogo','paths')]
            if tarea=='deploy':opciones.append(('Destino: '+dest,'dest'))
            if tarea in ('download','deploy') and dest!='ftp':
                opciones.append(('Selección: '+seleccion,'selection'))
            if tarea!='deploy' or dest!='ftp':opciones.append(('Filtro: '+(datos['only'] or 'todos'),'only'))
            if tarea=='download':
                opciones += [('Descargas simultáneas: '+datos['jobs'],'jobs'),
                             ('Volver a descargar: '+('sí' if datos['refresh'] else 'no'),'refresh')]
            if tarea=='deploy' and dest=='disk':opciones.append(('Preparación: '+datos['mode'],'mode'))
            if tarea=='deploy' and dest=='ftp':opciones.append(('Conexión FTP / FTPS','ftp'))
            opciones.append(('Salir','exit'))
            accion = elige('Opciones de '+tarea,opciones)
            if accion=='exit':raise KeyboardInterrupt
            if accion=='target':
                datos['target']=elige('Perfil de URLs; la ejecución sigue siendo en este equipo',
                    [('Configuración actual','')]+[(nom,nom) for nom in cfg.get('targets',{})])
            elif accion=='paths':
                noms=['output','cache','ram_dir']+(['catalog_file','catalog_profile'] if tarea=='generate' else [])
                nom=elige('Directorios',[(x,x) for x in noms])
                valor=campo(nom,datos[nom])
                datos[nom]=str(Path(valor).expanduser().resolve()) if valor else ''
            elif accion=='dest':
                dest=elige('Destino del despliegue',[('Disco local','disk'),('RAM / tmpfs','ram'),('Réplica FTP / FTPS','ftp')])
                if dest=='ftp':datos['only']=''
            elif accion=='selection':
                opciones=[('Todas las URL de url.txt','all'),('Light','light'),('Heavy','heavy'),('Archivo de URL específico','file')]
                if tarea=='deploy':opciones.insert(0,('Toda la caché existente','cache'))
                seleccion=elige('Imágenes locales; los enlaces de origen se publican con generate',opciones)
                if seleccion in ('file','light','heavy'):
                    nom='url_file' if seleccion=='file' else seleccion+'_url_file'
                    datos[nom]=str(Path(campo('Lista de URL',datos[nom])).expanduser().resolve())
            elif accion in ('only','jobs'):
                datos[accion]=campo(accion,datos[accion])
            elif accion=='refresh':datos['refresh']=not datos['refresh']
            elif accion=='mode':datos['mode']=elige('Contenido de las imágenes',[('Extraer a disco','extract'),('Montar ISO en solo lectura','mount')])
            elif accion=='ftp':
                nom=elige('Conexión; la contraseña se solicitará oculta al ejecutar',
                          [(x,x) for x in ('ftp_host','ftp_user','ftp_port','ftp_root','ftp_tls')])
                if nom=='ftp_tls':datos[nom]=not datos[nom]
                else:datos[nom]=campo(nom,datos[nom])
            elif accion=='review':
                args=argumentos()
                cmd=['bash',str(raiz/(tarea+'.sh'))]+args
                print('Calculando el plan de '+tarea+'...',flush=True)
                rsp=subprocess.run(cmd+['--dry-run'],capture_output=True,text=True,stdin=subprocess.DEVNULL)
                resumen=[shlex.join(cmd),'']+(rsp.stdout+rsp.stderr).splitlines()
                if rsp.returncode:
                    campo('El plan tiene errores. Enter para revisar opciones',resumen=resumen)
                    continue
                if val.dry_run:
                    campo('Simulación solicitada. Enter para terminar',resumen=resumen)
                    return args+['--dry-run']
                if campo('Escribir EJECUTAR para aplicar este plan; Enter vuelve',resumen=resumen)=='EJECUTAR':
                    return args
