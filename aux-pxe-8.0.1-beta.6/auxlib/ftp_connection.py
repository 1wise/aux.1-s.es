# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
# Author & Credits: https://www.alawise.es/1-s
"""Report FTP failures by connection phase and expose the actual login directory."""
import ftplib
import os
import ssl

from .settings import convierte
from .ssh_auth import oculta


def abre(dat, sec, raiz=None, timeout=60, exige_tls=False):
    tls=dat.get('ftp_tls',True)
    if exige_tls and tls is not True:raise ValueError('La réplica requiere FTPS con certificado válido.')
    host=convierte('ftp_host',str(dat.get('ftp_host') or ''))
    usr=convierte('ftp_user',str(dat.get('ftp_user') or ''))
    clave=sec.get('ftp_password') or os.environ.get('AUX_FTP_PASSWORD')
    if not clave:raise ValueError('FTP: falta ftp_password en el almacén privado del usuario actual; B → Contraseña FTP.')
    conn=ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=timeout) if tls else ftplib.FTP(timeout=timeout)
    fase='conexión';pwd=None
    try:
        conn.connect(host,convierte('ftp_port',str(dat.get('ftp_port',21))))
        if tls:fase='TLS';conn.auth()
        fase='login';conn.login(usr,clave)
        if tls:fase='protección de datos';conn.prot_p()
        conn.set_pasv(True)
        fase='PWD';pwd=conn.pwd()
        if raiz is not None:fase='directorio';conn.cwd(raiz)
        fase='modo binario';conn.voidcmd('TYPE I')
        return conn
    except (OSError,EOFError,ftplib.Error,ValueError) as exc:
        conn.close();detalle=' '.join(oculta(str(exc),{**sec,'ftp_password':clave}).split())[:400]
        mensaje=('FTPS' if tls else 'FTP')+' ['+fase+']: '+detalle
        if fase=='directorio':mensaje+='; raíz solicitada '+str(raiz)+'; PWD tras login '+str(pwd)+'. Usar B → Explorar FTP para elegir una ruta visible por FTP.'
        raise ValueError(mensaje) from None


def listado(conn):
    try:return list(conn.mlsd(facts=['type','size']))
    except ftplib.error_perm as exc:
        if not str(exc).startswith(('500','501','502','504')):raise
    raiz=conn.pwd();sal=[]
    for valor in conn.nlst():
        nombre=valor.rstrip('/').rsplit('/',1)[-1]
        if nombre in ('','.','..'):continue
        try:conn.cwd(nombre);tipo='dir';conn.cwd(raiz)
        except ftplib.error_perm:tipo='file'
        sal.append((nombre,{'type':tipo}))
    return sal


def prueba(dat, sec):
    conn=abre(dat,sec)
    try:
        pwd=conn.pwd();items=listado(conn)
        result={'login_directory':pwd,'directories':[n for n,f in items if f.get('type')=='dir' and not n.startswith('.')],
                'requested_root':dat.get('ftp_root','/'),'root_status':'ok'}
        try:conn.cwd(result['requested_root'])
        except ftplib.all_errors as exc:result.update(root_status='error',root_error=oculta(str(exc),sec))
        return result
    except ftplib.all_errors as exc:raise ValueError('FTP [listado]: '+oculta(str(exc),sec)+'; revisar modo pasivo y conexión de datos.') from None
    finally:conn.close()
