#!/usr/bin/env python3
# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author & Credits: https://www.alawise.es/1-s
"""Build the integrated static website without deploying or touching server state."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
from types import ModuleType
import zipfile

from auxlib import VERSION

DIR_APP=Path(__file__).resolve().parent


def motor():
    pth=DIR_APP/'generate.sh'
    txt=pth.read_text().split("<<'AUXPY'\n",1)[1].rsplit('\nAUXPY\n',1)[0]
    mod=ModuleType('aux_generate')
    mod.__file__=str(pth)
    exec(compile(txt,str(pth),'exec'),mod.__dict__)
    return mod


def empaqueta(destino):
    excl={'dist','.git','.openai','.venv','__pycache__'}
    files=[pth for pth in sorted(DIR_APP.rglob('*')) if pth.is_file() and
           not set(pth.relative_to(DIR_APP).parts)&excl and pth.suffix!='.pyc' and pth.name!='SHA256SUMS']
    sumas=''.join(hashlib.sha256(pth.read_bytes()).hexdigest()+'  '+str(pth.relative_to(DIR_APP))+'\n' for pth in files)
    nombre='aux-suite-'+VERSION
    zip_pth=destino/'downloads'/(nombre+'.zip')
    zip_pth.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_pth,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as arc:
        for pth in files:
            arc.write(pth,str(Path(nombre)/pth.relative_to(DIR_APP)))
        arc.writestr(nombre+'/SHA256SUMS',sumas)
    with zipfile.ZipFile(zip_pth) as arc:
        if arc.testzip():
            raise ValueError('Falló la verificación del paquete generado.')
    zip_pth.with_suffix('.zip.sha256').write_text(hashlib.sha256(zip_pth.read_bytes()).hexdigest()+'  '+zip_pth.name+'\n')
    return zip_pth


def construye(destino,paquete=False):
    destino=destino.resolve()
    if destino==DIR_APP or DIR_APP.is_relative_to(destino):
        raise ValueError('La salida no puede sustituir el árbol de fuentes.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    eng=motor()
    args=sys.argv
    try:
        sys.argv=[str(DIR_APP/'generate.sh')]
        cfg=eng.obt_args('generate',DIR_APP)
    finally:
        sys.argv=args
    eng.carga_recursos()
    with tempfile.TemporaryDirectory(prefix='aux7-web-build-',dir=destino.parent) as tmp:
        cfg.output=Path(tmp)/'public'
        cfg.cache=Path(tmp)/'cache'
        cfg.output.mkdir();cfg.cache.mkdir()
        cfg.tec_enabled=True
        recs=eng.obt_catalog((DIR_APP/'url.txt').read_text())
        eng.gen_pages(recs,cfg,state='source')
        for pth in cfg.output.rglob('*.php'):
            pth.unlink()
        (cfg.output/'version.json').write_text(json.dumps({'version':VERSION,'applications':['workspace.html','installer.html','catalogue.html','systems.html'],'compiled_new_isos':False},indent=2)+'\n')
        if paquete:
            empaqueta(cfg.output)
        requeridos=['index.html','workspace.html','installer.html','catalogue.html','systems.html','assets/workspace.js','assets/workspace.css']
        if any(not (cfg.output/nom).is_file() for nom in requeridos):
            raise ValueError('Faltan aplicaciones en la salida web.')
        if destino.exists():
            if not (destino/'index.html').is_file():
                raise ValueError('La salida existente no es una web generada; se conserva intacta.')
            shutil.rmtree(destino)
        shutil.copytree(cfg.output,destino)
    from auxlib.webapps import modelo
    dat = modelo(recs)
    return {'version':VERSION,'output':str(destino),'resources':len(recs),
            'catalog_entries':len(dat['entries']),
            'external_netboot_entries':sum(ent.get('remote_only',False) for ent in dat['entries']),
            'applications':requeridos[:5]}


def main():
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--output',type=Path,default=DIR_APP/'dist')
    par.add_argument('--package-source',action='store_true')
    cfg=par.parse_args()
    print(json.dumps(construye(cfg.output,cfg.package_source),ensure_ascii=False))


if __name__=='__main__':
    main()
