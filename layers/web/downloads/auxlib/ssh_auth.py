# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Supply SSH passwords through a private pipe, never argv or environment."""
from contextlib import contextmanager
import copy
import errno
import getpass
import os
from pathlib import Path
import sys
import tempfile
import threading

from . import settings


def oculta(txt, sec):
    for val in (sec or {}).values():
        if isinstance(val,str) and val:txt=txt.replace(val,'[oculto]')
    return txt


def error_ssh(code, stderr, sec=None):
    txt=oculta(stderr or '',sec);low=txt.lower()
    if 'host key verification failed' in low or 'remote host identification has changed' in low:
        motivo='identidad del servidor no validada en known_hosts del usuario actual; verificar la huella con SSH antes de reintentar'
    elif 'permission denied' in low or 'authentication failed' in low:
        motivo='autenticación rechazada; revisar usuario y contraseña SSH en Bastion'
    elif 'resolve hostname' in low:motivo='no se pudo resolver el servidor SSH'
    elif 'connection refused' in low:motivo='conexión rechazada; revisar servidor y puerto SSH'
    elif 'timed out' in low:motivo='tiempo de conexión agotado'
    elif 'rsync: command not found' in low:motivo='el servidor no ofrece rsync; usar el FTP configurado'
    elif 'bad owner or permissions' in low:motivo='SSH rechaza los permisos de su configuración local'
    else:motivo='falló el comando remoto'
    detalle=' '.join(txt.split())[-500:]
    return 'SSH/rsync ('+str(code)+'): '+motivo+('. '+detalle if detalle else '')


@contextmanager
def autenticacion(dat, sec=None, config=None):
    sec=settings.lee_secretos(config=config) if sec is None else sec
    modo=settings.valor(dat,'mirror.ssh_auth','auto')
    clave=sec.get('ssh_password') if modo!='key' else None
    if modo=='password' and not clave and sys.stdin.isatty():
        clave=getpass.getpass('Contraseña SSH / rsync (entrada oculta): ')
    if modo=='password' and not clave:
        raise ValueError('Falta ssh_password: B → Contraseña SSH / rsync, o aux-config secret ssh_password.')
    if clave and any(c in clave for c in ('\0','\r','\n')):raise ValueError('Contraseña SSH inválida.')
    cfg=copy.deepcopy(dat)
    if clave:cfg.setdefault('mirror',{})['ssh_auth']='password'
    from .mirror_transport import ssh_args
    ssh,host=ssh_args(cfg,password_available=bool(clave))
    if not clave:
        yield {'ssh':ssh,'host':host,'run':{},'secrets':sec}
        return
    # A named pipe survives OpenSSH closing extra descriptors before askpass.
    # The helper contains only a pipe path; no password is written to a regular file.
    with tempfile.TemporaryDirectory(prefix='aux-ssh-') as tmp:
        pth=Path(tmp);pipe=pth/'auth.pipe';os.mkfifo(pipe,0o600)
        stop=threading.Event()
        def sirve():
            while not stop.is_set():
                try:fd=os.open(pipe,os.O_WRONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
                except OSError as exc:
                    if exc.errno==errno.ENXIO:stop.wait(.05);continue
                    break
                try:os.write(fd,clave.encode('utf-8')+b'\n')
                except OSError:pass
                finally:os.close(fd)
                stop.wait(.05)
        worker=threading.Thread(target=sirve,daemon=True)
        helper=pth/'askpass'
        helper.write_text('#!'+sys.executable+'\n# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7\n# Author & Credits: https://www.alawise.es/1-s\n'
            'import sys\nwith open('+repr(str(pipe))+',"rb") as f:\n sys.stdout.buffer.write(f.readline())\n')
        helper.chmod(0o700)
        worker.start()
        env={**os.environ,'SSH_ASKPASS':str(helper),'SSH_ASKPASS_REQUIRE':'force'}
        try:yield {'ssh':ssh,'host':host,'run':{'env':env},'secrets':{**sec,'ssh_password':clave}}
        finally:stop.set();worker.join(timeout=1)


def prueba(dat, sec=None, config=None):
    import subprocess
    with autenticacion(dat,sec,config) as auth:
        result=subprocess.run(auth['ssh']+[auth['host'],'printf AUX_SSH_OK'],capture_output=True,text=True,timeout=30,**auth['run'])
        if result.returncode:raise ValueError(error_ssh(result.returncode,result.stderr,auth['secrets']))
        if result.stdout!='AUX_SSH_OK':raise ValueError('SSH respondió, pero no confirmó el comando de prueba.')
    return ['SSH: autenticación y comando de lectura correctos.']
