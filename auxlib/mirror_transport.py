# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Resumable physical transfers and complete remote SHA-256 verification."""
import ftplib
import hashlib
import json
import os
from pathlib import Path
import shlex
import ssl
import subprocess

from . import settings as cfg
from .mirror_inventory import comprueba_local, ruta_rel, valida_vista

# The fixed remote program only reads expected regular files beneath the site root.
VERIFICA = r'''
import hashlib,json,pathlib,stat,sys
d=json.load(sys.stdin);root=pathlib.Path(d['root']).resolve(strict=True);bad=[];count=0
for e in d['files']:
 try:
  rel=pathlib.PurePosixPath(e['relative'])
  if rel.is_absolute() or '..' in rel.parts:raise ValueError('unsafe path')
  p=root.joinpath(*rel.parts)
  if not p.resolve().is_relative_to(root) or any(a.is_symlink() for a in [p,*list(p.parents)[:len(rel.parts)-1]]):raise ValueError('symlink')
  if not stat.S_ISREG(p.stat().st_mode) or p.stat().st_size!=e['size']:raise ValueError('size')
  sha=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(1048576),b''):sha.update(b)
  if sha.hexdigest()!=e['sha256']:raise ValueError('sha256')
  count+=1
 except (OSError,ValueError) as err:bad.append({'relative':e['relative'],'error':str(err)})
print(json.dumps({'checked':count,'expected':len(d['files']),'failures':bad}))
'''


def ssh_args(dat):
    vals = [cfg.convierte(n,str(cfg.valor(dat,n,''))) for n in ('mirror.ssh_host','mirror.ssh_user')]
    puerto = cfg.convierte('mirror.ssh_port',str(cfg.valor(dat,'mirror.ssh_port',22)))
    args = ['ssh','-p',str(puerto),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes']
    ident = cfg.valor(dat,'mirror.ssh_identity')
    if ident: args += ['-i',str(Path(ident).expanduser())]
    return args, vals[1]+'@'+vals[0]


def raiz_remota(dat):
    nom = 'mirror.remote_root' if cfg.valor(dat,'mirror.transport','rsync') == 'rsync' else 'ftp_root'
    if nom=='ftp_root' and cfg.valor(dat,nom)=='/':return '/'
    return cfg.convierte(nom,str(cfg.valor(dat,nom,'')))


def comando_rsync(dat, pth_vista):
    ssh, host = ssh_args(dat)
    remoto = raiz_remota(dat)
    return ['rsync','-rtpL','--protect-args','--checksum','--partial','--partial-dir=.aux-rsync-partial',
            '--chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r','--itemize-changes','-e',shlex.join(ssh),
            str(Path(pth_vista))+'/',host+':'+remoto.rstrip('/')+'/']


def conecta_ftp(dat, sec):
    if dat.get('ftp_tls',True) is not True: raise ValueError('La réplica requiere FTPS con certificado válido.')
    host = cfg.convierte('ftp_host',str(dat.get('ftp_host') or ''))
    usr = cfg.convierte('ftp_user',str(dat.get('ftp_user') or ''))
    clave = sec.get('ftp_password') or os.environ.get('AUX_FTP_PASSWORD')
    if not clave: raise ValueError('Falta ftp_password en el almacén privado.')
    conn = ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=60)
    try:
        conn.connect(host,cfg.convierte('ftp_port',str(dat.get('ftp_port',21))))
        conn.login(usr,clave); conn.prot_p(); conn.set_pasv(True)
        conn.cwd(raiz_remota(dat)); conn.voidcmd('TYPE I')
        return conn
    except Exception:
        conn.close()
        raise ValueError('No se pudo abrir FTPS; revisar host, certificado, usuario y raíz.') from None


def tam_ftp(conn, nom):
    try: return conn.size(nom)
    except ftplib.error_perm as err:
        if str(err).startswith('550'): return None
        raise


def cambia_dir(conn, raiz, rel, crear=False):
    conn.cwd(raiz)
    for nom in ruta_rel(rel).split('/')[:-1]:
        try: conn.cwd(nom)
        except ftplib.error_perm:
            if not crear: raise
            conn.mkd(nom); conn.cwd(nom)
    conn.voidcmd('TYPE I')


def envia(dat, items, pth_vista, sec):
    comprueba_local(items)
    valida_vista(items,pth_vista)
    if cfg.valor(dat,'mirror.transport','rsync') == 'rsync':
        subprocess.run(comando_rsync(dat,pth_vista),check=True)
    else:
        conn = conecta_ftp(dat,sec)
        raiz = raiz_remota(dat)
        try:
            for idx,ent in enumerate(items,1):
                cambia_dir(conn,raiz,ent['relative'],crear=True)
                tmp = '.aux-upload-'+ent['sha256']+'.part'
                pos = tam_ftp(conn,tmp) or 0
                if pos > ent['size']: raise ValueError('Parcial remoto mayor que INPUT: '+ent['relative'])
                print(f"FTPS {idx}/{len(items)} {ent['relative']} | {pos}/{ent['size']}",flush=True)
                if pos < ent['size'] or ent['size'] == 0:
                    with open(ent['source'],'rb') as arc:
                        arc.seek(pos)
                        conn.storbinary('STOR '+tmp,arc,blocksize=262144,rest=pos or None)
                if tam_ftp(conn,tmp) != ent['size']: raise ValueError('Transferencia incompleta: '+ent['relative'])
                comprueba_local([ent])
                conn.rename(tmp,Path(ent['relative']).name)
        except ftplib.all_errors:
            raise ValueError('FTPS interrumpido; la siguiente ejecución reanuda los parciales.') from None
        finally: conn.close()
    comprueba_local(items)


def verifica(dat, items, sec):
    if cfg.valor(dat,'mirror.transport','rsync') == 'rsync':
        ssh, host = ssh_args(dat)
        req = {'root':raiz_remota(dat),'files':[{k:e[k] for k in ('relative','size','sha256')} for e in items]}
        ret = subprocess.run(ssh+[host,shlex.join(['python3','-c',VERIFICA])],
                             input=json.dumps(req),text=True,capture_output=True,check=True)
        dat = json.loads(ret.stdout)
        if dat.get('expected') != len(items) or not isinstance(dat.get('failures'),list) or not isinstance(dat.get('checked'),int):
            raise ValueError('Respuesta de verificación SSH inválida.')
        return dat
    conn = conecta_ftp(dat,sec)
    fallos, cant = [], 0
    try:
        for ent in items:
            try:
                cambia_dir(conn,raiz_remota(dat),ent['relative'])
                if tam_ftp(conn,Path(ent['relative']).name) != ent['size']: raise ValueError('size')
                sha = hashlib.sha256()
                conn.retrbinary('RETR '+Path(ent['relative']).name,sha.update,blocksize=1048576)
                if sha.hexdigest() != ent['sha256']: raise ValueError('sha256')
                cant += 1
            except (ValueError,ftplib.error_perm) as err:
                fallos.append({'relative':ent['relative'],'error':str(err)})
    finally: conn.close()
    return {'checked':cant,'expected':len(items),'failures':fallos}
