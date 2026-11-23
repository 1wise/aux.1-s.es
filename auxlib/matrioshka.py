# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Package an offline deployment envelope with independently verified nested layers."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from . import VERSION
from .common import DIR_APP

LIMITE=24000000


def sha(pth):
    with pth.open('rb') as arc:return hashlib.file_digest(arc,'sha256').hexdigest()


def zip_arbol(folder,salida):
    with zipfile.ZipFile(salida,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as arc:
        for p in sorted(Path(folder).rglob('*')):
            if p.is_symlink():raise ValueError('No se admiten enlaces en la web empaquetada.')
            if p.is_file():arc.write(p,p.relative_to(folder).as_posix())


def crea(salida,source_zip,web_root=None):
    salida=Path(salida).resolve();source_zip=Path(source_zip).resolve()
    if salida.exists():raise ValueError('La entrega existente es inmutable; elegir un archivo nuevo.')
    expected=Path(str(source_zip)+'.sha256').read_text().split()[0]
    if sha(source_zip)!=expected:raise ValueError('La suite no coincide con su SHA-256.')
    with zipfile.ZipFile(source_zip) as arc:
        if arc.testzip():raise ValueError('La suite contiene archivos ZIP dañados.')
        size=sum(e.file_size for e in arc.infolist() if not e.is_dir())
    if size>LIMITE:raise ValueError('La suite supera 24 MB de fuentes; no se cuentan las capas duplicadas del envoltorio.')
    from .wan_boot import informacion
    img,inf=informacion()
    with tempfile.TemporaryDirectory(prefix='aux-matrioshka-') as tmp:
        root=Path(tmp);layers=root/'layers';layers.mkdir();web=root/'web'
        if web_root:shutil.copytree(web_root,web)
        else:
            import importlib.util
            spec=importlib.util.spec_from_file_location('aux_native_web_builder',DIR_APP/'build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
            build.construye(web)
        # One source layer supplies public downloads and an optional working tree.
        for p in (web/'downloads').glob('aux-fast-boot.zip*'):p.unlink()
        for p in web.rglob('*.html'):
            p.write_text(p.read_text().replace('downloads/aux-fast-boot.zip','downloads/'+source_zip.name))
        img_name='aux-minimal-ipxe-'+VERSION+'.img.gz'
        page='<!doctype html><html lang="es"><meta charset="utf-8"><title>AUX / Matrioshka</title><h1>Web, fuentes e imagen mínima</h1><p><a href="index.html">AUX</a> · <a href="downloads/'+source_zip.name+'">Suite completa</a> · <a href="downloads/'+img_name+'">Imagen mínima iPXE</a></p><p>El presupuesto de la suite es 24 MB de fuentes. El envoltorio contiene capas adicionales. La imagen incluida es el bootstrap iPXE actual, no una Rescue Linux nueva; el arranque hasta login sigue pendiente.</p></html>'
        (web/'matrioshka.html').write_text(page)
        nom_source=layers/source_zip.name;shutil.copy2(source_zip,nom_source)
        nom_image=layers/img_name
        with img.open('rb') as src,nom_image.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6) as dst:shutil.copyfileobj(src,dst)
        nom_web=layers/'web.zip';zip_arbol(web,nom_web);shutil.rmtree(web)
        dat={'schema':'aux-matrioshka-v1','version':VERSION,'budget':{'suite_source_bytes':size,'suite_limit_bytes':LIMITE,'outer_layers_counted_separately':True},'minimal_image':{'type':'GRUB hybrid ISO/USB iPXE bootstrap','raw_size_bytes':img.stat().st_size,'raw_sha256':inf['sha256'],'menu_url':inf['menu_url'],'new_linux_rescue':False,'boot_test':'not-tested'},'layers':{}}
        for nom,p,download in [('web',nom_web,None),('sources',nom_source,source_zip.name),('image',nom_image,img_name)]:dat['layers'][nom]={'path':p.relative_to(root).as_posix(),'sha256':sha(p),'size_bytes':p.stat().st_size,'download_name':download}
        (root/'MANIFEST.json').write_text(json.dumps(dat,ensure_ascii=False,indent=2)+'\n')
        shutil.copy2(DIR_APP/'packaging/deploy-matrioshka.py',root/'DEPLOY.py')
        (root/'README.md').write_text('# AUX '+VERSION+' / Matrioshka\n\nTres capas verificadas: web lista, fuentes y la imagen mínima iPXE actual.\n\nPlan sin escritura:\n\n    python3 DEPLOY.py --web-root ./web-para-subir\n\nCrear la web con sus descargas incluidas:\n\n    python3 DEPLOY.py --web-root ./web-para-subir --apply\n\nOpcional: extraer también las fuentes de trabajo fuera de la web:\n\n    python3 DEPLOY.py --web-root ./web-para-subir --sources-root ./fuentes-aux --apply\n\nUsar destinos nuevos. Para Bastion sin Python, ejecutar aquí y subir el contenido de web-para-subir mediante FTPS. Para Excalibur, copiar ese árbol al destino después de revisar su configuración. La publicación no instala servicios ni inicia enrolamiento. Las fuentes y la imagen comprimida quedan en downloads/. Descomprimir la imagen con gzip -dk antes de grabarla con la herramienta habitual. No se escribe en discos desde este desplegador.\n\nLa imagen incluida es el bootstrap iPXE existente (BIOS y UEFI x86_64), sin nueva aceptación hasta login. La receta de Rescue Linux está en las fuentes; no se afirma una nueva ISO compilada.\n\n24 MB es el límite del árbol de fuentes de la suite, incluida su imagen actual. El tamaño del envoltorio y las capas repetidas se informa aparte en MANIFEST.json. Los self-assamblers trabajan en self-assamble/ dentro de las fuentes extraídas.\n')
        salida.parent.mkdir(parents=True,exist_ok=True);zip_arbol(root,salida)
    Path(str(salida)+'.sha256').write_text(sha(salida)+'  '+salida.name+'\n')
    return {'archive':str(salida),'archive_bytes':salida.stat().st_size,'sha256':sha(salida),'suite_source_bytes':size,'suite_limit_bytes':LIMITE}


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--source-zip',required=True,type=Path);par.add_argument('--web-root',type=Path);par.add_argument('--output',required=True,type=Path);args=par.parse_args(argv)
    print(json.dumps(crea(args.output,args.source_zip,args.web_root),ensure_ascii=False));return 0
