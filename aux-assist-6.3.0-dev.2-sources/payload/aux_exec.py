#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Local proposal broker. The model-facing socket has NO approval operation."""
import argparse
import contextlib
import fcntl
import grp
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import socketserver
import stat
import subprocess
import sys
import time
import unicodedata

DIR_EST = Path('/run/aux-exec/state')
ARC_SOCK = Path('/run/aux-exec/control.sock')
DIR_TRB = Path('/work/managed')
MAX_MSG = 32768
TTL = 600
ACCIONES = ('diagnostic', 'write_file', 'service_state')
DIAG = {'memory': ['/usr/bin/free', '-h'],
        'disks': ['/usr/bin/lsblk', '-o', 'NAME,TYPE,SIZE,RO,FSTYPE'],
        'services': ['/usr/bin/systemctl', '--no-pager', '--failed', '--plain']}
SERVICIOS = ('chronyd.service',)
SCHEMA = {'type': 'object', 'additionalProperties': False,
          'properties': {nom: {'type': 'string'} for nom in
                         ('action', 'target', 'content', 'state', 'reason')},
          'required': ['action', 'target', 'content', 'state', 'reason']}
SCHEMA['properties']['action']['enum'] = list(ACCIONES)


def seguro(txt):
    # Treat every provider string and command output as hostile terminal input.
    return ''.join(c for c in str(txt) if c in '\n\t' or unicodedata.category(c)[0] != 'C')


def digesto(dat):
    return hashlib.sha256(json.dumps(dat, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def valida(dat):
    if not isinstance(dat, dict) or set(dat) != set(SCHEMA['required']):
        raise ValueError('Plan: campos desconocidos o incompletos.')
    if any(not isinstance(v, str) for v in dat.values()):
        raise ValueError('Plan: los campos deben ser texto.')
    if len(json.dumps(dat).encode()) > 16384 or not 1 <= len(dat['reason']) <= 512:
        raise ValueError('Plan demasiado grande o sin motivo.')
    if any(seguro(v) != v for v in dat.values()):
        raise ValueError('Plan con controles de terminal o caracteres invisibles.')
    act, obj = dat['action'], dat['target']
    if act == 'diagnostic':
        if obj not in DIAG or dat['content'] or dat['state']:
            raise ValueError('Diagnóstico no permitido.')
    elif act == 'write_file':
        # A flat, root-only workspace avoids symlink traversal and configuration injection.
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\.txt', obj):
            raise ValueError('Solo nombres simples *.txt en /work/managed.')
        if dat['state'] or len(dat['content'].encode()) > 8192:
            raise ValueError('Archivo: máximo 8192 bytes y state vacío.')
        if re.search(r'(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,}|PRIVATE KEY)', dat['content']):
            raise ValueError('No se admite material que parezca una credencial.')
    elif act == 'service_state':
        if obj not in SERVICIOS or dat['state'] not in ('active', 'inactive') or dat['content']:
            raise ValueError('Solo iniciar/detener chronyd.service; nunca reiniciar ni habilitar.')
    else:
        raise ValueError('Acción bloqueada. No hay shell libre, discos, paquetes ni red en esta fase.')
    return dict(dat)


class Motor:
    def __init__(self, pth_est=DIR_EST, pth_trb=DIR_TRB):
        self.pth_est, self.pth_trb = Path(pth_est), Path(pth_trb)
        self.pth_est.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._privado(self.pth_est)

    @staticmethod
    def _privado(pth):
        inf = pth.lstat()
        if not stat.S_ISDIR(inf.st_mode) or inf.st_uid != os.geteuid() or inf.st_mode & 0o077:
            raise ValueError('Directorio privado inseguro: ' + str(pth))

    @contextlib.contextmanager
    def bloqueo(self):
        fd = os.open(self.pth_est / 'lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as arc:
            fcntl.flock(arc, fcntl.LOCK_EX)
            yield

    def guarda(self, dat):
        pth = self.pth_est / (dat['id'] + '.json')
        tmp = pth.with_suffix('.new')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as arc:
            json.dump(dat, arc, ensure_ascii=True)
            arc.flush()
            os.fsync(arc.fileno())
        os.replace(tmp, pth)

    def lee(self, ide):
        if not isinstance(ide, str) or not re.fullmatch(r'[a-f0-9]{24}', ide):
            raise ValueError('Identificador inválido.')
        dat = json.loads((self.pth_est / (ide + '.json')).read_text())
        if dat['status'] == 'pending' and time.time() > dat['expires']:
            dat['status'] = 'expired'
            self.guarda(dat)
        return dat

    def evento(self, dat):
        # The audit trail deliberately excludes prompts, contents and command output.
        ent = {k: dat[k] for k in ('id', 'status', 'digest', 'owner')}
        ent.update(timestamp=time.time(), action=dat['plan']['action'])
        fd = os.open(self.pth_est / 'audit.jsonl', os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as arc:
            arc.write(json.dumps(ent) + '\n')

    def propone(self, plan, uid):
        plan = valida(plan)
        if len(list(self.pth_est.glob('*.json'))) >= 128:
            raise ValueError('Máximo de 128 propuestas por arranque; revisar antes de continuar.')
        if (self.pth_est / 'revoked').exists():
            raise ValueError('Ejecutor revocado localmente.')
        dat = {'id': secrets.token_hex(12), 'owner': uid, 'plan': plan, 'digest': digesto(plan),
               'created': time.time(), 'expires': time.time() + TTL, 'status': 'pending'}
        self.guarda(dat)
        self.evento(dat)
        return dat

    def listado(self, uid=None):
        return [dat for pth in sorted(self.pth_est.glob('*.json'))
                for dat in [self.lee(pth.stem)] if uid is None or dat['owner'] == uid]

    def atiende(self, req, uid):
        if not isinstance(req, dict) or set(req) - {'op', 'id', 'plan'}:
            raise ValueError('Solicitud inválida.')
        with self.bloqueo():
            if req.get('op') == 'propose':
                return self.propone(req.get('plan'), uid)
            if req.get('op') == 'list':
                return [{'id': dat['id'], 'status': dat['status'],
                         'plan': {k: dat['plan'][k] for k in ('action', 'target')}}
                        for dat in self.listado(uid)]
            if req.get('op') in ('get', 'cancel', 'undo_request'):
                dat = self.lee(req.get('id'))
                if dat['owner'] != uid:
                    raise ValueError('Propuesta ajena.')
                if req['op'] == 'cancel' and dat['status'] == 'pending':
                    dat['status'] = 'cancelled'
                if req['op'] == 'undo_request':
                    if dat['status'] != 'applied' or dat['plan']['action'] == 'diagnostic':
                        raise ValueError('Esta acción no admite deshacer.')
                    dat['undo_requested'] = True
                self.guarda(dat)
                return dat
            # There is intentionally no remote approve/execute/undo endpoint.
            raise ValueError('Operación no autorizada: la aprobación solo existe en la consola local root.')

    def archivo(self, nom):
        if not self.pth_trb.exists() and not self.pth_trb.is_symlink():
            return {'exists': False}
        self._privado(self.pth_trb)
        pth = self.pth_trb / nom
        if not pth.exists() and not pth.is_symlink():
            return {'exists': False}
        fd = os.open(pth, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as arc:
            inf = os.fstat(arc.fileno())
            if not stat.S_ISREG(inf.st_mode) or inf.st_nlink != 1 or inf.st_uid != os.geteuid():
                raise ValueError('Archivo no regular, enlazado o de otro propietario.')
            if inf.st_mode & 0o077:
                raise ValueError('Archivo accesible por otros usuarios; se rechaza.')
            txt = arc.read(8193)
        if len(txt) > 8192:
            raise ValueError('Archivo previo demasiado grande.')
        return {'exists': True, 'text': txt.decode('utf-8'), 'mode': stat.S_IMODE(inf.st_mode)}

    def escribe(self, nom, snap):
        self.pth_trb.mkdir(mode=0o700, exist_ok=True)
        self._privado(self.pth_trb)
        pth = self.pth_trb / nom
        if not snap['exists']:
            pth.unlink(missing_ok=True)
            return
        tmp = self.pth_trb / ('.aux-' + secrets.token_hex(12))
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, snap['mode'])
        try:
            with os.fdopen(fd, 'w') as arc:
                arc.write(snap['text'])
                arc.flush()
                os.fsync(arc.fileno())
            os.replace(tmp, pth)
        finally:
            tmp.unlink(missing_ok=True)

    @staticmethod
    def comando(cmd):
        # Fixed argv, fixed environment and a bounded runtime; never shell=True.
        rsp = subprocess.run(cmd, capture_output=True, timeout=30, check=False,
                             env={'PATH': '/usr/sbin:/usr/bin', 'LANG': 'C.UTF-8',
                                  'SYSTEMD_PAGER': 'cat', 'PAGER': 'cat'}, stdin=subprocess.DEVNULL)
        return rsp.returncode, seguro(rsp.stdout[:4096].decode(errors='replace'))

    def estado_servicio(self, nom):
        cod, txt = self.comando(['/usr/bin/systemctl', 'is-active', nom])
        estado = txt.strip()
        if estado not in ('active', 'inactive'):
            raise ValueError('Servicio no estable (failed/unknown/transitional); intervención manual.')
        return estado

    def prepara(self, dat, undo=False):
        if (self.pth_est / 'revoked').exists():
            raise ValueError('Ejecutor revocado; no se ejecutará ninguna acción.')
        plan = valida(dat['plan'])
        if digesto(plan) != dat['digest']:
            raise ValueError('El plan cambió después de proponerlo.')
        if dat['status'] != ('applied' if undo else 'pending'):
            raise ValueError('Estado incompatible; caducó, ya se consumió o necesita revisión manual.')
        if not undo and time.time() > dat['expires']:
            raise ValueError('Propuesta caducada.')
        if undo and time.time() > dat['created'] + 3600:
            raise ValueError('Ventana de deshacer caducada; revisar manualmente.')
        act, obj = plan['action'], plan['target']
        if act == 'diagnostic':
            if undo:
                raise ValueError('Un diagnóstico no modifica nada y no tiene deshacer.')
            return None
        actual = self.archivo(obj) if act == 'write_file' else self.estado_servicio(obj)
        if undo and actual != dat['after']:
            raise ValueError('El destino cambió después; no se sobrescriben cambios ajenos.')
        return actual

    def aplica(self, ide, digest, undo=False, dry_run=False, precondicion=None):
        with self.bloqueo():
            dat = self.lee(ide)
            if digest != dat['digest']:
                raise ValueError('La confirmación no corresponde al plan mostrado.')
            antes = self.prepara(dat, undo)
            if precondicion is not None and antes != precondicion['current']:
                raise ValueError('El destino cambió durante la confirmación; volver a revisar.')
            if dry_run:
                return {'dry_run': True, 'id': ide, 'plan': dat['plan'], 'current': antes,
                        'note': 'No action executed.'}
            plan = dat['plan']
            dat['status'] = 'undoing' if undo else 'applying'
            if not undo:
                dat['before'] = antes
            self.guarda(dat)
            self.evento(dat)
            try:
                if plan['action'] == 'diagnostic':
                    cod, txt = self.comando(DIAG[plan['target']])
                    if cod:
                        raise ValueError('Diagnóstico falló; código ' + str(cod))
                    dat['result'] = txt
                elif plan['action'] == 'write_file':
                    destino = dat['before'] if undo else {'exists': True, 'text': plan['content'], 'mode': 0o600}
                    self.escribe(plan['target'], destino)
                    dat['after'] = self.archivo(plan['target'])
                    dat['result'] = 'Archivo restaurado.' if undo else 'Archivo escrito en /work/managed.'
                else:
                    destino = dat['before'] if undo else plan['state']
                    if antes != destino:
                        cod, _ = self.comando(['/usr/bin/systemctl', 'start' if destino == 'active' else 'stop', plan['target']])
                        if cod:
                            raise ValueError('Cambio de servicio falló; código ' + str(cod))
                    dat['after'] = self.estado_servicio(plan['target'])
                    if dat['after'] != destino:
                        raise ValueError('No se alcanzó el estado solicitado.')
                    dat['result'] = 'Estado restaurado.' if undo else 'Estado de servicio comprobado.'
                dat['status'] = 'undone' if undo else 'applied'
            except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
                # Partial effects are possible; never claim a failed command was rolled back.
                dat['status'] = 'needs_review'
                dat['result'] = 'Acción interrumpida o fallida; revisar estado y copia previa. ' + type(exc).__name__
            self.guarda(dat)
            self.evento(dat)
            return dat


def cliente(req, pth_sock=ARC_SOCK):
    raw = json.dumps(req).encode() + b'\n'
    if len(raw) > MAX_MSG:
        raise ValueError('Solicitud demasiado grande.')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as cli:
        cli.settimeout(10)
        cli.connect(str(pth_sock))
        cli.sendall(raw)
        with cli.makefile('rb') as arc:
            rsp = arc.readline(256 * 1024 + 1)
    if len(rsp) > 256 * 1024:
        raise ValueError('Respuesta local demasiado grande.')
    dat = json.loads(rsp)
    if 'error' in dat:
        raise ValueError(dat['error'])
    return dat['ok']


def sirve(motor, pth_sock=ARC_SOCK):
    # A restart cancels pending consent; interrupted changes need human review.
    with motor.bloqueo():
        for dat in motor.listado():
            if dat['status'] in ('pending', 'applying', 'undoing'):
                dat['status'] = 'cancelled' if dat['status'] == 'pending' else 'needs_review'
                motor.guarda(dat)
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            try:
                import struct
                _, uid, _ = struct.unpack('3i', self.request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                raw = self.rfile.readline(MAX_MSG + 1)
                if len(raw) > MAX_MSG or not raw.endswith(b'\n'):
                    raise ValueError('Solicitud incompleta o demasiado grande.')
                rsp = {'ok': motor.atiende(json.loads(raw), uid)}
            except (OSError, ValueError, KeyError, TypeError) as exc:
                rsp = {'error': seguro(str(exc))[:256]}
            self.wfile.write(json.dumps(rsp).encode() + b'\n')
    pth_sock = Path(pth_sock)
    if pth_sock.exists():
        raise ValueError('Socket existente; no se reemplaza una instancia activa.')
    with socketserver.UnixStreamServer(str(pth_sock), Handler) as srv:
        os.chown(pth_sock, 0, grp.getgrnam('aux-ai').gr_gid)
        pth_sock.chmod(0o660)
        try:
            srv.serve_forever()
        finally:
            pth_sock.unlink(missing_ok=True)


def revision(motor):
    if os.geteuid() != 0 or not sys.stdin.isatty() or os.ttyname(sys.stdin.fileno()) != '/dev/tty6':
        raise ValueError('Revisión únicamente en la consola física root /dev/tty6 (menú E).')
    print('Ejecutor AUX 6.2 · consola local. No compartir esta terminal con el agente.')
    print('listar | ver ID | aplicar ID | deshacer ID | simular ID | revocar | salir')
    while True:
        tok = input('AUX aprobación> ').split()
        if tok == ['salir']:
            return
        try:
            if tok == ['listar']:
                with motor.bloqueo():
                    for dat in motor.listado():
                        print(dat['id'], dat['status'], dat['plan']['action'], seguro(dat['plan']['target']),
                              'DESHACER SOLICITADO' if dat.get('undo_requested') else '')
                continue
            if tok == ['revocar']:
                with motor.bloqueo():
                    (motor.pth_est / 'revoked').touch(mode=0o600)
                    for dat in motor.listado():
                        if dat['status'] == 'pending':
                            dat['status'] = 'cancelled'
                            motor.guarda(dat)
                print('Nuevas acciones bloqueadas. Detener G/M con I en el menú. No se revierten cambios previos.')
                continue
            if len(tok) != 2 or tok[0] not in ('ver', 'aplicar', 'deshacer', 'simular'):
                print('Usar listar, ver/aplicar/deshacer/simular ID, revocar o salir.')
                continue
            dat = motor.lee(tok[1])
            print(seguro(json.dumps(dat['plan'], indent=2, ensure_ascii=False)))
            print('ID:', dat['id'], '| SHA-256:', dat['digest'], '| estado:', dat['status'])
            if tok[0] == 'ver':
                print('Resultado:', seguro(dat.get('result', '(pendiente)')))
                continue
            if tok[0] == 'simular':
                print(seguro(json.dumps(motor.aplica(dat['id'], dat['digest'], dry_run=True), ensure_ascii=False)))
                continue
            with motor.bloqueo():
                precondicion = {'current': motor.prepara(dat, undo=tok[0] == 'deshacer')}
            print('Estado previo:', seguro(json.dumps(precondicion['current'], ensure_ascii=False)))
            frase = ('DESHACER ' if tok[0] == 'deshacer' else 'APLICAR ') + dat['id'] + ' ' + dat['digest'][:12]
            if input('Escribir exactamente ' + frase + ': ') != frase:
                print('Sin confirmación; nada ejecutado.')
                continue
            rsp = motor.aplica(dat['id'], dat['digest'], undo=tok[0] == 'deshacer', precondicion=precondicion)
            print(rsp['status'], seguro(rsp.get('result', '')))
        except (ValueError, OSError) as exc:
            print(seguro(str(exc)))


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('mode', choices=('serve', 'review'))
    cfg = par.parse_args()
    if os.geteuid() != 0:
        par.error('Solo root; los asistentes usan el socket sin privilegios.')
    os.umask(0o077)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        motor = Motor()
        sirve(motor) if cfg.mode == 'serve' else revision(motor)
    except (EOFError, KeyboardInterrupt):
        return 0
    except (OSError, ValueError) as exc:
        print(seguro(str(exc)), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
