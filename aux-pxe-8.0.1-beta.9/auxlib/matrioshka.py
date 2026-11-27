# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Package an offline deployment envelope with independently verified nested layers."""
import argparse
import hashlib
import importlib.util
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
        prefix='aux-'+VERSION+'/'
        if any(not e.filename.startswith(prefix) for e in arc.infolist()) or arc.read(prefix+'VERSION').decode().strip()!=VERSION:
            raise ValueError('La suite no corresponde a la versión actual.')
        size=sum(e.file_size for e in arc.infolist() if not e.is_dir())
    if size>LIMITE:raise ValueError('La suite supera 24 MB de fuentes; no se cuentan las capas duplicadas del envoltorio.')
    from .wan_boot import informacion
    img,inf=informacion()
    with tempfile.TemporaryDirectory(prefix='aux-matrioshka-') as tmp:
        root=Path(tmp);layers=root/'layers';layers.mkdir();web=root/'web'
        if web_root:shutil.copytree(web_root,web)
        else:
            spec=importlib.util.spec_from_file_location('aux_native_web_builder',DIR_APP/'build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
            build.construye(web)
        # Four sibling payloads match the repository root; the web is auxiliary.
        for p in (web/'downloads').glob('aux-fast-boot.zip*'):p.unlink()
        for p in web.rglob('*.html'):
            p.write_text(p.read_text().replace('downloads/aux-fast-boot.zip','downloads/'+source_zip.name))
        from .release_bundle import nombres
        nombres_all=nombres();img_name=nombres_all['image']
        enlaces=' · '.join('<a href="downloads/'+archivo+'">'+rotulo+'</a>' for archivo,rotulo in [(source_zip.name,'Suite completa'),(nombres_all['aux-pxe'],'aux-pxe'),(nombres_all['tec-cli'],'tec-cli'),(img_name,'Arranque USB básico')])
        page='<!doctype html><html lang="es"><meta charset="utf-8"><title>AUX / Matrioshka</title><h1>Cuatro entregas junto al Git</h1><p><a href="index.html">AUX</a> · '+enlaces+'</p><p>Suite completa, aux-pxe, tec-cli y arranque USB básico al mismo nivel. El presupuesto de la suite es 24 MB de fuentes; el envoltorio se contabiliza aparte. La imagen USB es el bootstrap iPXE actual; el arranque hasta login sigue pendiente.</p></html>'
        (web/'matrioshka.html').write_text(page)
        nom_source=root/source_zip.name;shutil.copy2(source_zip,nom_source)
        payloads={'sources':nom_source,'image':root/img_name}
        shutil.copyfile(img,payloads['image'])
        # Reuse the reviewed module bytes when the four-payload release exists.
        for nom in ('aux-pxe','tec-cli'):
            pth=source_zip.parent/nombres_all[nom]
            if not pth.is_file():
                spec=importlib.util.spec_from_file_location('aux_matrioshka_modules',DIR_APP/'package-modules.py')
                mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.empaqueta(root)
                break
        for nom in ('aux-pxe','tec-cli'):
            pth=source_zip.parent/nombres_all[nom];dst=root/nombres_all[nom]
            if pth.is_file():
                if sha(pth)!=Path(str(pth)+'.sha256').read_text().split()[0]:raise ValueError('SHA-256 incorrecto del módulo '+nom)
                shutil.copyfile(pth,dst)
            with zipfile.ZipFile(dst) as arc:
                if arc.testzip():raise ValueError('Módulo ZIP dañado: '+nom)
                info=json.loads(arc.read('modules/'+nom+'.json'))
                if info['version']!=VERSION or info['module']!=nom:raise ValueError('Versión de módulo incorrecta: '+nom)
            payloads[nom]=dst
        (web/'downloads').mkdir(exist_ok=True)
        for pth in payloads.values():
            Path(str(pth)+'.sha256').write_text(sha(pth)+'  '+pth.name+'\n')
            for arc in (pth, Path(str(pth)+'.sha256')):
                shutil.copyfile(arc, web/'downloads'/arc.name)
        from .release_page import publica_descargas
        from .navigation import publica_navegacion
        from .branding import registro
        publica_descargas(web, registro()['project']['url'])
        if 'class="sidebar"' in (web/'index.html').read_text():
            publica_navegacion(web)
        for pth in payloads.values():
            for nom in (pth.name, pth.name+'.sha256'):
                (web/'downloads'/nom).unlink()
        # Reconstruct shared web assets from the four complete payloads at deploy time.
        # This keeps the envelope within hosting limits without thinning a product ZIP.
        copias={inf['sha256']:('image',None,img.stat().st_size)}
        for nom in ('aux-pxe','tec-cli'):
            with zipfile.ZipFile(payloads[nom]) as arc:
                for ent in arc.infolist():
                    if ent.is_dir() or ent.file_size<16384:continue
                    dig=hashlib.sha256(arc.read(ent)).hexdigest()
                    copias.setdefault(dig,(nom,ent.filename,ent.file_size))
        restaurar=[]
        for pth in sorted(web.rglob('*')):
            if pth.is_symlink():raise ValueError('No se admiten enlaces en la web empaquetada.')
            if not pth.is_file() or pth.stat().st_size<16384:continue
            dig=sha(pth)
            if dig not in copias:continue
            nom,miembro,tam=copias[dig]
            restaurar.append({'path':pth.relative_to(web).as_posix(),'layer':nom,'member':miembro,'sha256':dig,'size_bytes':tam})
            pth.unlink()
        nom_web=layers/'web.zip';zip_arbol(web,nom_web);shutil.rmtree(web)
        dat={'schema':'aux-matrioshka-v2','version':VERSION,'budget':{'suite_source_bytes':size,'suite_limit_bytes':LIMITE,'outer_layers_counted_separately':True},'repository':{'source_directory':'suite','source_prefix':'aux-'+VERSION+'/','deliverables_in_root':True,'git_metadata_included':False},'minimal_image':{'type':'GRUB hybrid ISO/USB iPXE bootstrap','compression':None,'raw_size_bytes':img.stat().st_size,'raw_sha256':inf['sha256'],'menu_url':inf['menu_url'],'new_linux_rescue':False,'boot_test':'not-tested'},'layers':{}}
        for nom,p in [('web',nom_web),*payloads.items()]:dat['layers'][nom]={'path':p.relative_to(root).as_posix(),'sha256':sha(p),'size_bytes':p.stat().st_size,'download_name':p.name if nom!='web' else None}
        dat['web_restore']=restaurar
        (root/'MANIFEST.json').write_text(json.dumps(dat,ensure_ascii=False,indent=2)+'\n')
        shutil.copy2(DIR_APP/'packaging/deploy-matrioshka.py',root/'DEPLOY.py')
        (root/'README.md').write_text('# AUX '+VERSION+' / Matrioshka\n\nCuatro entregas hermanas en la raíz: suite completa ZIP, aux-pxe ZIP, tec-cli ZIP e imagen básica de arranque USB .img. Cada archivo tiene SHA-256. La web preparada es una capa auxiliar; no es una quinta imagen de producto.\n\nPlan sin escritura:\n\n    python3 DEPLOY.py --web-root ./web-para-subir\n\nCrear la web con las cuatro descargas:\n\n    python3 DEPLOY.py --web-root ./web-para-subir --apply\n\nPreparar también un directorio de trabajo como el repositorio: fuentes en suite/ y las cuatro entregas a su lado:\n\n    python3 DEPLOY.py --web-root ./web-para-subir --sources-root ./repositorio-aux --apply\n\nUsar destinos nuevos. El Git original conserva sus metadatos; no se empaquetan .git, credenciales ni historial privado. Un clon del repositorio tiene las cuatro entregas en el mismo nivel que .git y suite/. Los paquetes son salidas del árbol suite/, por lo que no se incluyen recursivamente a sí mismos.\n\nPara Bastion sin Python, preparar localmente y subir el contenido de web-para-subir por FTPS. La imagen .img ya está sin comprimir y se usa con la herramienta habitual para grabar USB. Este desplegador no escribe discos ni instala servicios.\n\nLa imagen básica es el bootstrap iPXE existente para BIOS y UEFI x86_64, sin nueva aceptación hasta login ni Rescue Linux recién compilada. Las fuentes de Rescue siguen disponibles.\n\n24 MB es el límite de fuentes de la suite; módulos duplicados, las cuatro entregas y el envoltorio se contabilizan aparte. Los self-assamblers trabajan en suite/self-assamble/ dentro del directorio de trabajo extraído.\n')
        salida.parent.mkdir(parents=True,exist_ok=True);zip_arbol(root,salida)
    Path(str(salida)+'.sha256').write_text(sha(salida)+'  '+salida.name+'\n')
    return {'archive':str(salida),'archive_bytes':salida.stat().st_size,'sha256':sha(salida),'suite_source_bytes':size,'suite_limit_bytes':LIMITE}


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--source-zip',required=True,type=Path);par.add_argument('--web-root',type=Path);par.add_argument('--output',required=True,type=Path);args=par.parse_args(argv)
    print(json.dumps(crea(args.output,args.source_zip,args.web_root),ensure_ascii=False));return 0
