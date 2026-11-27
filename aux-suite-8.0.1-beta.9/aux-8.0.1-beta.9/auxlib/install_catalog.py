# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Select the operator's inputs before the installer changes the host."""
import json
import os
from pathlib import Path
import sys

from .common import crea_si_falta
from .catalog_v8 import carga, ruta_cfg
from .checkstatus import vigente
from .settings import lee_config


def seleccion(src, root, servicio, config=None):
    personal = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'aux/config.json'
    explicita = config or os.environ.get('AUX_CONFIG_FILE')
    arc_cfg = Path(explicita or personal).expanduser().resolve()
    nueva = None
    semilla = None
    if explicita or arc_cfg.exists():
        dat = lee_config(arc_cfg)
    else:
        # The legacy server file remains the service configuration. A fresh
        # operator configuration keeps mutable catalogue and status together.
        dat = dict(servicio)
        for campo in ('catalog_file', 'catalog_profile', 'checksums', 'status_file', 'evidence_file',
                      'url_file', 'light_url_file', 'heavy_url_file', 'metadata_cache', 'catalog_sources_file'):
            val = dat.get(campo)
            if val and not Path(val).is_absolute() and (root/val).exists():
                if campo != 'catalog_file' or val != 'catalog.json':
                    dat[campo] = str((root/val).resolve())
        nueva = dat
    arc_cat = ruta_cfg(dat, 'catalog_file', 'catalog.json', arc_cfg)
    if not arc_cat.is_file():
        if nueva is None or arc_cat != arc_cfg.parent/'catalog.json':
            raise ValueError(f'Falta el catálogo configurado: {arc_cat} (catalog_file en {arc_cfg}).')
        semilla = root/'catalog.json' if (root/'catalog.json').is_file() else src/'catalog.json'
    carga(semilla or arc_cat, src/'fast-boot.json' if nueva is not None else arc_cfg)
    return arc_cfg, arc_cat, nueva, semilla


def genera_instalacion(root, seleccionada, orden, tec=None):
    arc_cfg, arc_cat, nueva, semilla = seleccionada
    if nueva is not None:
        if semilla:
            crea_si_falta(arc_cat, semilla.read_bytes())
        crea_si_falta(arc_cfg, (json.dumps(nueva, ensure_ascii=False, indent=2)+'\n').encode())
    # Re-read after first-use creation so a concurrent change always wins.
    dat = lee_config(arc_cfg)
    arc_cat = ruta_cfg(dat, 'catalog_file', 'catalog.json', arc_cfg)
    cat = carga(arc_cat, arc_cfg)
    arc_est = ruta_cfg(dat, 'status_file', 'state/status.json', arc_cfg)
    est = json.loads(arc_est.read_text()) if arc_est.is_file() else {}
    base = [sys.executable, str(root/'aux')]
    flags = ['--config', str(arc_cfg), '--catalog', str(arc_cat)]
    if not vigente(est, cat, dat) or est.get('remote_inventory', {}).get('errors'):
        orden(*base, 'checkstatus', *flags)
    orden(*base, 'generate', *flags, '--output', str(root/'html'), '--apply', *(['--tec',tec] if tec else []))
