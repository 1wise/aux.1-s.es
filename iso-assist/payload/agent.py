#!/usr/bin/python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Create an outgoing TLS session only on request, then await local root consent."""
import asyncio
import argparse
import contextlib
import json
from pathlib import Path
import subprocess
import signal
import sys
import time
from urllib.parse import urlsplit
import aiohttp
import assist
import support_case


async def pregunta(txt):
    # A removable stdin reader avoids an executor thread surviving tunnel revocation.
    print(txt, end='', flush=True)
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    def read():
        if not future.done():
            future.set_result(sys.stdin.readline().strip())
    loop.add_reader(sys.stdin.fileno(), read)
    try:
        return await future
    finally:
        loop.remove_reader(sys.stdin.fileno())


def abre_ssh(key, direct_key='', host_key=None, directo=False):
    pth = assist.DIR_RUN
    pth.mkdir(mode=0o700, exist_ok=True)
    assist.etiqueta(pth, 'var_run_t')
    arc = pth / 'authorized_keys'
    arc.write_text(assist.valida_clave(key) + (assist.valida_clave(direct_key) if direct_key else ''));arc.chmod(0o600)
    assist.etiqueta(arc, 'ssh_home_t')
    if host_key:
        (pth / 'host_ed25519').write_text(host_key);(pth / 'host_ed25519').chmod(0o600)
        dat = assist.ejecuta(['ssh-keygen', '-y', '-f', str(pth / 'host_ed25519')], capture_output=True, text=True)
        (pth / 'host_ed25519.pub').write_text(dat.stdout)
    else:
        assist.ejecuta(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(pth / 'host_ed25519')])
    for nom in ('host_ed25519', 'host_ed25519.pub'):
        assist.etiqueta(pth / nom, 'sshd_key_t')
    assist.ejecuta(['tmux', '-S', str(assist.SOC_TMX), 'new-session', '-d', '-s', 'assist',
                   '-c', '/work', '/bin/bash --noprofile --norc'])
    cfg = assist.configura_ssh()
    if not directo and not direct_key:
        cfg = cfg.replace('ListenAddress 0.0.0.0\nListenAddress ::', 'ListenAddress 127.0.0.1')
    arc = pth / 'sshd.conf';arc.write_text(cfg);arc.chmod(0o600)
    assist.etiqueta(arc, 'etc_t')
    assist.ejecuta(['/usr/bin/sshd', '-t', '-f', str(arc)])
    assist.ejecuta(['systemctl', 'start', 'aux-assist-sshd.service'])
    return (pth / 'host_ed25519.pub').read_text()


async def revoca(cas):
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5), trust_env=False) as client:
            async with client.post(cas['url'] + '/api/sessions/' + cas['id'] + '/agent-close',
                                   headers={'Authorization': 'Bearer ' + cas['token']}, allow_redirects=False):
                pass
    except (aiohttp.ClientError, OSError, asyncio.TimeoutError):
        pass


async def run(url, cas=None):
    support_case.origen(url)
    if not cas:
        print('Solicitud web: el cli verá la IP pública y un identificador temporal.')
        if await pregunta('Escribir SOLICITO para contactar con el cli: ') != 'SOLICITO':
            return
    timeout = aiohttp.ClientTimeout(total=20)
    cnt_rtt = 1
    async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
        if cas:
            ses = {'id': cas['id'], 'token': cas['token'], 'code': cas['code']}
        else:
            async with client.post(url + '/api/sessions', allow_redirects=False) as rsp:
                rsp.raise_for_status();ses = await rsp.json()
        print('Solicitud:', ses['code'], '| CLI:', url)
        print('Ctrl-C cancela el caso y cierra SSH. Un reinicio conserva un permiso vigente.')
        while True:
            reader = writer = task = refresh = None
            ssh_started = False
            try:
                ws_url = url.replace('https://', 'wss://', 1) + '/agent/' + ses['id']
                async with client.ws_connect(ws_url, headers={'Authorization': 'Bearer ' + ses['token']},
                    heartbeat=15, max_msg_size=65536, compress=0) as ws:
                    async def upload():
                        while chunk := await reader.read(32768):
                            await ws.send_bytes(chunk)
                        await ws.close()

                    async def vigila():
                        nonlocal cas
                        while True:
                            await asyncio.sleep(1)
                            if cas:
                                try:
                                    uid_usb, pth_cas = support_case.ruta()
                                    res = time.time() < cas['expires'] and pth_cas.exists()
                                except (OSError, ValueError, subprocess.SubprocessError):
                                    res = False
                                if not res:
                                    subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
                                    with contextlib.suppress(OSError, ValueError, subprocess.SubprocessError):
                                        support_case.borra()
                                    cas = None
                                    await ws.send_json({'type': 'revoke'})
                                    await ws.close()
                                    return

                    refresh = asyncio.create_task(vigila())
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            dat = json.loads(msg.data)
                            if dat['type'] in ('offer', 'resume'):
                                if ssh_started:
                                    raise ValueError('Unexpected second authorization.')
                                tech = dat['technician']
                                key = assist.valida_clave(dat['key'])
                                clv_dir = assist.valida_clave(dat['direct_key']) if dat.get('direct_key') else ''
                                if dat['type'] == 'resume':
                                    if (not cas or tech['sub'] != cas['technician']['sub'] or
                                            key != cas['key'] or clv_dir != cas.get('direct_key', '') or
                                            int(dat['expires']) != cas['expires']):
                                        raise ValueError('Support case authorization changed.')
                                    uid_usb, pth_cas = support_case.ruta()
                                    support_case.valida(cas, uid_usb)
                                    ssh_started = True
                                    host_key = abre_ssh(key, clv_dir, cas['host_key'])
                                else:
                                    if cas:
                                        raise ValueError('A new offer cannot replace a saved case.')
                                    print('Technician:', assist.texto(tech['name']))
                                    print('Contact:', assist.texto(tech['contact']))
                                    print('Web SSH key:', support_case.huella_clave(key))
                                    cas_rec = None
                                    if support_case.portatil():
                                        cas_rec = support_case.nuevo('web')
                                        print('Root assistance including restarts until', support_case.plazo(cas_rec))
                                        print('The technician case register will receive this USB UUID and a hashed computer identity.')
                                        if clv_dir:
                                            print('Also direct SSH on port 4242:', support_case.huella_clave(clv_dir))
                                    else:
                                        # The generic Live still grants access only for this boot.
                                        clv_dir = ''
                                    if await pregunta('Escribir AUTORIZO para abrir la asistencia: ') != 'AUTORIZO':
                                        await ws.send_json({'type': 'revoke'});return
                                    ssh_started = True
                                    host_key = abre_ssh(key, clv_dir)
                                    if cas_rec:
                                        cas_rec.update(id=ses['id'], code=ses['code'], url=url, token=ses['token'],
                                            technician=tech, key=key, direct_key=clv_dir,
                                            host_key=(assist.DIR_RUN / 'host_ed25519').read_text())
                                        support_case.guarda(cas_rec)
                                        cas = cas_rec
                                ssh_started = True
                                await ws.send_json({'type': 'ready', 'host_key': host_key,
                                    'resume': bool(cas), 'expires': cas['expires'] if cas else 0,
                                    'device': {'usb_uuid': cas['usb'], 'hardware_id': cas['hardware']} if cas else {}})
                                assist.estado('WEB ASSISTANCE AUTHORIZED | ' + tech['name'] + '\n' + ses['code'] +
                                    ('\nUntil: ' + support_case.plazo(cas) if cas else '') + '\nF6: Ctrl-C closes the case.\n')
                            elif dat['type'] == 'authorized' and cas:
                                if int(dat['expires']) != cas['expires']:
                                    raise ValueError('Case deadline changed.')
                                cnt_rtt = 1
                                print('Case ready:', ses['code'], '| Until:', support_case.plazo(cas))
                            elif dat['type'] == 'open' and ssh_started and writer is None:
                                reader, writer = await asyncio.open_connection('127.0.0.1', assist.PORT_SSH)
                                task = asyncio.create_task(upload())
                            elif dat['type'] == 'closed':
                                if not dat.get('resume'):
                                    if cas:support_case.borra()
                                    cas = None
                                break
                            else:
                                raise ValueError('Unexpected gateway state.')
                        elif msg.type == aiohttp.WSMsgType.BINARY and writer:
                            writer.write(msg.data);await writer.drain()
                        else:
                            break
            except aiohttp.ClientResponseError as exc:
                if exc.status in (401, 403, 404):
                    if cas:support_case.borra()
                    print('Support case closed or unavailable.')
                    return
                if not cas:raise
            except (aiohttp.ClientError, OSError, asyncio.TimeoutError):
                if not cas:raise
            except (ValueError, KeyError, TypeError):
                if cas:
                    support_case.borra()
                    await revoca(cas)
                raise
            finally:
                for dat in (task, refresh):
                    if dat:
                        dat.cancel()
                        with contextlib.suppress(asyncio.CancelledError, ConnectionError):
                            await dat
                if writer:
                    writer.close()
                    with contextlib.suppress(ConnectionError):
                        await writer.wait_closed()
                if ssh_started:
                    subprocess.run(['systemctl', 'stop', 'aux-assist-sshd.service'], check=False)
                assist.limpia()
            if not cas:
                return
            if time.time() >= cas['expires'] or not support_case.carga():
                support_case.borra()
                await revoca(cas)
                return
            assist.estado('RECONNECTING | ' + ses['code'] + '\nUntil: ' + support_case.plazo(cas) + '\n')
            print('Reconnecting the same case in', cnt_rtt, 'seconds. Ctrl-C cancels.')
            await asyncio.sleep(cnt_rtt)
            cnt_rtt = min(30, cnt_rtt * 2)


def main():
    par = argparse.ArgumentParser(description=__doc__)
    par.add_argument('--resume', action='store_true')
    cfg = par.parse_args()
    cas = support_case.carga() if cfg.resume else None
    if cfg.resume and not cas:
        return
    def termina(*_):
        # SIGTERM from shutdown must not turn a transport loss into case revocation.
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, termina)
    try:
        if cas:
            asyncio.run(run(cas['url'], cas))
            return
        cfg = json.loads((Path(__file__).parent / 'cli.json').read_text())
        nodes = list(cfg['nodes'].items())
        for idx, (name, ent) in enumerate(nodes, 1):
            print(str(idx) + '. ' + name + ' | ' + ent['url'])
        num = input('CLI [1]: ').strip() or '1'
        if not num.isdigit() or not 1 <= int(num) <= len(nodes):
            raise ValueError('CLI inválido.')
        asyncio.run(run(nodes[int(num) - 1][1]['url']))
    except KeyboardInterrupt:
        cas = support_case.carga()
        if cas:
            support_case.borra()
            asyncio.run(revoca(cas))
        print('\nSupport case cancelled.')


if __name__ == '__main__':
    main()
