#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Keep a fixed, revocable support authorization on the verified persistent USB."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit
import assist

dur_seg = 8 * 3600


def portatil():
    return 'aux.persist=1' in Path('/proc/cmdline').read_text().split()


def equipo():
    # A USB machine-id travels with the stick, so bind the grant to DMI instead.
    eqp_id = str(uuid.UUID(Path('/sys/class/dmi/id/product_uuid').read_text().strip()))
    if eqp_id in ('00000000-0000-0000-0000-000000000000', 'ffffffff-ffff-ffff-ffff-ffffffffffff'):
        raise ValueError('A stable hardware UUID is required for reboot authorization.')
    return hashlib.sha256(eqp_id.encode()).hexdigest()


def ruta():
    import portable_usb
    uid_usb = portable_usb.verifica()
    pth = portable_usb.fuentes_api(True).parent / 'support'
    portable_usb.directorio_privado(pth, True)
    return uid_usb, pth / 'case.json'


def origen(txt):
    dat = urlsplit(txt)
    if (dat.scheme != 'https' or not dat.hostname or dat.path or dat.query or dat.fragment
            or dat.username or dat.password or not re.fullmatch(r'[\x21-\x7e]{1,1024}', txt)):
        raise ValueError('An HTTPS origin without path or credentials is required.')
    return txt


def nuevo(prov):
    uid_usb, pth_cas = ruta()
    if prov not in ('web', 'direct'):
        raise ValueError('Unknown support case mode.')
    tms_ini = int(time.time())
    if tms_ini < 1704067200:
        raise ValueError('Set the system clock before authorizing restarts.')
    return {'schema': 'aux-support-v1', 'mode': prov, 'usb': uid_usb, 'hardware': equipo(),
            'created': tms_ini, 'expires': tms_ini + dur_seg}


def valida(cas, uid_usb):
    if (not isinstance(cas, dict) or cas.get('schema') != 'aux-support-v1' or
            cas.get('mode') not in ('web', 'direct') or cas.get('usb') != uid_usb or
            cas.get('hardware') != equipo() or not re.fullmatch(r'[a-f0-9]{32}', cas.get('id', '')) or
            not isinstance(cas.get('created'), int) or not isinstance(cas.get('expires'), int) or
            not cas['created'] - 300 <= time.time() < cas['expires'] <= cas['created'] + dur_seg):
        raise ValueError('Support case expired, changed equipment or has an invalid clock.')
    if not isinstance(cas.get('technician'), dict) or not cas['technician'].get('sub'):
        raise ValueError('Support case technician is missing.')
    for nom in ('name', 'contact'):
        assist.texto(cas['technician'][nom])
    assist.valida_clave(cas['key'])
    if cas.get('direct_key'):
        assist.valida_clave(cas['direct_key'])
    if not isinstance(cas.get('host_key'), str) or not 128 <= len(cas['host_key']) <= 8192:
        raise ValueError('Support case host key is missing.')
    if cas['mode'] == 'web':
        origen(cas['url'])
        if not re.fullmatch(r'[A-Za-z0-9_-]{40,64}', cas['token']):
            raise ValueError('Support case capability is invalid.')
    return cas


def guarda(cas):
    import portable_usb
    uid_usb, pth_cas = ruta()
    valida(cas, uid_usb)
    portable_usb.atomic(pth_cas, (json.dumps(cas, ensure_ascii=False) + '\n').encode())


def carga():
    if not portatil():
        return None
    uid_usb, pth_cas = ruta()
    try:
        dat = pth_cas.lstat()
        if (not stat.S_ISREG(dat.st_mode) or dat.st_uid != 0 or dat.st_mode & 0o077
                or dat.st_nlink != 1 or dat.st_size > 32768):
            raise ValueError('Support case storage is not private.')
        return valida(json.loads(pth_cas.read_text()), uid_usb)
    except FileNotFoundError:
        return None
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        borra()
        print('Saved support authorization is unavailable; local approval is required.')
        return None


def borra():
    uid_usb, pth_cas = ruta()
    pth_cas.unlink(missing_ok=True)
    fd = os.open(pth_cas.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


def plazo(cas):
    return datetime.datetime.fromtimestamp(cas['expires'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def huella_clave(clv_pub):
    return subprocess.run(['ssh-keygen', '-lf', '/dev/stdin', '-E', 'sha256'],
                          input=assist.valida_clave(clv_pub), capture_output=True, text=True, check=True).stdout.strip()


def reanuda_directa(cas):
    import agent
    def termina(*_):
        # A machine shutdown preserves the grant; an explicit local close removes it.
        raise SystemExit(0)
    ent = signal.signal(signal.SIGTERM, termina)
    try:
        uid_usb, pth_cas = ruta()
        valida(cas, uid_usb)
        agent.abre_ssh(cas['key'], host_key=cas['host_key'], directo=True)
        assist.estado('DIRECT SSH ACTIVE | ' + cas['technician']['name'] + '\n'
                      'Case: ' + cas['id'] + '\nUntil: ' + plazo(cas) + '\nF6: Enter or Ctrl-C closes the case.\n')
        print('Direct SSH restored on port 4242. Case:', cas['id'])
        print('Authorized until:', plazo(cas), '| F6: Enter or Ctrl-C closes the case.')
        print('Addresses:', ', '.join(assist.red()))
        while time.time() < cas['expires'] and pth_cas.exists():
            if select.select([sys.stdin], [], [], 1)[0]:
                sys.stdin.readline()
                break
        borra()
    except KeyboardInterrupt:
        borra()
    finally:
        signal.signal(signal.SIGTERM, ent)
        subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
        assist.limpia()


def directa(ent):
    import agent
    cas = nuevo('direct')
    clv_pub = assist.valida_clave(ent['clave'])
    print('Technician:', ent['nombre'], '| Contact:', ent['contacto'])
    print('Approved SSH key:', huella_clave(clv_pub))
    print('Root access, including restarts on this equipment, until', plazo(cas))
    if input('Type AUTORIZO to authorize this case: ').strip() != 'AUTORIZO':
        return
    cas.update(id=uuid.uuid4().hex, code='LOCAL', key=clv_pub, direct_key='', url='', token='',
               technician={'sub': 'local:' + hashlib.sha256(clv_pub.encode()).hexdigest(),
                           'name': ent['nombre'], 'contact': ent['contacto']})
    try:
        agent.abre_ssh(clv_pub, directo=True)
        cas['host_key'] = (assist.DIR_RUN / 'host_ed25519').read_text()
        guarda(cas)
    finally:
        subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
        assist.limpia()
    reanuda_directa(cas)


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('action', choices=('status', 'close'))
    cfg = par.parse_args()
    if os.geteuid() != 0:
        raise ValueError('Root local control is required.')
    cas = carga()
    if cfg.action == 'close':
        borra()
        subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
        assist.limpia()
    elif cas:
        print(cas['id'], cas['mode'], cas['technician']['name'], plazo(cas))
    else:
        print('No resumable support case.')


if __name__ == '__main__':
    main()
