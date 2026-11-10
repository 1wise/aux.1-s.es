# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author & Credits: https://www.alawise.es/1-s
"""Shared path, process, integrity and atomic-write primitives."""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

DIR_APP = Path(__file__).resolve().parent.parent
CABECERA = '# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4\n# Author & Credits: https://www.alawise.es/1-s\n'


def suma(pth):
    dig = hashlib.sha256()
    with Path(pth).open('rb') as arc:
        for dat in iter(lambda: arc.read(1048576), b''):
            dig.update(dat)
    return dig.hexdigest()


def atomico(pth, dat, modo=0o644):
    pth = Path(pth)
    pth.parent.mkdir(parents=True, exist_ok=True)
    fd, nom = tempfile.mkstemp(prefix='.' + pth.name + '.', dir=pth.parent)
    try:
        with os.fdopen(fd, 'wb') as arc:
            arc.write(dat.encode() if isinstance(dat, str) else dat)
            arc.flush()
            os.fsync(arc.fileno())
        os.chmod(nom, modo)
        os.replace(nom, pth)
    finally:
        Path(nom).unlink(missing_ok=True)


def guarda_json(pth, dat, modo=0o644):
    atomico(pth, json.dumps(dat, ensure_ascii=False, indent=2) + '\n', modo)


def dentro(raiz, rel):
    # Reject escaping symlinks before a privileged install writes through them.
    raiz = Path(raiz).resolve()
    dst = raiz / rel
    if Path(rel).is_absolute() or not dst.resolve().is_relative_to(raiz):
        raise ValueError('Ruta fuera del destino: ' + str(rel))
    return dst


def ejecuta(cmd, aplicar=False, **cfg):
    print('+', shlex.join([str(val) for val in cmd]), flush=True)
    if aplicar:
        return subprocess.run([str(val) for val in cmd], check=True, **cfg)
    return None


def identificador(txt):
    if not isinstance(txt, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,95}', txt):
        raise ValueError('Identificador inválido: ' + repr(txt))
    return txt
