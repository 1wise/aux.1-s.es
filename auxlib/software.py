# Timestamp: 2026-11-09 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Keep native tasksel/comps choices shared by web, console and installers."""
import argparse
from collections import Counter
import hashlib
import json
from functools import lru_cache
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .common import DIR_APP, guarda_json


def huella(dat):
    val = {nom:ent for nom,ent in dat.items() if nom != 'digest_sha256'}
    return hashlib.sha256(json.dumps(val, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def campos(txt):
    """Read Debian control paragraphs, including indented continuation lines."""
    for blo in re.split(r'\n\s*\n', txt.strip()):
        dat = {}
        nom = None
        for lin in blo.splitlines():
            if lin[:1].isspace() and nom:
                dat[nom] += '\n' + lin.strip()
            elif ':' in lin:
                nom, val = lin.split(':', 1)
                dat[nom] = val.strip()
        if dat:
            yield dat


def debian(txt, paq_dat):
    grupos = []
    for ent in campos(txt):
        nom = ent['Task']
        paq = ent.get('Key', '').split()
        if ent.get('Packages') == 'standard':
            paq += paq_dat['standard']
        elif ent.get('Packages'):
            raise ValueError('Modo de tarea no admitido: ' + nom)
        det = paq_dat['packages'].get(paq[0], {}) if paq else {}
        des = ent.get('Description') or det.get('Description') or nom
        grupos.append({'id':nom, 'label':des.splitlines()[0], 'description':des,
                       'section':ent.get('Section', 'user'),
                       'parents':ent.get('Parent', '').split(),
                       'enhances':ent.get('Enhances', ''), 'packages':paq})
    return {'groups':grupos, 'environments':[]}


def fedora(txt):
    raiz = ET.fromstring(txt)
    def rot(ent, nom):
        esp = ent.find(nom + "[@{http://www.w3.org/XML/1998/namespace}lang='es']")
        return esp.text if esp is not None else ent.findtext(nom, '')
    grupos = []
    for ent in raiz.findall('group'):
        tipos = Counter(val.get('type', 'mandatory') for val in ent.findall('packagelist/packagereq'))
        grupos.append({'id':ent.findtext('id'), 'label':rot(ent, 'name'),
                       'description':rot(ent, 'description'),
                       'visible':ent.findtext('uservisible', 'true') == 'true',
                       'package_types':dict(tipos)})
    entornos = []
    for ent in raiz.findall('environment'):
        opt = ent.findall('optionlist/groupid')
        entornos.append({'id':ent.findtext('id'), 'label':rot(ent, 'name'),
                         'description':rot(ent, 'description'),
                         'required':[val.text for val in ent.findall('grouplist/groupid')],
                         'optional':[val.text for val in opt],
                         'default':[val.text for val in opt if val.get('default') == 'true']})
    return {'groups':grupos, 'environments':entornos}


@lru_cache(maxsize=2)
def carga(dis):
    if dis not in ('debian', 'fedora'):
        raise ValueError('Distribución nativa desconocida.')
    dat = json.loads((DIR_APP / 'config/software' / (dis + '.json')).read_text())
    if dat.get('distribution') != dis or dat.get('digest_sha256') != huella(dat):
        raise ValueError('El catálogo de software no coincide con su manifiesto.')
    ids = [ent['id'] for ent in dat['groups']]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9][a-z0-9+_.-]*', nom) for nom in ids):
        raise ValueError('Identificador nativo inválido o duplicado.')
    for ent in dat['groups']:
        if any(not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', nom) for nom in ent.get('packages', [])):
            raise ValueError('Nombre de paquete inválido.')
        if any(nom not in ids for nom in ent.get('parents', [])):
            raise ValueError('La tarea requiere un padre ausente.')
    for ent in dat['environments']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9+_.-]*', ent['id']) or any(nom not in ids for nom in ent['required'] + ent['optional'] + ent['default']):
            raise ValueError('El entorno contiene un grupo ausente o inválido.')
    return dat


def defecto(dis):
    dat = carga(dis)
    sal = {'catalog_sha256':dat['digest_sha256']}
    if dis == 'debian':
        sal['tasks'] = ['standard', 'desktop', 'xfce-desktop', 'ssh-server']
    else:
        sal.update(environment='xfce-desktop-environment', groups=[])
        ent = next(ent for ent in dat['environments'] if ent['id'] == sal['environment'])
        sal['groups'] = ent['default'][:]
    return sal


def resuelve(dis, nativo):
    dat = carga(dis)
    permitidos = {'catalog_sha256', 'tasks'} if dis == 'debian' else {'catalog_sha256', 'environment', 'groups'}
    if not isinstance(nativo, dict) or set(nativo) != permitidos:
        raise ValueError('Selección de software nativo inválida.')
    if nativo['catalog_sha256'] != dat['digest_sha256']:
        raise ValueError('Cambió el catálogo de software; revisar y exportar de nuevo la selección.')
    campo = 'tasks' if dis == 'debian' else 'groups'
    lista = nativo[campo]
    mapa = {ent['id']:ent for ent in dat['groups']}
    if not isinstance(lista, list) or len(lista) > len(mapa) or any(not isinstance(nom, str) or nom not in mapa for nom in lista):
        raise ValueError('La selección contiene una tarea o grupo desconocido.')
    lista = list(dict.fromkeys(lista))
    ent = None
    if dis == 'fedora':
        nom = nativo['environment']
        if not isinstance(nom, str):
            raise ValueError('Entorno inválido.')
        if nom:
            ent = next((ent for ent in dat['environments'] if ent['id'] == nom), None)
            if not ent:
                raise ValueError('Entorno desconocido: ' + nom)
            lista = list(dict.fromkeys(ent['required'] + lista))
    else:
        # A desktop subtask needs its native parent, independent of UI filtering.
        for nom in lista:
            for padre in mapa[nom]['parents']:
                if padre not in lista:
                    lista.append(padre)
    paq = ['@' + nom for nom in lista] if dis == 'fedora' else list(dict.fromkeys(
        paq for nom in lista for paq in mapa[nom]['packages']))
    sal = dict(nativo)
    sal[campo] = lista
    return {'native':sal, 'packages':paq, 'groups':lista,
            'environment':ent['id'] if ent else ''}


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--distro', choices=('debian', 'fedora'), required=True)
    par.add_argument('--input', type=Path, required=True)
    par.add_argument('--package-metadata', type=Path)
    par.add_argument('--source-url', required=True)
    par.add_argument('--release', required=True)
    par.add_argument('--output', type=Path, required=True)
    cfg = par.parse_args()
    txt = cfg.input.read_text()
    if cfg.distro == 'debian':
        if not cfg.package_metadata:
            par.error('Debian necesita --package-metadata con las claves y prioridades del índice de paquetes.')
        dat = debian(txt, json.loads(cfg.package_metadata.read_text()))
    else:
        dat = fedora(txt)
    dat.update(schema='aux-software-catalog-v1', distribution=cfg.distro,
               release=cfg.release, architecture='amd64' if cfg.distro == 'debian' else 'x86_64',
               source_url=cfg.source_url, source_sha256=hashlib.sha256(cfg.input.read_bytes()).hexdigest())
    dat['digest_sha256'] = huella(dat)
    guarda_json(cfg.output, dat)


if __name__ == '__main__':
    main()
