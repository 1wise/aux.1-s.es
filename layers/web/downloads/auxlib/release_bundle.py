# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Place four immutable release payloads beside a repository's .git directory."""
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
    with Path(pth).open('rb') as arc:return hashlib.file_digest(arc,'sha256').hexdigest()


def nombres():
    return {'sources':'aux-suite-'+VERSION+'.zip','aux-pxe':'aux-pxe-'+VERSION+'.zip',
            'tec-cli':'tec-cli-'+VERSION+'.zip','image':'aux-minimal-ipxe-'+VERSION+'.img'}


def prepara(destino):
    pth_dst=Path(destino).resolve();nom_all=nombres()
    # Do not overwrite a reviewed release or include the output tree in itself.
    if pth_dst.is_relative_to(DIR_APP.resolve()):raise ValueError('Guardar las cuatro entregas fuera del árbol suite/.')
    if any((pth_dst/n).exists() or (pth_dst/(n+'.sha256')).exists() for n in nom_all.values()):
        raise ValueError('La entrega existente es inmutable; elegir otro directorio.')
    spec=importlib.util.spec_from_file_location('aux_release_modules',DIR_APP/'package-modules.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    files=sorted(set(mod.archivos('aux-pxe'))|set(mod.archivos('tec-cli')))
    sumas=DIR_APP/'SHA256SUMS'
    sumas.write_text(''.join(sha(p)+'  '+p.relative_to(DIR_APP).as_posix()+'\n' for p in files))
    files.append(sumas);tam_src=sum(p.stat().st_size for p in files)
    if tam_src>LIMITE:raise ValueError('La suite supera 24 MB de fuentes.')
    from .wan_boot import informacion
    img,inf=informacion()
    dat={'schema':'aux-release-bundle-v1','version':VERSION,
         'budget':{'suite_source_bytes':tam_src,'suite_limit_bytes':LIMITE,'outer_layers_counted_separately':True},
         'layout':{'source_directory':'suite','deliverables_in_repository_root':True},'deliverables':{}}
    with tempfile.TemporaryDirectory(prefix='aux-release-') as tmp:
        pth_tmp=Path(tmp)
        with zipfile.ZipFile(pth_tmp/nom_all['sources'],'w',zipfile.ZIP_DEFLATED,compresslevel=6) as arc:
            for p in files:arc.write(p,'aux-'+VERSION+'/'+p.relative_to(DIR_APP).as_posix())
        dat['budget']['suite_archive_bytes']=(pth_tmp/nom_all['sources']).stat().st_size
        if dat['budget']['suite_archive_bytes']>LIMITE:raise ValueError('La suite completa supera 24 MB.')
        mod.empaqueta(pth_tmp)
        shutil.copyfile(img,pth_tmp/nom_all['image'])
        pth_dst.mkdir(parents=True,exist_ok=True)
        for nom,archivo in nom_all.items():
            pth=pth_tmp/archivo;dig=sha(pth)
            shutil.copyfile(pth,pth_dst/archivo)
            (pth_dst/(archivo+'.sha256')).write_text(dig+'  '+archivo+'\n')
            dat['deliverables'][nom]={'path':archivo,'size_bytes':pth.stat().st_size,'sha256':dig}
    dat['minimal_image']={'raw_sha256':inf['sha256'],'raw_size_bytes':img.stat().st_size,
                          'menu_url':inf['menu_url'],'new_linux_rescue':False,'boot_test':'not-tested'}
    (pth_dst/'RELEASE.json').write_text(json.dumps(dat,ensure_ascii=False,indent=2)+'\n')
    return dat


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--output',required=True,type=Path)
    print(json.dumps(prepara(par.parse_args(argv).output),ensure_ascii=False));return 0
