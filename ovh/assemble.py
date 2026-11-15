#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.1.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Materialize one complete B/P/T public root; never upload private TEC state."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

PRIVADOS = {'.git', '.env', '.ssh', '__pycache__', 'usuarios.json', 'tecnicos.json',
            'solicitudes.json', 'manage.php', 'sessions', 'data', 'secret', 'secrets', 'logs'}


def sha(pth):
    with pth.open('rb') as arc:
        return hashlib.file_digest(arc, 'sha256').hexdigest()


def inventario(pth, raices, rel=Path('.'), activos=None):
    real = pth.resolve(strict=True)
    if not any(real.is_relative_to(raiz) for raiz in raices):
        raise ValueError('Enlace fuera de las raíces autorizadas: ' + str(pth))
    if pth.name in PRIVADOS or pth.name.endswith(('.key', '.secret', '.pem', '.log')):
        raise ValueError('Material privado en árbol público: ' + str(pth))
    inf = real.stat()
    if stat.S_ISREG(inf.st_mode):
        return [(real, rel)]
    if not stat.S_ISDIR(inf.st_mode):
        raise ValueError('Entrada no regular: ' + str(pth))
    activos = set() if activos is None else set(activos)
    if real in activos:
        raise ValueError('Bucle de enlaces: ' + str(pth))
    activos.add(real)
    return [ent for src in sorted(real.iterdir()) for ent in
            inventario(src, raices, rel / src.name, activos)]


def prepara(pth_web, pth_iso, pth_tec, pth_sal, aplicar=False, adicionales=()):
    pth_web, pth_iso, pth_sal = (Path(p).resolve() for p in (pth_web, pth_iso, pth_sal))
    if pth_sal.exists() or any(pth_sal.is_relative_to(p) for p in (pth_web, pth_iso)):
        raise ValueError('Usar un destino nuevo fuera de las fuentes; no se sobrescriben despliegues.')
    raices = [pth_web, pth_iso] + [Path(p).resolve() for p in adicionales]
    archivos = dict((str(rel), src) for src, rel in inventario(pth_web, raices))
    # The existing catalog uses root-level ISO filenames, not a second ISO copy.
    for src in sorted(pth_iso.glob('*.iso')):
        real = src.resolve(strict=True)
        if not any(real.is_relative_to(p) for p in raices):
            raise ValueError('ISO fuera de las raíces permitidas.')
        if src.name in archivos and sha(archivos[src.name]) != sha(real):
            raise ValueError('Colisión de ISO con contenido distinto: ' + src.name)
        archivos[src.name] = real
    if pth_tec:
        tec = Path(pth_tec).resolve()
        if (tec / 'manage.php').exists() or not (tec / 'index.php').is_file():
            raise ValueError('TEC debe ser únicamente tec/web, nunca el directorio administrativo.')
        if any(rel.startswith('tec/') for rel in archivos):
            raise ValueError('La raíz fuente ya contiene tec/; no se mezcla con otra copia.')
        archivos.update((str(Path('tec') / rel), src) for src, rel in inventario(tec, [tec]))
    datos = {'version': '6.1.0-dev.1', 'shared_root': str(pth_sal),
             'hosts': ['b.1-s.es', 'p.1-s.es', 't.1-s.es'],
             'files': len(archivos), 'bytes': sum(src.stat().st_size for src in archivos.values()),
             'iso_count': sum(rel.endswith('.iso') for rel in archivos), 'applied': aplicar}
    if not aplicar:
        return datos
    if shutil.disk_usage(pth_sal.parent).free < datos['bytes'] + 64 * 1024**2:
        raise ValueError('Espacio insuficiente para una copia física completa.')
    pth_sal.mkdir(mode=0o755)
    for rel, src in archivos.items():
        dst = pth_sal / rel
        dst.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        shutil.copyfile(src, dst, follow_symlinks=True)
        dst.chmod(0o644)
    shutil.copyfile(Path(__file__).parent / 'shared.htaccess', pth_sal / '.htaccess')
    (pth_sal / 'bastion-manifest.json').write_text(json.dumps(datos, indent=2) + '\n')
    return datos


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--web-root', required=True, type=Path)
    par.add_argument('--iso-dir', required=True, type=Path)
    par.add_argument('--tec-web', type=Path)
    par.add_argument('--output', required=True, type=Path)
    par.add_argument('--allow-root', action='append', default=[], type=Path,
                     help='Explicit trusted root for links to extracted RAM/disk trees')
    par.add_argument('--apply', action='store_true', help='Copy after validation; default is inventory only')
    cfg = par.parse_args()
    try:
        print(json.dumps(prepara(cfg.web_root, cfg.iso_dir, cfg.tec_web, cfg.output,
                                 cfg.apply, cfg.allow_root), indent=2))
    except (ValueError, OSError) as exc:
        par.exit(1, str(exc) + '\nNo se ha enviado nada a OVH. Un destino parcial debe revisarse, no publicarse.\n')


if __name__ == '__main__':
    main()
