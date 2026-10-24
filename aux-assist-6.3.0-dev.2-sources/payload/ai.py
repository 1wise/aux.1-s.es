#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Small interactive API terminal; only explicitly typed conversation leaves the Live."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import ssl
import stat
import sys
import unicodedata
import urllib.error
import urllib.request
import warnings

DIR_APP = Path(__file__).resolve().parent
TITULOS = {'openai': 'GPT Assist', 'gemini': 'Gemini Assist'}
INSTRUCCION = ('You assist a Linux rescue operator. Ask for missing facts and distinguish '
    'observations from guesses. Explain commands before suggesting them. Ask the operator '
    'to identify the intended device before destructive disk operations. You cannot inspect '
    'this computer or execute commands. Reply in the operator\'s language.')
MAX_RESPUESTA = 2 * 1024 * 1024
MAX_CONTEXTO = 65536


def valida_cfg(dat):
    # Reject unknown fields so credentials cannot accidentally enter a public ISO.
    permitidos = {'enabled', 'openai', 'gemini', 'timeout_seconds', 'max_output_tokens'}
    if not isinstance(dat, dict) or set(dat) - permitidos:
        raise ValueError('AI: configuración pública inválida; no admite claves ni endpoints privados.')
    sal = {'enabled': True, 'openai': {'model': None}, 'gemini': {'model': None},
           'timeout_seconds': 60, 'max_output_tokens': 1024}
    sal.update(dat)
    if not isinstance(sal['enabled'], bool):
        raise ValueError('AI: enabled debe ser true o false.')
    for nom in TITULOS:
        ent = sal[nom]
        if not isinstance(ent, dict) or set(ent) - {'model'}:
            raise ValueError('AI: cada proveedor solo admite model, nunca credenciales.')
        mod = ent.get('model')
        if mod is not None and (not isinstance(mod, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', mod)):
            raise ValueError('AI: nombre de modelo inválido.')
        sal[nom] = {'model': mod}
    for nom, minimo, maximo in [('timeout_seconds', 10, 120), ('max_output_tokens', 128, 4096)]:
        val = sal[nom]
        if type(val) is not int or not minimo <= val <= maximo:
            raise ValueError(f'AI: {nom} debe estar entre {minimo} y {maximo}.')
    return sal


def texto_seguro(txt):
    # Provider output is untrusted terminal input: discard ANSI, OSC and bidi controls.
    return ''.join(car for car in txt if car in '\n\t' or unicodedata.category(car)[0] != 'C')


def peticion(prov, modelo, historial, cfg):
    if prov == 'openai':
        return 'https://api.openai.com/v1/responses', {
            'model': modelo, 'instructions': INSTRUCCION, 'input': historial,
            'store': False, 'max_output_tokens': cfg['max_output_tokens']}
    if prov == 'gemini':
        return 'https://generativelanguage.googleapis.com/v1beta/models/' + modelo + ':generateContent', {
            'systemInstruction': {'parts': [{'text': INSTRUCCION}]},
            'contents': [{'role': 'model' if ent['role'] == 'assistant' else 'user',
                          'parts': [{'text': ent['content']}]} for ent in historial],
            'generationConfig': {'maxOutputTokens': cfg['max_output_tokens']}}
    raise ValueError('AI: proveedor desconocido.')


def extrae(prov, dat):
    if prov == 'openai':
        bloques = [ent for salida in dat.get('output', []) if salida.get('type') == 'message'
                   for ent in salida.get('content', [])]
        txt = '\n'.join(ent.get('text', ent.get('refusal', '')) for ent in bloques
                        if ent.get('type') in ('output_text', 'refusal'))
        parcial = dat.get('status') == 'incomplete'
    else:
        candidatos = dat.get('candidates') or []
        uno = candidatos[0] if candidatos else {}
        txt = '\n'.join(ent['text'] for ent in uno.get('content', {}).get('parts', [])
                        if isinstance(ent.get('text'), str) and not ent.get('thought'))
        parcial = uno.get('finishReason') == 'MAX_TOKENS'
    if not txt.strip():
        raise RuntimeError('La API no devolvió texto visible; revisar modelo, filtros o límite de salida.')
    if parcial:
        txt += '\n[Respuesta incompleta: se alcanzó un límite del proveedor.]'
    return texto_seguro(txt)


class SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Authorization headers must never be forwarded to another origin.
        return None


def consulta(prov, modelo, clave, historial, cfg):
    url, dat = peticion(prov, modelo, historial, cfg)
    return extrae(prov, consulta_raw(prov, clave, url, dat, cfg))


def consulta_raw(prov, clave, url, dat, cfg):
    # Both chat and tool calls share the same verified transport and error redaction.
    cab = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    cab['Authorization' if prov == 'openai' else 'x-goog-api-key'] = (
        'Bearer ' + clave if prov == 'openai' else clave)
    req = urllib.request.Request(url, data=json.dumps(dat).encode(), headers=cab, method='POST')
    abr = urllib.request.build_opener(SinRedireccion(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with abr.open(req, timeout=cfg['timeout_seconds']) as rsp:
            cuerpo = rsp.read(MAX_RESPUESTA + 1)
        if len(cuerpo) > MAX_RESPUESTA:
            raise RuntimeError('Respuesta API demasiado grande; no se guardó.')
        dat = json.loads(cuerpo)
        if not isinstance(dat, dict):
            raise ValueError('API response must be an object')
        return dat
    except urllib.error.HTTPError as exc:
        # API error bodies can echo submitted material; report actionable status only.
        motivos = {401: 'clave no válida', 403: 'acceso denegado', 404: 'modelo o recurso no disponible',
                   429: 'cuota o límite de peticiones', 400: 'petición o modelo no compatible'}
        raise RuntimeError(f'API HTTP {exc.code}: {motivos.get(exc.code, "error del proveedor")}. No se reintentó.') from None
    except (urllib.error.URLError, TimeoutError, ssl.SSLError):
        raise RuntimeError('No se pudo conectar por HTTPS. Revisar red, DNS, reloj y certificados; no se reintentó.') from None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise RuntimeError('Respuesta API no reconocida; no se guardó.') from None


def valida_api_clave(clave):
    if not re.fullmatch(r'[\x21-\x7e]{8,512}', clave):
        raise ValueError('Formato de clave API inválido.')
    return clave


def lee_clave_preparada(prov):
    # PID 1 provides only this service's credential; the key never enters the environment.
    pth_cre = os.environ.get('CREDENTIALS_DIRECTORY')
    if not pth_cre or not prov:
        return None
    if prov not in TITULOS:
        raise ValueError('Proveedor API inválido.')
    try:
        fd = os.open(Path(pth_cre) / (prov + '.key'), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Credencial preparada inválida.')
        dat = os.read(fd, 515)
    finally:
        os.close(fd)
    if not dat:
        return None
    try:
        clave = dat.decode('ascii').removesuffix('\n').removesuffix('\r')
        return valida_api_clave(clave)
    except (ValueError, UnicodeError):
        raise ValueError('Credencial preparada inválida.') from None


def pide_clave(prov=None):
    try:
        guardada = lee_clave_preparada(prov)
    except (OSError, ValueError):
        print('Clave preparada no utilizable. Disponible la entrada manual.')
        guardada = None
    if guardada:
        modo = input('Clave API: L llave / V visible / O oculta [L]: ').strip().upper() or 'L'
        if modo == 'L':
            print('Clave preparada seleccionada; no se muestra su contenido.')
            return guardada
    else:
        modo = input('Entrada de clave: V visible / O oculta [V]: ').strip().upper() or 'V'
    # Visible input is deliberate for long keys typed on the physical QEMU console.
    if modo == 'V':
        clave = input('Clave API temporal (visible): ').strip()
    elif modo == 'O':
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                clave = getpass.getpass('Clave API temporal (sin eco): ').strip()
        except getpass.GetPassWarning:
            raise ValueError('No se puede desactivar el eco de esta terminal.') from None
    else:
        raise ValueError('Elegir una de las opciones de entrada de clave.')
    return valida_api_clave(clave)


def terminal(prov, cfg):
    if not cfg['enabled']:
        raise ValueError('Asistentes API desactivados en ai.json.')
    if not sys.stdin.isatty():
        raise ValueError('Abrir en una terminal interactiva para introducir la clave.')
    print(TITULOS[prov] + ' · API por HTTPS · Ctrl-Alt-F6: menú')
    print('Solo se envían los mensajes escritos aquí. No hay ejecución automática de comandos.')
    print('/nueva borra el contexto local; /salir cierra y libera la clave de esta sesión.')
    modelo = cfg[prov]['model'] or input('Modelo API disponible en tu cuenta: ').strip()
    valida_cfg({prov: {'model': modelo or '!'}})
    clave = pide_clave(prov)
    historial = []
    try:
        while True:
            txt = input('\nTú> ').strip()
            if txt == '/salir':
                return
            if txt == '/nueva':
                historial.clear()
                print('Contexto local borrado. La siguiente consulta empieza de cero.')
                continue
            if not txt:
                continue
            if len(txt.encode()) > 8192 or clave in txt:
                print('Mensaje rechazado: máximo 8192 bytes; no pegar la clave en el chat.')
                continue
            candidato = historial + [{'role': 'user', 'content': txt}]
            if len(candidato) > 31 or len(json.dumps(candidato).encode()) > MAX_CONTEXTO:
                print('Límite de contexto local. Usar /nueva antes de continuar.')
                continue
            print('Consultando API…', flush=True)
            try:
                respuesta = consulta(prov, modelo, clave, candidato, cfg)
            except RuntimeError as exc:
                print(str(exc))
                continue
            # Retain only successful turns in RAM; never create a transcript on disk.
            respuesta = respuesta.replace(clave, '[clave omitida]')
            historial = candidato + [{'role': 'assistant', 'content': respuesta}]
            print('\n' + TITULOS[prov] + '>\n' + respuesta)
    finally:
        historial.clear()
        clave = None


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--provider', required=True, choices=TITULOS)
    par.add_argument('--config', type=Path, default=DIR_APP / 'ai.json')
    par.add_argument('--agent', action='store_true', help='Propose local actions; physical root approval is still required')
    args = par.parse_args()
    try:
        cfg = valida_cfg(json.loads(args.config.read_text()))
        if args.agent:
            from ai_agent import terminal_agente
            terminal_agente(args.provider, cfg)
        else:
            terminal(args.provider, cfg)
    except (EOFError, KeyboardInterrupt):
        pass
    except (ValueError, OSError) as exc:
        print('Asistente no iniciado:', texto_seguro(str(exc)))
        return 1
    finally:
        print('\nSesión cerrada. Ctrl-Alt-F6 para volver al menú.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
