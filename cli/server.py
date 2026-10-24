#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Consent-bound SSH over an outbound WSS stream. No public SSH forwarding port."""
import asyncio
import base64
import contextlib
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import sqlite3
import tempfile
import time
import uuid

import aiohttp
from aiohttp import web
import asyncssh
from history import History

LOG = logging.getLogger('aux.cli')
VERSION = '6.3.0-dev.2'


def b64url(dat):
    return base64.urlsafe_b64encode(dat).rstrip(b'=').decode('ascii')


def firma(claims, secret):
    payload = b64url(json.dumps(claims, separators=(',', ':')).encode())
    return payload + '.' + b64url(hmac.digest(secret, payload.encode(), 'sha256'))


class Tickets:
    def __init__(self, secret, node):
        self.secret, self.node, self.used = secret, node, {}

    def consume(self, token, scope):
        try:
            if not isinstance(token, str) or len(token) > 8192:
                raise ValueError()
            payload, sig = token.split('.')
            expected = b64url(hmac.digest(self.secret, payload.encode(), 'sha256'))
            if not hmac.compare_digest(sig, expected):
                raise ValueError()
            dat = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
            now = time.time()
            if (dat['aud'] != self.node or dat['scope'] != scope or not dat['sub'] or
                    not now - 5 <= dat['exp'] <= now + 65 or len(dat['nonce']) < 32):
                raise ValueError()
            self.used = {key: exp for key, exp in self.used.items() if exp > now}
            if dat['nonce'] in self.used or len(self.used) >= 10000:
                raise ValueError()
            self.used[dat['nonce']] = dat['exp']
            return dat
        except (ValueError, KeyError, TypeError, UnicodeError):
            raise web.HTTPUnauthorized(text='Invalid, expired or replayed authorization') from None


@dataclass
class Session:
    id: str
    code: str
    token_hash: str
    created: float
    expires: float
    state: str = 'pending'
    tech: dict | None = None
    key: object = None
    host_key: object = None
    agent: object = None
    browser: object = None
    bridge: object = None
    ssh: object = None
    process: object = None
    terminal_task: object = None
    closing: bool = False
    res: bool = False
    susp: bool = False
    uid_usb: str = ''
    eqp_id: str = ''
    tty_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def public(self):
        return {'id': self.id, 'code': self.code, 'state': self.state,
                'created': int(self.created), 'expires': int(self.expires),
                'technician': self.tech['name'] if self.tech else None, 'resume': self.res,
                'device': {'usb_uuid': self.uid_usb, 'hardware_id': self.eqp_id}}


class CLI:
    def __init__(self, secret, node='excalibur', origins=(), max_sessions=64, pth_est=None):
        self.tickets = Tickets(secret, node)
        self.node, self.origins = node, set(origins)
        self.sessions, self.rates = {}, {}
        self.max_sessions = max_sessions
        self.auth_lease = 75
        self.pth_est = Path(pth_est) if pth_est else None
        self.history = None
        if self.pth_est:
            self.pth_est.mkdir(mode=0o700, parents=True, exist_ok=True)
            dat = self.pth_est.lstat()
            if not stat.S_ISDIR(dat.st_mode) or dat.st_uid != os.geteuid() or dat.st_mode & 0o077:
                raise ValueError('Private case directory requires owner-only access')
        self.history = History(self.pth_est.parent / 'history.sqlite3' if self.pth_est else None)
        if self.pth_est:
            self.carga_casos()

    def registra(self, ses, nom_evt, reason=''):
        if ses.tech:
            try:
                self.history.append(ses.tech['sub'], {'node': self.node, 'event': nom_evt,
                    'at': int(time.time()), 'reason': reason, 'session': ses.public()})
            except (sqlite3.Error, OSError):
                # A full audit disk must never prevent closing an SSH authorization.
                self.history.failed = True
                LOG.exception('history_write_failed session=%s event=%s', ses.code, nom_evt)

    async def history_listing(self, req):
        tec = self.ticket(req, 'control')
        if self.history.failed:
            raise web.HTTPServiceUnavailable(text='History incomplete; review gateway logs')
        cur_evt = req.query.get('cursor', '0')
        if not re.fullmatch(r'[0-9]{1,18}', cur_evt):
            raise web.HTTPBadRequest(text='Invalid history cursor')
        return web.json_response({'node': self.node, **self.history.read(tec['sub'], int(cur_evt))})

    def carga_casos(self):
        for arc in self.pth_est.glob('*.json'):
            try:
                dat = arc.lstat()
                if (not re.fullmatch(r'[a-f0-9]{32}\.json', arc.name) or not stat.S_ISREG(dat.st_mode)
                        or dat.st_uid != os.geteuid() or dat.st_mode & 0o077 or dat.st_size > 32768):
                    raise ValueError()
                cas_rec = json.loads(arc.read_text())
                if (cas_rec['node'] != self.node or cas_rec['id'] != arc.stem or
                        not re.fullmatch(r'[a-f0-9]{64}', cas_rec['token_hash']) or
                        not time.time() < cas_rec['expires'] <= cas_rec['created'] + 29400 or
                        not cas_rec['tech']['sub']):
                    raise ValueError()
                ses = Session(cas_rec['id'], cas_rec['code'], cas_rec['token_hash'],
                              cas_rec['created'], cas_rec['expires'], state='reconnecting',
                              tech=cas_rec['tech'], key=asyncssh.import_private_key(cas_rec['key']), res=True)
                ses.uid_usb = cas_rec.get('device', {}).get('usb_uuid', '')
                ses.eqp_id = cas_rec.get('device', {}).get('hardware_id', '')
                if len(self.sessions) >= self.max_sessions:
                    break
                self.sessions[ses.id] = ses
                self.registra(ses, 'gateway_restarted')
            except (OSError, ValueError, KeyError, TypeError, asyncssh.Error):
                LOG.warning('discarded unavailable stored case file=%s', arc.name)
                arc.unlink(missing_ok=True)

    def guarda_caso(self, ses):
        if not self.pth_est:
            return
        cas_rec = {'node': self.node, 'id': ses.id, 'code': ses.code, 'token_hash': ses.token_hash,
                   'created': ses.created, 'expires': ses.expires, 'tech': ses.tech,
                   'key': ses.key.export_private_key().decode(), 'device': ses.public()['device']}
        fd, nom = tempfile.mkstemp(prefix='.case-', dir=self.pth_est)
        try:
            with os.fdopen(fd, 'w') as arc:
                json.dump(cas_rec, arc);arc.flush();os.fsync(arc.fileno())
            os.replace(nom, self.pth_est / (ses.id + '.json'))
            self.sincroniza_casos()
        finally:
            Path(nom).unlink(missing_ok=True)

    def sincroniza_casos(self):
        if self.pth_est:
            fd = os.open(self.pth_est, os.O_RDONLY | os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)

    def oferta(self, ses, res=False):
        return {'type': 'resume' if res else 'offer', 'technician': ses.tech,
                'key': ses.key.export_public_key().decode(), 'fingerprint': ses.key.get_fingerprint(),
                'direct_key': ses.tech.get('direct_key', ''), 'expires': int(ses.expires)}

    def by_token(self, id_ses, token):
        ses = self.sessions.get(id_ses)
        if not ses or ses.expires <= time.time() or ses.closing or not hmac.compare_digest(
                ses.token_hash, hashlib.sha256(token.encode()).hexdigest()):
            raise web.HTTPUnauthorized(text='Session unavailable')
        if ses.susp:
            raise web.HTTPConflict(text='Previous transport is closing; retry shortly')
        return ses

    def ticket(self, req, scope):
        val = req.headers.get('Authorization', '')
        return self.tickets.consume(val.removeprefix('Bearer '), scope)

    def owned(self, id_ses, tech):
        ses = self.sessions.get(id_ses)
        if not ses or ses.closing or ses.expires <= time.time() or not ses.tech or ses.tech['sub'] != tech['sub']:
            raise web.HTTPForbidden(text='Session not assigned to this technician')
        return ses

    async def create(self, req):
        # Use the socket peer, not an arbitrary forwarded address. Nginx also rate limits.
        now, peer = time.time(), req.remote or 'unknown'
        self.rates = {key: val for key, val in self.rates.items() if now - val[0] < 60}
        start, count = self.rates.get(peer, (now, 0))
        if count >= 6 or len(self.sessions) >= self.max_sessions:
            raise web.HTTPTooManyRequests(text='CLI capacity reached; retry later')
        self.rates[peer] = (start, count + 1)
        id_ses, token = secrets.token_hex(16), secrets.token_urlsafe(32)
        code = 'AUX-' + secrets.token_hex(4).upper()
        ses = Session(id_ses, code, hashlib.sha256(token.encode()).hexdigest(), now, now + 600)
        self.sessions[id_ses] = ses
        LOG.info('created node=%s session=%s', self.node, code)
        return web.json_response({**ses.public(), 'token': token, 'node': self.node}, status=201)

    async def listing(self, req):
        tech = self.ticket(req, 'control')
        return web.json_response({'node': self.node, 'sessions': [ses.public()
            for ses in self.sessions.values() if not ses.closing and ses.expires > time.time()
            and (ses.state == 'pending' or ses.tech and ses.tech['sub'] == tech['sub'])]})

    async def claim(self, req):
        tech = self.ticket(req, 'control')
        ses = self.sessions.get(req.match_info['id'])
        # No await occurs before the claim transition: two technicians cannot win together.
        if not ses or ses.state != 'pending' or ses.closing or not ses.agent or ses.expires <= time.time():
            raise web.HTTPConflict(text='Session already claimed or not connected')
        if not isinstance(tech.get('name'), str) or not isinstance(tech.get('contact'), str):
            raise web.HTTPForbidden()
        ses.tech = {key: tech[key] for key in ('sub', 'name', 'contact')}
        clv_dir = tech.get('direct_key', '')
        if clv_dir:
            try:
                clv_dir = asyncssh.import_public_key(clv_dir).export_public_key().decode()
            except (ValueError, asyncssh.Error):
                raise web.HTTPForbidden(text='Invalid technician public key') from None
            ses.tech['direct_key'] = clv_dir
        ses.key = asyncssh.generate_private_key('ssh-ed25519')
        ses.state = 'awaiting_client'
        self.registra(ses, 'claimed')
        await ses.agent.send_json(self.oferta(ses))
        LOG.info('claimed session=%s tech=%s', ses.code, tech['sub'])
        return web.json_response(ses.public())

    async def revoke(self, req):
        tech = self.ticket(req, 'control')
        ses = self.owned(req.match_info['id'], tech)
        await self.close(ses, 'technician_closed')
        return web.json_response({'state': 'closed'})

    async def revoke_agent(self, req):
        ses = self.by_token(req.match_info['id'], req.headers.get('Authorization', '').removeprefix('Bearer '))
        await self.close(ses, 'client_revoked')
        return web.json_response({'state': 'closed'})

    async def authenticate_socket(self, req, scope):
        if req.headers.get('Origin') not in self.origins:
            raise web.HTTPForbidden(text='Origin not allowed')
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=65536, compress=False)
        await ws.prepare(req)
        try:
            first = await asyncio.wait_for(ws.receive_json(), 5)
            if not isinstance(first, dict):
                raise ValueError()
            claims = self.tickets.consume(first.get('ticket', ''), scope)
            return ws, claims
        except (ValueError, TypeError, asyncio.TimeoutError, web.HTTPException):
            await ws.close(code=1008, message=b'Authorization required')
            return ws, None

    async def agent_socket(self, req):
        # Tokens travel in Authorization, never URL/query parameters or access logs.
        token = req.headers.get('Authorization', '').removeprefix('Bearer ')
        ses = self.by_token(req.match_info['id'], token)
        if ses.agent:
            raise web.HTTPConflict(text='Agent already connected')
        ws = web.WebSocketResponse(heartbeat=15, max_msg_size=65536, compress=False)
        await ws.prepare(req)
        ses.agent = ws
        if ses.res:
            ses.state = 'awaiting_resume'
            await ws.send_json(self.oferta(ses, True))
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    if not ses.bridge or ses.state != 'active':
                        raise ValueError('SSH bytes before client authorization')
                    await asyncio.get_running_loop().sock_sendall(ses.bridge, msg.data)
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    dat = json.loads(msg.data)
                    if dat.get('type') == 'ready' and ses.state in ('awaiting_client', 'awaiting_resume'):
                        # Identity labels arrive only after local consent. They never grant access.
                        ent = dat.get('device', {})
                        if not isinstance(ent, dict):
                            raise ValueError('Invalid device identity')
                        uid_usb, eqp_id = ent.get('usb_uuid', ''), ent.get('hardware_id', '')
                        if not isinstance(uid_usb, str) or not isinstance(eqp_id, str):
                            raise ValueError('Invalid device identity')
                        if uid_usb or eqp_id:
                            if (not isinstance(uid_usb, str) or str(uuid.UUID(uid_usb)) != uid_usb
                                    or not isinstance(eqp_id, str) or not re.fullmatch(r'[a-f0-9]{64}', eqp_id)):
                                raise ValueError('Invalid device identity')
                        if ses.uid_usb and (uid_usb != ses.uid_usb or eqp_id != ses.eqp_id):
                            raise ValueError('Support case device changed')
                        ses.uid_usb, ses.eqp_id = uid_usb, eqp_id
                        ses.host_key = asyncssh.import_public_key(dat['host_key'])
                        if ses.res:
                            # Reconnection must never extend the original authorization deadline.
                            if int(dat.get('expires', 0)) != int(ses.expires):
                                raise ValueError('Case deadline changed')
                        elif dat.get('resume') is True:
                            tms_fin = int(dat.get('expires', 0))
                            if not time.time() < tms_fin <= min(time.time() + 28800, ses.created + 29400):
                                raise ValueError('Invalid case deadline')
                            ses.res, ses.expires = True, tms_fin
                            self.guarda_caso(ses)
                        else:
                            ses.expires = time.time() + 3600
                        ses.state = 'ready'
                        if ses.res:
                            self.guarda_caso(ses)
                        self.registra(ses, 'authorized')
                        if ses.res:
                            await ws.send_json({'type': 'authorized', 'expires': int(ses.expires)})
                        LOG.info('client_authorized session=%s', ses.code)
                    elif dat.get('type') == 'revoke':
                        await self.close(ses, 'client_revoked')
                        break
                    else:
                        raise ValueError('Invalid agent state transition')
                else:
                    break
        except (ValueError, KeyError, OSError, asyncssh.Error):
            LOG.warning('agent_protocol_error session=%s', ses.code)
            await self.close(ses, 'agent_protocol_error')
        finally:
            if ses.agent is ws:
                await self.close(ses, 'agent_disconnected')
        return ws

    async def terminal(self, req):
        ws, tech = await self.authenticate_socket(req, 'terminal')
        if tech is None:
            return ws
        ses = None
        started = False
        try:
            ses = self.owned(req.match_info['id'], tech)
            if tech.get('session') != ses.id or ses.state != 'ready' or ses.browser:
                raise web.HTTPConflict(text='Session not ready or already in use')
            ses.browser, ses.state = ws, 'active'
            self.registra(ses, 'terminal_opened')
            started = True
            ses.terminal_task = asyncio.current_task()
            local, remote = socket.socketpair()
            local.setblocking(False)
            remote.setblocking(False)
            ses.bridge = local
            ws_ag = ses.agent
            await ws_ag.send_json({'type': 'open'})

            async def upstream():
                while chunk := await asyncio.get_running_loop().sock_recv(local, 32768):
                    await ws_ag.send_bytes(chunk)

            bridge_task = asyncio.create_task(upstream())
            try:
                # Pin exactly the host key supplied on this authorized agent connection.
                ses.ssh = await asyncssh.connect(ses.id + '.invalid', port=4242, sock=remote, username='root', config=None,
                    client_keys=[ses.key], agent_path=None, known_hosts=([ses.host_key], [], []),
                    encoding=None, login_timeout=15)
                ses.process = await ses.ssh.create_process(term_type='xterm-256color',
                    term_size=(100, 30), encoding=None)
                ssh_prc = ses.process
                await ws.send_json({'type': 'ready', 'code': ses.code})
                pending = 0
                drained = asyncio.Event()
                drained.set()

                async def output():
                    nonlocal pending
                    while chunk := await ssh_prc.stdout.read(32768):
                        while pending >= 131072:
                            drained.clear()
                            await drained.wait()
                        pending += len(chunk)
                        await ws.send_bytes(chunk)
                    await ws.close()

                out_task = asyncio.create_task(output())
                lease = time.monotonic() + self.auth_lease
                try:
                    while not ws.closed:
                        msg = await asyncio.wait_for(ws.receive(), max(.1, lease - time.monotonic()))
                        if msg.type == aiohttp.WSMsgType.BINARY:
                            ssh_prc.stdin.write(msg.data)
                            await ssh_prc.stdin.drain()
                        elif msg.type == aiohttp.WSMsgType.TEXT:
                            dat = json.loads(msg.data)
                            if dat.get('type') == 'auth':
                                renew = self.tickets.consume(dat['ticket'], 'terminal')
                                if renew['sub'] != tech['sub'] or renew.get('session') != ses.id:
                                    raise ValueError('Authorization changed')
                                lease = time.monotonic() + self.auth_lease
                            elif dat.get('type') == 'resize':
                                cols, rows = int(dat['cols']), int(dat['rows'])
                                if not 20 <= cols <= 300 or not 5 <= rows <= 150:
                                    raise ValueError('Invalid terminal size')
                                ssh_prc.change_terminal_size(cols, rows)
                            elif dat.get('type') == 'ack':
                                count = int(dat['bytes'])
                                if not 0 < count <= pending:
                                    raise ValueError('Invalid output acknowledgement')
                                pending -= count
                                drained.set()
                            else:
                                raise ValueError('Invalid terminal control')
                        else:
                            break
                finally:
                    out_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await out_task
            finally:
                bridge_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, OSError):
                    await bridge_task
                remote.close()
                local.close()
        except (web.HTTPException, ValueError, KeyError, OSError, asyncssh.Error, asyncio.TimeoutError):
            if ses and started and ses.browser is ws:
                await self.close(ses, 'authorization_or_transport_failed')
            await ws.close(code=1008, message=b'Session closed or authorization expired')
        finally:
            if ses and started and ses.browser is ws:
                await self.close(ses, 'terminal_closed')
            else:
                await ws.close()
        return ws

    async def close(self, ses, reason):
        if ses.closing:
            return
        res = ses.res and ses.expires > time.time() and reason in (
            'agent_disconnected', 'terminal_closed', 'authorization_or_transport_failed', 'cli_shutdown')
        if ses.susp:
            # Explicit revocation wins even while an old transport is still closing.
            if not res:
                ses.closing, ses.state = True, 'closed'
                self.registra(ses, 'closed', reason)
                self.sessions.pop(ses.id, None)
                if self.pth_est:
                    (self.pth_est / (ses.id + '.json')).unlink(missing_ok=True)
                    self.sincroniza_casos()
            return
        ses.susp = True
        ses.closing, ses.state = not res, 'reconnecting' if res else 'closed'
        self.registra(ses, 'disconnected' if res else 'closed', reason)
        if not res:
            self.sessions.pop(ses.id, None)
            if self.pth_est:
                (self.pth_est / (ses.id + '.json')).unlink(missing_ok=True)
                self.sincroniza_casos()
        LOG.info('closed session=%s reason=%s', ses.code, reason)
        # Close the SSH transport before the UI, so revocation stops input immediately.
        if ses.ssh:
            ses.ssh.close()
        if ses.bridge:
            ses.bridge.close()
        ws_ag, ws = ses.agent, ses.browser
        ses.agent = ses.browser = ses.bridge = ses.ssh = ses.process = ses.terminal_task = None
        if ws_ag and not ws_ag.closed:
            with contextlib.suppress(ConnectionError, RuntimeError):
                await ws_ag.send_json({'type': 'closed', 'reason': reason, 'resume': res})
            with contextlib.suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
                await ws_ag.close()
        if ws and not ws.closed:
            with contextlib.suppress(ConnectionError, RuntimeError, asyncio.TimeoutError):
                await ws.close()
        ses.host_key = None
        if not res or ses.closing:
            ses.key = None
        ses.susp = False

    async def sweep(self, app):
        async def monitor():
            while True:
                await asyncio.sleep(1)
                for ses in list(self.sessions.values()):
                    if ses.expires <= time.time():
                        await self.close(ses, 'expired')
        task = asyncio.create_task(monitor())
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        for ses in list(self.sessions.values()):
            await self.close(ses, 'cli_shutdown')
        self.history.db.close()

    def app(self):
        async def health(_):
            return web.json_response({'version': VERSION, 'node': self.node,
                                      'history_available': not self.history.failed})
        app = web.Application(client_max_size=16384)
        app.add_routes([
            web.get('/health', health),
            web.post('/api/sessions', self.create), web.get('/api/sessions', self.listing),
            web.get('/api/history', self.history_listing),
            web.post('/api/sessions/{id}/claim', self.claim),
            web.post('/api/sessions/{id}/close', self.revoke),
            web.post('/api/sessions/{id}/agent-close', self.revoke_agent),
            web.get('/agent/{id}', self.agent_socket), web.get('/terminal/{id}', self.terminal)])
        app.cleanup_ctx.append(self.sweep)
        return app


def main():
    os.umask(0o077)
    cfg_full = json.loads(Path(os.environ.get('AUX_CLI_CONFIG', '/etc/aux-cli/fast-boot.json')).read_text())
    node = os.environ.get('AUX_CLI_NODE', 'excalibur')
    cfg = cfg_full['cli']['nodes'][node]
    secret = Path(os.environ['AUX_CLI_SECRET_FILE']).read_bytes().strip()
    if len(secret) < 32:
        raise ValueError('CLI signing secret needs at least 32 random bytes')
    origins = cfg_full['cli'].get('origins', ['https://tec.1-s.es', 'https://tec.1-s.eu', 'https://t.1-s.es', 'https://t.1-s.eu'])
    cli = CLI(secret, node, origins, cfg.get('max_sessions', 64),
              os.environ.get('AUX_CLI_STATE', '/var/lib/aux-cli/cases'))
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # TLS terminates at the local Nginx vhost. Do not bind this service publicly.
    web.run_app(cli.app(), host='127.0.0.1', port=cfg.get('port', 8096), access_log=None)


if __name__ == '__main__':
    main()
