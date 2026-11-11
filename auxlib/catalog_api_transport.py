# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Bounded API transport adapted from the AUX Assist client, without terminal actions."""
import json
import re
import ssl
import unicodedata
import urllib.error
import urllib.request

MAX_RESPUESTA = 2 * 1024 * 1024


def texto_seguro(txt):
    # Provider output is untrusted terminal input: discard ANSI, OSC and bidi controls.
    return ''.join(car for car in txt if car in '\n\t' or unicodedata.category(car)[0] != 'C')


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
