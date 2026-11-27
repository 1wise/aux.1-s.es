# Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
# Author & Credits: https://www.alawise.es/1-s
"""Record bounded HTTP observations separately from integrity and boot evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime
import hashlib
import ipaddress
from pathlib import Path
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import json
from .catalog_v8 import carga,url_publica
from .common import guarda_json
SCHEMA='aux-url-audit-v1'
TRUSTED_SUFFIXES=('debian.org','fedoraproject.org','alpinelinux.org','gentoo.org','ubuntu.com','kernel.org','archlinux.org','netboot.xyz','github.com','githubusercontent.com','centos.org','almalinux.org','rockylinux.org','opensuse.org','sourceforge.net','ibiblio.org','memtest.org','supergrubdisk.org','system-rescue.org','systemrescue.org')


def ahora():return datetime.datetime.now(datetime.timezone.utc).isoformat()


def publica(url):
    url_publica(url);part=urllib.parse.urlsplit(url)
    if part.port not in (None,80,443):raise ValueError('Only public HTTP/HTTPS ports are audited.')
    try:addresses=socket.getaddrinfo(part.hostname,part.port or (443 if part.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except socket.gaierror:
        # Managed HTTPS proxies resolve publisher DNS remotely; unknown hosts stay unverified.
        if part.scheme=='https' and any(part.hostname==s or part.hostname.endswith('.'+s) for s in TRUSTED_SUFFIXES):return url
        raise
    for ent in addresses:
        if not ipaddress.ip_address(ent[4][0]).is_global:raise ValueError('Private and local addresses are excluded.')
    return url


class Redireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        publica(newurl)
        if req.full_url.startswith('https://') and not newurl.startswith('https://'):raise ValueError('HTTPS downgrade refused.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def comprueba(ent,timeout=12,cliente=None):
    url=ent['original_url'];start=time.monotonic()
    row={'id':ent['id'],'original_url':url,'url_sha256':hashlib.sha256(url.encode()).hexdigest(),'checked_at':ahora(),
         'status':'unknown','verified':False,'boot_test':'not-tested','integrity':'not-checked'}
    try:
        publica(url);abr=cliente or urllib.request.build_opener(Redireccion())
        req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'AUX-Catalog-Audit/8.0 (+https://www.alawise.es/1-s)'})
        try:rsp=abr.open(req,timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in (405,501):raise
            req=urllib.request.Request(url,headers={'Range':'bytes=0-511','User-Agent':'AUX-Catalog-Audit/8.0'})
            rsp=abr.open(req,timeout=timeout)
        with rsp:
            publica(rsp.url);row.update(http_status=rsp.status,final_url=rsp.url,content_type=rsp.headers.get('Content-Type',''),etag=rsp.headers.get('ETag'))
            tam=rsp.headers.get('Content-Length')
            if rsp.headers.get('Content-Range'):tam=rsp.headers['Content-Range'].rsplit('/',1)[-1]
            if tam and tam.isdigit():row['size_bytes']=int(tam)
            if req.get_method()!='HEAD':rsp.read(512)
        if row['http_status'] not in (200,206):row['status']='http-error'
        elif 'text/html' in row['content_type'].lower() and ent.get('artifact_type') not in ('menu','manifest') and not ent.get('remote_only'):row['status']='unexpected-html'
        elif ent.get('size_bytes') and row.get('size_bytes') and ent['size_bytes']!=row['size_bytes']:row['status']='metadata-mismatch'
        else:row.update(status='reachable',verified=True)
    except urllib.error.HTTPError as exc:
        row.update(http_status=exc.code,status='missing' if exc.code in (404,410) else 'temporarily-unavailable' if exc.code>=500 else 'access-unconfirmed')
    except (OSError,ValueError,urllib.error.URLError) as exc:row.update(status='unknown',error=type(exc).__name__+': '+str(exc)[:180])
    row['elapsed_ms']=round((time.monotonic()-start)*1000);return row


def audita(cat,jobs=6,timeout=12):
    if not 1<=jobs<=16 or not 1<=timeout<=60:raise ValueError('Invalid audit limits.')
    sems={};lock=threading.Lock()
    def run(ent):
        with lock:sem=sems.setdefault(urllib.parse.urlsplit(ent['original_url']).hostname,threading.Semaphore(2))
        with sem:return comprueba(ent,timeout)
    with ThreadPoolExecutor(max_workers=jobs) as exe:rows=list(exe.map(run,cat['entries']))
    good=sum(e['verified'] for e in rows);date=ahora()
    return {'schema':SCHEMA,'checked_at':date,'next_due':(datetime.datetime.fromisoformat(date)+datetime.timedelta(days=7)).isoformat(),
            'cadence':'weekly','method':'HTTP HEAD; bounded GET fallback','scope':'URL and declared size; no artifact hashing or boot acceptance',
            'summary':{'total':len(rows),'verified':good,'needs_review':len(rows)-good},'entries':rows}


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--catalog');par.add_argument('--config');par.add_argument('--output',type=Path,default=Path('config/catalog.audit.json'))
    par.add_argument('--jobs',type=int,default=6);par.add_argument('--timeout',type=int,default=12);par.add_argument('--apply',action='store_true')
    args=par.parse_args(argv);cat=carga(args.catalog,args.config)
    if not args.apply:print(json.dumps({'operation':'catalog-audit','resources':len(cat['entries']),'output':str(args.output),'network':False,'apply_required':True}));return 0
    dat=audita(cat,args.jobs,args.timeout);guarda_json(args.output,dat);print(json.dumps(dat['summary']));return 0


if __name__=='__main__':raise SystemExit(main())
