# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Local osquery inspection, read-only osctrl API access and enrollment preparation."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import warnings

from . import VERSION
from .common import DIR_APP, atomico
from .console_ui import aplicacion, campo
from .interactive import elige

TABLAS = {
    'system': ('system_info', 'Identidad, CPU y memoria del equipo'),
    'os': ('os_version', 'Sistema operativo'),
    'agent': ('osquery_info', 'Versión y estado del proceso osquery'),
    'ports': ('listening_ports', 'Puertos en escucha'),
    'processes': ('processes', 'Procesos visibles para la cuenta local'),
    'rpm': ('rpm_packages', 'Paquetes RPM instalados'),
    'deb': ('deb_packages', 'Paquetes Debian instalados'),
}
ENDPOINTS = ('enroll_tls_endpoint', 'config_tls_endpoint', 'logger_tls_endpoint',
             'distributed_tls_read_endpoint', 'distributed_tls_write_endpoint')
LIM_BYTES = 2 * 1024 * 1024


def identificador(txt):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', txt or ''):
        raise ValueError('Identificador de entorno o consulta inválido.')
    return txt


def url_api(txt):
    url = urllib.parse.urlsplit(txt)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('La API requiere una URL HTTPS sin credenciales, consulta ni fragmento.')
    if any(ord(c) < 33 for c in txt) or url.path not in ('', '/', '/api/v1', '/api/v1/'):
        raise ValueError('Usar el origen HTTPS de osctrl o su base /api/v1.')
    try:
        url.port
    except ValueError:
        raise ValueError('Puerto de API inválido.') from None
    return urllib.parse.urlunsplit((url.scheme, url.netloc, '', '', ''))


def valida_servidor(servidor):
    url = urllib.parse.urlsplit('https://' + servidor)
    if not url.hostname or url.username or url.password or url.path or url.query or url.fragment or any(c.isspace() for c in servidor):
        raise ValueError('Servidor TLS: usar hostname[:puerto], sin protocolo ni ruta.')
    try:
        url.port
    except ValueError:
        raise ValueError('Puerto TLS inválido.') from None


def lee_endpoints(pth):
    arc = Path(pth).expanduser()
    if not arc.is_file() or arc.stat().st_size > 16384:
        raise ValueError('Elegir un JSON de endpoints existente, de hasta 16 KiB.')
    dat = json.loads(arc.read_text())
    if not isinstance(dat, dict) or set(dat) != set(ENDPOINTS):
        raise ValueError('El JSON debe contener exactamente los cinco endpoints TLS documentados.')
    for val in dat.values():
        if not isinstance(val, str) or not re.fullmatch(r'/[A-Za-z0-9_./-]+', val) or val.startswith('//') or '..' in val.split('/'):
            raise ValueError('Endpoint TLS inválido: usar una ruta absoluta simple sin secretos.')
    return dat


def pide_token():
    # A broken terminal must never downgrade hidden token entry to echoed input.
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try:
            token = getpass.getpass('Token osctrl temporal (sin eco): ').strip()
        except getpass.GetPassWarning:
            raise ValueError('No se puede ocultar el token en esta terminal.') from None
    if not token:
        raise ValueError('El token no puede quedar vacío.')
    return token


def estado_local():
    binario = shutil.which('osqueryi')
    servicio = 'no disponible'
    if shutil.which('systemctl'):
        rsp = subprocess.run(['systemctl', 'is-active', 'osqueryd'], capture_output=True,
                             text=True, timeout=10, check=False)
        servicio = rsp.stdout.strip() or 'sin servicio systemd accesible'
    return {'osqueryi': binario, 'osqueryd': servicio,
        'installation': 'https://osquery.io/downloads',
        'scope': 'osqueryi inspecciona este equipo; no consulta la base de osqueryd.'}


def osquery(sql):
    binario = shutil.which('osqueryi')
    if not binario:
        raise ValueError('No está instalado osqueryi. Instalar el paquete oficial para este sistema: https://osquery.io/downloads')
    # No shell, extensions, writable SQL or user-supplied meta commands are accepted here.
    rsp = subprocess.run([binario, '--json', sql], capture_output=True, text=True,
                         timeout=30, check=False)
    if rsp.returncode:
        raise ValueError('osquery no pudo consultar la tabla. Revisar plataforma y permisos locales.')
    if len(rsp.stdout.encode()) > LIM_BYTES:
        raise ValueError('Resultado demasiado grande; reducir --limit.')
    try:
        dat = json.loads(rsp.stdout)
    except json.JSONDecodeError:
        raise ValueError('osquery devolvió una respuesta JSON inválida.') from None
    if not isinstance(dat, list):
        raise ValueError('Se esperaba una lista de filas de osquery.')
    return dat


def consulta_local(nom, limite=100, esquema=False):
    if nom not in TABLAS or not 1 <= limite <= 1000:
        raise ValueError('Consulta o límite inválido.')
    tabla = TABLAS[nom][0]
    columnas = osquery('PRAGMA table_info(' + tabla + ');')
    if not columnas:
        raise ValueError('Tabla no disponible en esta plataforma: ' + tabla)
    if esquema:
        return {'table': tabla, 'columns': columnas}
    filas = osquery('SELECT * FROM ' + tabla + ' LIMIT ' + str(limite) + ';')
    return {'table': tabla, 'limit': limite, 'rows': filas,
            'possibly_truncated': len(filas) == limite}


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def oculta(dat):
    if isinstance(dat, dict):
        return {nom: '[oculto]' if re.search(r'token|secret|password|private.?key', nom, re.I)
                else oculta(val) for nom, val in dat.items()}
    if isinstance(dat, list):
        return [oculta(val) for val in dat]
    return dat


def consulta_api(base, token, accion, entorno='', nombre='', pagina=1, limite=100, ca_file=None):
    base = url_api(base)
    if not isinstance(token, str) or not token.strip() or any(ord(c) < 32 for c in token):
        raise ValueError('Falta OSCTRL_API_TOKEN o contiene caracteres inválidos.')
    if not 1 <= limite <= 1000 or pagina < 1:
        raise ValueError('Página o límite inválido.')
    if accion == 'environments':
        ruta = '/api/v1/environments'
    else:
        env = urllib.parse.quote(identificador(entorno), safe='')
        rutas = {'nodes': '/api/v1/nodes/' + env + '/active',
                 'queries': '/api/v1/all-queries/' + env,
                 'results': '/api/v1/queries/' + env + '/results/' + urllib.parse.quote(identificador(nombre), safe='') if accion == 'results' else ''}
        if accion not in rutas:
            raise ValueError('Acción API de lectura desconocida.')
        ruta = rutas[accion]
        if accion == 'results':
            ruta += '?' + urllib.parse.urlencode({'page': pagina, 'page_size': limite})
    peticion = urllib.request.Request(base + ruta,
        headers={'Authorization': 'Bearer ' + token.strip(), 'Accept': 'application/json'}, method='GET')
    cliente = urllib.request.build_opener(SinRedireccion(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca_file)))
    try:
        with cliente.open(peticion, timeout=30) as rsp:
            contenido = rsp.read(LIM_BYTES + 1)
    except urllib.error.HTTPError as exc:
        exc.close()
        if exc.code in (401, 403):
            raise ValueError('osctrl rechazó el acceso: revisar vigencia y permisos del token.') from None
        if 300 <= exc.code < 400:
            raise ValueError('La API redirige a otra URL. Revisar el origen configurado; no se reenvió el token.') from None
        raise ValueError('Error HTTP de osctrl: ' + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise ValueError('No se pudo conectar con osctrl mediante TLS verificado.') from None
    if len(contenido) > LIM_BYTES:
        raise ValueError('Respuesta superior a 2 MiB. Usar un entorno o consulta más acotado.')
    try:
        dat = oculta(json.loads(contenido))
    except (json.JSONDecodeError, UnicodeError):
        raise ValueError('La API no devolvió JSON válido.') from None
    return {'resource': accion, 'page': pagina if accion == 'results' else None,
            'data': dat[:limite] if isinstance(dat, list) else dat,
            'truncated': isinstance(dat, list) and len(dat) > limite}


def prepara_enrolamiento(servidor, endpoints, ca, secreto, salida=None, aplicar=False, host_identifier="hostname"):
    # Endpoints come from the selected osctrl environment, never from guessed URL conventions.
    if host_identifier not in ('hostname','uuid','instance'):raise ValueError('Identificador de host: hostname, uuid o instance.')
    valida_servidor(servidor)
    dat = lee_endpoints(endpoints)
    pth_ca = Path(ca).expanduser()
    pth_sec = Path(secreto).expanduser()
    if not pth_ca.is_absolute() or not pth_ca.is_file() or not pth_sec.is_absolute():
        raise ValueError('La CA debe ser un archivo absoluto existente y el secreto una ruta absoluta privada.')
    if any(any(ord(c) < 32 for c in str(p)) for p in (pth_ca,pth_sec)):
        raise ValueError('Las rutas privadas no admiten caracteres de control.')
    from .settings import valida_privado
    valida_privado(pth_sec)
    pth_out = Path(salida).expanduser().absolute() if salida else None
    if pth_out:
        valida_privado(pth_out)
        if not pth_out.parent.is_dir():
            raise ValueError('El directorio padre privado no existe.')
    if pth_out and (pth_out.is_relative_to(DIR_APP) or pth_out.exists() or pth_out.is_symlink()):
        raise ValueError('Elegir un directorio privado nuevo fuera de las fuentes AUX.')
    flags = ['--tls_hostname=' + servidor, '--tls_server_certs=' + str(pth_ca),
             '--enroll_secret_path=' + str(pth_sec), '--host_identifier='+host_identifier,
             '--config_plugin=tls', '--logger_plugin=tls', '--distributed_plugin=tls',
             '--disable_distributed=false'] + ['--' + nom + '=' + dat[nom] for nom in ENDPOINTS]
    plan = {'server': servidor, 'output': str(pth_out) if pth_out else None,
            'flags': flags, 'effect': 'Sólo preparar archivos; no instala, enrola ni reinicia osqueryd.',
            'activation': 'Al activar estos flags, osctrl podrá proporcionar configuración y consultas al agente.'}
    if aplicar:
        if not pth_out:
            raise ValueError('--output es obligatorio con --apply.')
        pth_out.mkdir(mode=0o700, parents=False)
        atomico(pth_out / 'osquery.flags', '\n'.join(flags) + '\n', 0o600)
        atomico(pth_out / 'README.txt', 'Revisar el servicio osqueryd y su flagfile antes de activar.\n'
            'Crear el archivo enroll_secret_path con el secreto del entorno, modo 0600, fuera de la web.\n'
            'No cambiar una instalación ya enrolada sin revisar su configuración y base de estado.\n'
            'La activación debe hacerse en el equipo destinado al enrolamiento.\n', 0o600)
    return plan


def menu(cfg):
    datos = {'api_url': cfg.api_url or os.environ.get('OSCTRL_API_URL', ''),
             'environment': cfg.environment or '', 'name': cfg.name or ''}
    token = None
    with aplicacion('AUX OBSERVE', 'configuracion'):
        while True:
            accion = elige('osquery / osctrl', [('Estado local de osquery', 'status'),
                ('Consultar una tabla local', 'local'), ('Ver esquema de una tabla', 'schema'),
                ('Configurar conexión osctrl', 'config'), ('Entornos osctrl', 'environments'),
                ('Nodos activos del entorno', 'nodes'), ('Consultas del entorno', 'queries'),
                ('Resultados de una consulta', 'results'), ('Preparar flags de enrolamiento', 'enrollment'),
                ('Volver', 'back')])
            if accion == 'back':
                return 0
            try:
                if accion == 'status':
                    dat = estado_local()
                elif accion in ('local', 'schema'):
                    nom = elige('Tabla local: esquema comprobado antes de consultar',
                        [(val[1] + ' / ' + val[0], nom) for nom, val in TABLAS.items()])
                    dat = consulta_local(nom, cfg.limit, accion == 'schema')
                elif accion == 'config':
                    datos['api_url'] = campo('URL HTTPS de la API osctrl', datos['api_url'], validar=url_api)
                    datos['environment'] = campo('Identificador del entorno osctrl', datos['environment'], validar=identificador)
                    continue
                elif accion == 'enrollment':
                    srv = campo('Servidor TLS osctrl: hostname[:puerto]', validar=valida_servidor)
                    end = campo('JSON local de los cinco endpoints TLS', validar=lee_endpoints)
                    ca = campo('Archivo CA PEM existente')
                    sec = campo('Ruta privada del secreto de enrolamiento')
                    out = campo('Directorio nuevo privado para enrolamiento', str(Path.home() / '.config/aux-enrollment'))
                    host_id = elige('Identificador osctrl: hostname único y estable por equipo', [('Hostname (recomendado)', 'hostname'), ('UUID del sistema', 'uuid'), ('Instancia local', 'instance')])
                    dat = prepara_enrolamiento(srv, end, ca, sec, out, host_identifier=host_id)
                    if campo('Escribir GENERAR para preparar los flags', resumen=json.dumps(dat, ensure_ascii=False, indent=2).splitlines()) != 'GENERAR':continue
                    dat = prepara_enrolamiento(srv, end, ca, sec, out, True, host_id)
                else:
                    if not datos['api_url']:
                        datos['api_url'] = campo('URL HTTPS de la API osctrl', validar=url_api)
                    if accion != 'environments' and not datos['environment']:
                        datos['environment'] = campo('Identificador del entorno osctrl', validar=identificador)
                    if accion == 'results':
                        datos['name'] = campo('Identificador de la consulta osctrl', datos['name'], validar=identificador)
                    from .settings import lee_secretos
                    token = token or os.environ.get('OSCTRL_API_TOKEN') or lee_secretos().get('osctrl_api_token') or pide_token()
                    dat = consulta_api(datos['api_url'], token, accion, datos['environment'], datos['name'], limite=cfg.limit, ca_file=cfg.ca_file)
                campo('Resultado; Enter vuelve al módulo', resumen=json.dumps(dat, ensure_ascii=False, indent=2).splitlines())
            except KeyboardInterrupt:
                continue
            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                token = None
                campo('Operación pendiente; se conservan conexión y entorno', resumen=[str(exc)])


def main(argv=None):
    from .settings import lee_config, lee_secretos
    cfg_obs = lee_config().get('observe', {})
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--version', action='version', version='aux-observe ' + VERSION)
    par.add_argument('-i', '--interactive', action='store_true')
    par.add_argument('--api-url', default=os.environ.get('OSCTRL_API_URL') or cfg_obs.get('api_url'))
    par.add_argument('--ca-file', default=cfg_obs.get('ca_file'))
    par.add_argument('--environment', default=cfg_obs.get('environment')); par.add_argument('--name')
    par.add_argument('--limit', type=int, default=cfg_obs.get('limit',100)); par.add_argument('--page', type=int, default=1)
    sub = par.add_subparsers(dest='cmd')
    sub.add_parser('status')
    for nom in ('local', 'schema'):
        sub.add_parser(nom).add_argument('query', choices=TABLAS)
    sub.add_parser('environments'); sub.add_parser('nodes'); sub.add_parser('queries'); sub.add_parser('results')
    ent = sub.add_parser('enrollment')
    ent.add_argument('--server', required=True); ent.add_argument('--endpoints', required=True)
    ent.add_argument('--ca', required=True); ent.add_argument('--secret-path', required=True)
    ent.add_argument('--output'); ent.add_argument('--apply', action='store_true')
    ent.add_argument('--host-identifier',choices=('hostname','uuid','instance'),default='hostname')
    cfg = par.parse_args(argv)
    if not 1 <= cfg.limit <= 1000 or cfg.page < 1:
        par.error('--limit: 1..1000; --page: 1 o superior.')
    if cfg.interactive:
        if not sys.stdin.isatty():
            par.error('El menú requiere una terminal interactiva.')
        return menu(cfg)
    if cfg.cmd == 'status':
        dat = estado_local()
    elif cfg.cmd in ('local', 'schema'):
        dat = consulta_local(cfg.query, cfg.limit, cfg.cmd == 'schema')
    elif cfg.cmd == 'enrollment':
        dat = prepara_enrolamiento(cfg.server, cfg.endpoints, cfg.ca, cfg.secret_path, cfg.output, cfg.apply,cfg.host_identifier)
    elif cfg.cmd:
        dat = consulta_api(cfg.api_url or '', os.environ.get('OSCTRL_API_TOKEN') or lee_secretos().get('osctrl_api_token',''), cfg.cmd,
                           cfg.environment or '', cfg.name or '', cfg.page, cfg.limit, cfg.ca_file)
    else:
        par.print_help()
        return 0
    print(json.dumps(dat, ensure_ascii=False, indent=2))
    return 0
