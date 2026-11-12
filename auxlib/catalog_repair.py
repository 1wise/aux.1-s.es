# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Keep reviewed URL candidates separate from automatic upstream discovery."""
import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .common import guarda_json
from .catalog_profile import url_perfil

ORIGENES = ('manual', 'openai', 'gemini')
CAMPOS = {'slot_id', 'previous_url', 'original_url', 'reference_url', 'candidate_origin', 'added_at'}


def huella_candidatas(vals):
    return hashlib.sha256(json.dumps(vals, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def pendientes(informe):
    return [r for r in informe.get('resources', []) if r.get('status') not in ('resolved', 'rolling-checked')
            or r.get('http', {}).get('http') != 'passed' or r.get('unavailable_newer_versions')
            or r.get('source_warning')]


def lee_candidatas(pth):
    pth = Path(pth)
    if not pth.is_file():
        return []
    if pth.stat().st_size > 1048576:
        raise ValueError('Registro de URL candidatas demasiado grande.')
    dat = json.loads(pth.read_text())
    if not isinstance(dat, dict) or set(dat) != {'schema', 'candidates'} or dat['schema'] != 'aux-catalog-url-candidates-v1':
        raise ValueError('Registro de URL candidatas no reconocido.')
    vals = dat['candidates']
    if not isinstance(vals, list) or len(vals) > 512:
        raise ValueError('Demasiadas URL candidatas.')
    for ent in vals:
        if (not isinstance(ent, dict) or set(ent) != CAMPOS or
                not isinstance(ent['slot_id'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,120}', ent['slot_id']) or
                ent['candidate_origin'] not in ORIGENES or not isinstance(ent['added_at'], str)):
            raise ValueError('Candidata de recuperación inválida.')
        for nom in ('previous_url', 'original_url', 'reference_url'):
            url_perfil(ent[nom])
    return vals


def guarda_candidata(pth, fila, url, referencia, origen='manual'):
    if origen not in ORIGENES:
        raise ValueError('Origen de candidata desconocido.')
    pth = Path(pth)
    vals = lee_candidatas(pth)
    ent = {'slot_id': fila['slot_id'], 'previous_url': url_perfil(fila['previous_url']),
           'original_url': url_perfil(url), 'reference_url': url_perfil(referencia),
           'candidate_origin': origen,
           'added_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    vals = [e for e in vals if (e['slot_id'], e['original_url']) != (ent['slot_id'], url)] + [ent]
    # Bound repeated daily corrections while retaining several mirrors per resource.
    recientes = [e for e in vals if e['slot_id'] == ent['slot_id']][-8:]
    vals = [e for e in vals if e['slot_id'] != ent['slot_id']] + recientes
    if len(vals) > 512:
        raise ValueError('El registro requiere retirar candidatas antiguas antes de ampliarlo.')
    if pth.is_file():
        guarda_json(pth.with_name(pth.name + '.before-review'), json.loads(pth.read_text()))
    guarda_json(pth, {'schema': 'aux-catalog-url-candidates-v1', 'candidates': vals})


def opciones_guardadas(vals, slot, fuente, automaticas):
    from .catalog_downloads import nombre_archivo, resuelve_slot
    sal = []
    for val in vals:
        if val['slot_id'] != slot['id']:
            continue
        # Current edition, architecture and channel rules still apply to every retry.
        try:ent = resuelve_slot(slot, [{'original_url': val['original_url']}])
        except ValueError:continue
        oficiales = [e for e in automaticas if nombre_archivo(e['original_url']) == nombre_archivo(ent['original_url'])]
        if oficiales:
            ent = {**oficiales[0], **ent}
        ent.update(candidate_origin=val['candidate_origin'], reference_url=val['reference_url'],
                   allowed_hosts=list(dict.fromkeys(fuente['allowed_hosts'] + [urlsplit(val['original_url']).hostname])))
        sal.append(ent)
    return sal


def comprueba_candidata(config, fila, url, referencia, comprobar=None, valida_red=None):
    from .catalog_downloads import resuelve_slot, comprueba_enlace
    from .catalog_mirrors import valida_espejo
    url_perfil(url)
    url_perfil(referencia)
    slots = {s['id']: s for s in config['download_slots']}
    slot = slots.get(fila.get('slot_id'))
    if slot is None:
        from .catalog_downloads import coincide
        mats = [s for s in slots.values() if coincide(url, s)]
        if len(mats) != 1:
            raise ValueError('La URL necesita una regla de fuente única; configurar la fuente desde el catálogo.')
        slot = mats[0]
    fuente = next(f for f in config['download_sources'] if f['id'] == slot['source_id'])
    ent = resuelve_slot(slot, [{'original_url': url}])
    hosts = list(dict.fromkeys(fuente['allowed_hosts'] + [urlsplit(url).hostname]))
    (valida_red or valida_espejo)(url)
    http = (comprobar or comprueba_enlace)(url, hosts, None, fuente.get('mirror_redirect_origins', []))
    if http.get('http') != 'passed':
        raise ValueError('La URL candidata no supera la comprobación HTTP.')
    return {**ent, 'slot_id': slot['id'], 'http': http, 'size_bytes': http.get('size_bytes'), 'allowed_hosts': hosts}


def contexto_recuperacion(config, fila, cache):
    slot = next((s for s in config['download_slots'] if s['id'] == fila.get('slot_id')), None)
    if slot is None:
        raise ValueError('Configurar una regla de fuente antes de solicitar URL para esta entrada.')
    fuente = next(f for f in config['download_sources'] if f['id'] == slot['source_id'])
    campos = ('slot_id', 'previous_url', 'original_url', 'release', 'status', 'http', 'error',
              'unavailable_newer_versions', 'source_warning')
    contexto = {'request': 'Suggest up to four direct HTTPS payload URLs for this exact resource. '
                'Preserve its edition, architecture and release channel. Prefer a newer available release. '
                'Use the supplied current index excerpt as evidence; report uncertainty instead of inventing availability.',
                'resource': {k: fila[k] for k in campos if k in fila}, 'slot': slot,
                'source_url': fuente['url'], 'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    pth = Path(cache) / (hashlib.sha256(fuente['url'].encode()).hexdigest() + '.body')
    if pth.is_file():
        with pth.open('rb') as arc:
            contexto['upstream_index_excerpt'] = arc.read(18000).decode(errors='replace')
    return contexto


def valida_sugerencias(dat):
    from .catalog_api_transport import texto_seguro
    if not isinstance(dat, dict) or set(dat) != {'summary', 'candidates'} or not isinstance(dat['summary'], str):
        raise ValueError('Propuesta de recuperación no reconocida.')
    if len(dat['summary']) > 4000 or texto_seguro(dat['summary']) != dat['summary']:
        raise ValueError('Resumen de recuperación inválido.')
    vals = dat['candidates']
    if not isinstance(vals, list) or len(vals) > 4:
        raise ValueError('La propuesta debe contener como máximo cuatro URL.')
    for ent in vals:
        if not isinstance(ent, dict) or set(ent) != {'url', 'reference_url', 'reason'}:
            raise ValueError('Campos de URL propuesta no admitidos.')
        url_perfil(ent['url'])
        url_perfil(ent['reference_url'])
        if not isinstance(ent['reason'], str) or len(ent['reason']) > 2000 or texto_seguro(ent['reason']) != ent['reason']:
            raise ValueError('Explicación de URL propuesta inválida.')
    return dat
