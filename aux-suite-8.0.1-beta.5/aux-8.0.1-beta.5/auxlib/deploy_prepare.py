# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Complete deployment metadata without downloading or advancing pinned images."""
import copy

from .catalog_v8 import acciones, ahora, raiz_artefacto, refresca, ruta_cfg, valida
from .transfer_events import evento, verifica


def destinos(ent, args):
    loc = [x for x in acciones(ent['policy'])['locations'] if x != 'origin']
    sel = getattr(args, 'action', 'show')
    sel = {'disk': 'ssd', 'ftp': 'bastion'}.get(sel, sel)
    return [x for x in loc if sel not in ('ram', 'ssd', 'bastion') or x == sel]


def prepara_despliegues(cat, cfg, ids):
    nuevo = copy.deepcopy(cat)
    errores = {}
    for pos, ent in enumerate(nuevo['entries']):
        if ent['id'] not in ids:
            continue
        # Completed pins remain offline, even for a mutable upstream URL.
        if ent.get('size_bytes') and ent.get('sha256') and ent.get('resolved') is not False:
            continue
        try:
            if ent.get('sha256') and ent.get('resolved') is not False:
                pth_cache = ruta_cfg(cfg, 'cache', '../isos')
                for pth in (pth_cache/raiz_artefacto(ent)/ent['filename'], pth_cache/ent['filename']):
                    if not pth.is_file() or not pth.stat().st_size:
                        continue
                    if verifica(pth, ent) != ent['sha256']:
                        raise ValueError('Checksum de fuente incorrecto; ejecutar download para reparar la caché.')
                    ent['size_bytes'] = pth.stat().st_size
                    ent['size_observation'] = {'source': 'verified-cache', 'observed_at': ahora(),
                                               'sha256': ent['sha256']}
                    evento(ent['id'], 'SIZE', str(ent['size_bytes'])+' bytes · caché verificada')
                    break
            if not ent.get('size_bytes') or not ent.get('sha256') or ent.get('resolved') is False:
                act = acciones(ent['policy'])
                if not act['resolve'] or not act['crawl_level']:
                    raise ValueError('Faltan tamaño/checksum oficiales y C no permite resolver. Revisar C en el tablero o importar metadatos comprobados.')
                evento(ent['id'], 'RESOLVE', 'Completar metadatos antes de deploy; no se descarga la imagen')
                res = refresca({**cat, 'entries': [ent]}, cfg, [ent['id']])['entries'][0]
                # A deploy must keep the artifact already selected or downloaded.
                # An unresolved placeholder can acquire its first authenticated pin.
                if ent.get('sha256') and any(res.get(k) != ent.get(k) for k in ('original_url', 'sha256')):
                    raise ValueError('El origen ofrece otra versión; conservar la fijada. Ejecutar catalog refresh y download expresamente antes de deploy.')
                if not res.get('size_bytes') or not res.get('sha256') or res.get('resolved') is False:
                    raise ValueError('El origen no proporcionó tamaño y checksum completos.')
                for key in ('policy', 'priority', 'priority_sectors'):
                    if key in ent:
                        res[key] = copy.deepcopy(ent[key])
                nuevo['entries'][pos] = valida(res)
        except Exception as exc:
            errores[ent['id']] = str(exc)
            evento(ent['id'], 'SKIP', str(exc)+' · continuar con el lote')
    return nuevo, errores
