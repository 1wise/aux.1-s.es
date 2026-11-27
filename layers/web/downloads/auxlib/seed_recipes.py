# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Resolve AUX-owned starter recipes from official publisher metadata."""
import argparse
import configparser
import datetime
import hashlib
import json
from pathlib import Path
import re
import urllib.request
from .catalog_v8 import carga,guarda,valida
from .common import DIR_APP,guarda_json
from .catalog_audit import comprueba


def texto(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AUX-Recipes/8.0'}),timeout=20) as rsp:
        raw=rsp.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('Publisher metadata exceeded its size limit.')
    return raw.decode('utf-8')


def sidecar(url):
    try:return re.search(r'\b([a-fA-F0-9]{64})\b',texto(url)).group(1).lower()
    except (OSError,ValueError,AttributeError):return None


def linux(id,family,release,kernel,initrd,args,index,procedure,hashes=None,extra=()):
    cmp=[]
    for url in (kernel,initrd,*extra):
        sha=(hashes or {}).get(url)
        chk=comprueba({'id':id,'original_url':url,'artifact_type':'component'},timeout=20)
        cmp.append({'original_url':url,'filename':url.rsplit('/',1)[-1],'sha256':sha,'size_bytes':chk.get('size_bytes'),
                    'http_status':chk.get('http_status'),'checked_at':chk['checked_at'],'http_verified':chk['verified']})
    approved=all(c['http_verified'] for c in cmp)
    return valida({'id':id,'name':'AUX · '+family.title()+' netboot / kernel + initrd','family':family,'release':release,'architecture':'x86_64',
        'kind':'netboot','artifact_type':'component','original_url':kernel,'policy':'E04','sha256':cmp[0]['sha256'],'size_bytes':cmp[0]['size_bytes'],
        'source_index':index,'checksum_source':index,'procedure_url':procedure,'source_id':id,'recipe_owner':'AUX','components':cmp,
        'recipe_notes':'Receta propia revisada con metadatos oficiales. HTTP comprobado; arranque BIOS/UEFI hasta login pendiente.',
        'recipe':{'entry_id':id,'label':'AUX '+family.title()+' '+release,'type':'linux','architecture':'x86_64','firmware':'any',
                  'kernel_url':kernel,'initrd_url':initrd,'kernel_args':args,'menu_url':'','approved':approved}})


def debian():
    base='https://deb.debian.org/debian/dists/stable/'
    rel=texto(base+'Release');ver=re.search(r'^Version:\s*(.+)$',rel,re.M).group(1).strip();codename=re.search(r'^Codename:\s*(.+)$',rel,re.M).group(1).strip()
    base='https://deb.debian.org/debian/dists/'+codename+'/main/installer-amd64/current/images/'
    shaurl=base+'SHA256SUMS';sums={}
    for line in texto(shaurl).splitlines():
        fields=line.split()
        if len(fields)==2 and re.fullmatch('[a-fA-F0-9]{64}',fields[0]):sums[base+fields[1].lstrip('./*')]=fields[0].lower()
    kernel=base+'netboot/debian-installer/amd64/linux';initrd=base+'netboot/debian-installer/amd64/initrd.gz'
    return linux('aux-debian-netboot-amd64','debian',ver,kernel,initrd,['initrd=initrd.gz','ip=dhcp'],shaurl,
                 'https://www.debian.org/releases/stable/amd64/ch04s05.en.html',sums)


def fedora():
    root='https://dl.fedoraproject.org/pub/fedora/linux/releases/'
    versions=sorted(set(re.findall(r'href="([0-9]+)/"',texto(root))),key=int,reverse=True)
    if not versions:raise ValueError('No Fedora release directory was found.')
    tree=None
    for ver in versions[:3]:
        base=root+ver+'/Everything/x86_64/os/'
        try:tree=texto(base+'.treeinfo');break
        except OSError:continue
    if tree is None:raise ValueError('No published Fedora installer tree was available.')
    cfg=configparser.ConfigParser(interpolation=None);cfg.read_string(tree);sums={}
    for rel,sha in cfg.items('checksums'):
        if sha.startswith('sha256:'):sums[base+rel]=sha.split(':',1)[1]
    return linux('aux-fedora-netboot-x86_64','fedora',ver,base+'images/pxeboot/vmlinuz',base+'images/pxeboot/initrd.img',
                 ['initrd=initrd.img','ip=dhcp','inst.repo='+base],base+'.treeinfo',
                 'https://docs.fedoraproject.org/en-US/fedora/latest/install-guide/advanced/Network_based_Installations/',sums)


def alpine():
    import yaml
    root='https://dl-cdn.alpinelinux.org/alpine/latest-stable/releases/x86_64/'
    versions=yaml.safe_load(texto(root+'latest-releases.yaml'))
    version=next(str(r['version']) for r in versions if r.get('flavor') in ('netboot','alpine-netboot'))
    branch='v'+'.'.join(version.split('.')[:2]);base='https://dl-cdn.alpinelinux.org/alpine/'+branch+'/releases/x86_64/netboot/'
    kernel=base+'vmlinuz-lts';initrd=base+'initramfs-lts';modloop=base+'modloop-lts';sums={u:sidecar(u+'.sha256') for u in (kernel,initrd,modloop)}
    return linux('aux-alpine-netboot-x86_64','alpine',version,kernel,initrd,
                 ['initrd=initramfs-lts','ip=dhcp','modules=loop,squashfs,sd-mod,usb-storage','alpine_repo=https://dl-cdn.alpinelinux.org/alpine/'+branch+'/main','modloop='+modloop],
                 root+'latest-releases.yaml','https://wiki.alpinelinux.org/wiki/PXE_boot',sums,(modloop,))


RESOLVERS={'aux-debian-netboot-amd64':debian,'aux-fedora-netboot-x86_64':fedora,'aux-alpine-netboot-x86_64':alpine}


def actualiza(cat):
    mapa={e['id']:e for e in cat['entries']};result=[]
    for id,fn in RESOLVERS.items():
        try:
            ent=fn();mapa[id]=ent;result.append({'id':id,'status':'resolved','release':ent['release'],'approved':ent['recipe']['approved']})
        except (OSError,ValueError,KeyError,StopIteration,configparser.Error) as exc:result.append({'id':id,'status':'pending','error':type(exc).__name__+': '+str(exc)[:180]})
    return {**cat,'entries':list(mapa.values())},result


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--catalog',default=str(DIR_APP/'catalog.json'));par.add_argument('--apply',action='store_true');args=par.parse_args(argv)
    cat=carga(args.catalog)
    if not args.apply:print(json.dumps({'own_recipes':list(RESOLVERS),'network':False,'apply_required':True}));return 0
    cat,result=actualiza(cat);guarda(args.catalog,cat);guarda_json(DIR_APP/'config/recipes.resolve.json',{'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':result});print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
