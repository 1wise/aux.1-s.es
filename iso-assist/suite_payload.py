#!/usr/bin/env python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Package declared release files only; local state never enters a public Live."""
import hashlib
import io
from pathlib import Path
import tarfile

DIRS={'auxlib','ui','profiles','config','assist','tec','cli','src','assets','fonts',
      'nginx','ovh','usb','iso','iso-assist','debian'}
ENTRADAS=('aux-setup','aux-profile','aux-catalog','aux-enter','aux-assist','aux-tools','aux-images')
RAIZ=set(ENTRADAS)|{'fast-boot.json','download.sh','deploy.sh','generate.sh','build.py',
    'install-web.py','url.txt','light-url.txt','heavy-url.txt','alpine-sources.json','alpine-SHA256SUMS'}


def paquete_suite(raiz):
    raiz=Path(raiz).resolve();manifest=raiz/'SHA256SUMS'
    if not manifest.is_file():raise ValueError('Usar el paquete completo de AUX con SHA256SUMS.')
    archivos={}
    for lin in manifest.read_text().splitlines():
        sha,nom=lin.split('  ',1);rel=Path(nom)
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Ruta inválida en SHA256SUMS.')
        if not (nom in RAIZ or len(rel.parts)>1 and rel.parts[0] in DIRS):continue
        pth=raiz/rel
        if pth.is_symlink() or not pth.resolve().is_relative_to(raiz):raise ValueError('Fuente enlazada fuera del paquete.')
        dato=pth.read_bytes()
        if hashlib.sha256(dato).hexdigest()!=sha:
            raise ValueError('Fuente modificada respecto a SHA256SUMS: '+nom+'. Usar una entrega completa verificada.')
        archivos[nom]=(dato,pth.stat().st_mode & 0o777)
    if not set(ENTRADAS)<=archivos.keys():raise ValueError('Faltan aplicaciones en las fuentes de AUX.')
    archivos['SHA256SUMS']=(manifest.read_bytes(),0o644)
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz') as arc:
        for nom,(dato,modo) in sorted(archivos.items()):
            ent=tarfile.TarInfo(nom);ent.size=len(dato);ent.mode=modo
            arc.addfile(ent,io.BytesIO(dato))
    return buf.getvalue(),len(archivos)
