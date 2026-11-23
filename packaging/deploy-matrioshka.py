#!/usr/bin/env python3
# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Unpack verified web, source and minimal-image layers without a network connection."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile


def sha(pth):
    with pth.open('rb') as arc:return hashlib.file_digest(arc,'sha256').hexdigest()


def valida_zip(pth):
    with zipfile.ZipFile(pth) as arc:
        vistos=set()
        for ent in arc.infolist():
            rel=Path(ent.filename)
            if rel.is_absolute() or '..' in rel.parts or '\\' in ent.filename or ent.filename in vistos:raise ValueError('Ruta de paquete no permitida.')
            vistos.add(ent.filename)
            modo=ent.external_attr>>16
            if stat.S_IFMT(modo) not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError('El paquete contiene una entrada no regular.')
        if arc.testzip():raise ValueError('El paquete no supera la verificación ZIP.')


def extrae(pth,dst):
    # Paths and entry types were checked before any destination was created.
    dst.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(pth) as arc:
        for ent in arc.infolist():
            dest=dst/ent.filename
            if ent.is_dir():dest.mkdir(parents=True,exist_ok=True);continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            with arc.open(ent) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)
            dest.chmod(0o755 if ent.external_attr>>16&0o111 else 0o644)


def prepara(base,web_root,sources_root=None,apply=False):
    base=Path(base).resolve();web=Path(web_root).expanduser().resolve();src=Path(sources_root).expanduser().resolve() if sources_root else None
    dat=json.loads((base/'MANIFEST.json').read_text())
    if dat.get('schema')!='aux-matrioshka-v1':raise ValueError('Manifiesto de matrioshka desconocido.')
    if web.exists() or src and src.exists():raise ValueError('Elegir directorios nuevos; se conserva cualquier despliegue existente.')
    if src and (src.is_relative_to(web) or web.is_relative_to(src)):raise ValueError('Separar las fuentes de trabajo del directorio público.')
    if web.is_relative_to(base) and web==base or src==base:raise ValueError('El destino debe ser distinto del paquete.')
    layers={}
    for nom,ent in dat['layers'].items():
        rel=Path(ent['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('Ruta de capa inválida.')
        pth=base/rel
        if pth.is_symlink() or not pth.resolve().is_relative_to(base) or not pth.is_file():raise ValueError('Falta una capa regular.')
        if pth.stat().st_size!=ent['size_bytes'] or sha(pth)!=ent['sha256']:raise ValueError('SHA-256 incorrecto en la capa '+nom)
        layers[nom]=pth
    for nom in ('web','sources'):valida_zip(layers[nom])
    plan={'version':dat['version'],'web_root':str(web),'sources_root':str(src) if src else None,'suite_source_bytes':dat['budget']['suite_source_bytes'],'suite_limit_bytes':24000000,'apply':apply,'image':dat['minimal_image']}
    if not apply:return plan
    extrae(layers['web'],web)
    downloads=web/'downloads';downloads.mkdir(exist_ok=True)
    for nom in ('sources','image'):
        ent=dat['layers'][nom];out=downloads/ent['download_name']
        if out.exists():raise ValueError('Colisión de descarga: '+out.name)
        shutil.copyfile(layers[nom],out)
        (downloads/(out.name+'.sha256')).write_text(ent['sha256']+'  '+out.name+'\n')
    if src:extrae(layers['sources'],src)
    shutil.copyfile(base/'MANIFEST.json',web/'matrioshka-manifest.json')
    return plan


def main():
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--web-root',required=True,type=Path);par.add_argument('--sources-root',type=Path);par.add_argument('--apply',action='store_true');args=par.parse_args()
    print(json.dumps(prepara(Path(__file__).resolve().parent,args.web_root,args.sources_root,args.apply),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
