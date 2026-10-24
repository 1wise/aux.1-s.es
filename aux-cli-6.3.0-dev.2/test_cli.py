#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Exercise real SSH through the WebSocket bridge, consent, ownership and revocation."""
import asyncio
import contextlib
import json
from pathlib import Path
import secrets
import ssl
import subprocess
import tempfile
import time
import unittest

from aiohttp.test_utils import TestClient, TestServer
import aiohttp
import asyncssh
from server import CLI, Tickets, firma


class Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.secret = secrets.token_bytes(32)
        self.cli = CLI(self.secret, 'test', ['https://tec.example.test'])
        self.client = TestClient(TestServer(self.cli.app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    def ticket(self, scope='control', sub='tec_one', ses=''):
        return firma({'aud': 'test', 'scope': scope, 'sub': sub, 'session': ses,
            'name': 'Técnico Uno', 'contact': 'https://example.test',
            'exp': int(time.time()) + 60, 'nonce': secrets.token_hex(20)}, self.secret)

    def auth(self, sub='tec_one'):
        return {'Authorization': 'Bearer ' + self.ticket(sub=sub)}

    async def create(self):
        rsp = await self.client.post('/api/sessions')
        self.assertEqual(rsp.status, 201)
        ses = await rsp.json()
        ws = await self.client.ws_connect('/agent/' + ses['id'],
            headers={'Authorization': 'Bearer ' + ses['token']})
        return ses, ws

    async def claim(self, ses):
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/claim', headers=self.auth())
        self.assertEqual(rsp.status, 200)

    async def browser(self, ses, sub='tec_one'):
        ws = await self.client.ws_connect('/terminal/' + ses['id'], origin='https://tec.example.test')
        await ws.send_json({'ticket': self.ticket('terminal', sub, ses['id'])})
        return ws

    async def test_ticket_signature_audience_expiry_and_replay(self):
        tok = self.ticket()
        self.cli.tickets.consume(tok, 'control')
        with self.assertRaises(aiohttp.web.HTTPUnauthorized):
            self.cli.tickets.consume(tok, 'control')
        for bad in [tok + 'x', self.ticket('terminal')]:
            with self.assertRaises(aiohttp.web.HTTPUnauthorized):
                self.cli.tickets.consume(bad, 'control')
        with self.assertRaises(aiohttp.web.HTTPUnauthorized):
            Tickets(self.secret, 'other').consume(self.ticket(), 'control')

    async def test_no_claim_without_connected_client_and_no_secret_in_listing(self):
        rsp = await self.client.post('/api/sessions');ses = await rsp.json()
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/claim', headers=self.auth())
        self.assertEqual(rsp.status, 409)
        rsp = await self.client.get('/api/sessions', headers=self.auth())
        self.assertNotIn(ses['token'], await rsp.text())
        rsp = await self.client.get('/api/sessions')
        self.assertEqual(rsp.status, 401)

    async def test_client_confirmation_required_and_exclusive_claim(self):
        ses, agent = await self.create();await self.claim(ses)
        offer = await agent.receive_json();self.assertEqual(offer['type'], 'offer')
        self.assertEqual(self.cli.sessions[ses['id']].state, 'awaiting_client')
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/claim', headers=self.auth('tec_two'))
        self.assertEqual(rsp.status, 409)
        browser = await self.browser(ses)
        self.assertIn((await browser.receive()).type, [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED])
        self.assertIn(ses['id'], self.cli.sessions)
        await agent.close()

    async def test_wrong_technician_and_origin_cannot_enter(self):
        ses, agent = await self.create();await self.claim(ses);await agent.receive_json()
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.client.ws_connect('/terminal/' + ses['id'], origin='https://evil.example.test')
        browser = await self.browser(ses, 'tec_two')
        self.assertIn((await browser.receive()).type, [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED])
        self.assertIn(ses['id'], self.cli.sessions)
        await agent.close()

    async def test_invalid_agent_token_and_bytes_before_consent(self):
        ses, agent = await self.create()
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.client.ws_connect('/agent/' + ses['id'], headers={'Authorization': 'Bearer wrong'})
        await agent.send_bytes(b'SSH-2.0-without-consent\r\n')
        await agent.receive()
        self.assertNotIn(ses['id'], self.cli.sessions)

    async def test_expiry_removes_session(self):
        ses, agent = await self.create()
        self.cli.sessions[ses['id']].expires = time.time() - 1
        await asyncio.wait_for(agent.receive(), 3)
        self.assertNotIn(ses['id'], self.cli.sessions)

    async def test_https_wss_and_certificate_validation(self):
        with tempfile.TemporaryDirectory(prefix='aux-tls-') as tmp:
            key, cert = Path(tmp) / 'tls.key', Path(tmp) / 'tls.crt'
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                '-keyout', str(key), '-out', str(cert), '-subj', '/CN=127.0.0.1',
                '-addext', 'subjectAltName=IP:127.0.0.1'], check=True, capture_output=True)
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert, key)
            trusted = ssl.create_default_context(cafile=str(cert))
            tls_cli = CLI(self.secret, 'tls', ['https://tec.example.test'])
            server = TestServer(tls_cli.app(), scheme='https')
            await server.start_server(ssl=ctx)
            try:
                async with aiohttp.ClientSession() as client:
                    with self.assertRaises(aiohttp.ClientConnectorCertificateError):
                        await client.post(server.make_url('/api/sessions'))
                    async with client.post(server.make_url('/api/sessions'), ssl=trusted) as rsp:
                        self.assertEqual(rsp.status, 201);ses = await rsp.json()
                    url = str(server.make_url('/agent/' + ses['id'])).replace('https://', 'wss://')
                    async with client.ws_connect(url, ssl=trusted,
                        headers={'Authorization': 'Bearer ' + ses['token']}) as ws:
                        await ws.send_json({'type': 'revoke'})
                        await ws.receive()
                    self.assertNotIn(ses['id'], tls_cli.sessions)
            finally:
                await server.close()

    async def test_real_ssh_binary_utf8_and_client_revocation(self):
        await self.ssh_fixture()

    async def test_wrong_ssh_host_key_is_rejected(self):
        await self.ssh_fixture(wrong_host=True)

    async def test_expired_portal_authorization_closes_real_ssh(self):
        await self.ssh_fixture(expire_authorization=True)

    async def ssh_fixture(self, wrong_host=False, expire_authorization=False):
        ses, agent = await self.create();await self.claim(ses)
        offer = await agent.receive_json()
        accepted = asyncssh.import_public_key(offer['key'])
        host = asyncssh.generate_private_key('ssh-ed25519')
        class SSH(asyncssh.SSHServer):
            def begin_auth(self, username): return True
            def public_key_auth_supported(self): return True
            def validate_public_key(self, username, key): return username == 'root' and key == accepted
        paste_payload = b'k' * 165
        async def shell(proc):
            self.assertEqual(proc.term_type, 'xterm-256color')
            proc.stdout.write(b'caf\xc3');await proc.stdout.drain()
            proc.stdout.write(b'\xa9 \xc3\xb1 \x1b[32mOK\x1b[0m\r\n')
            val = await proc.stdin.readexactly(len(paste_payload))
            self.assertEqual(val, paste_payload)
            proc.stdout.write(b'ECHO:' + val);await proc.stdout.drain()
            await proc.stdin.read()
        ssh_server = await asyncssh.create_server(SSH, '127.0.0.1', 0,
            server_host_keys=[host], process_factory=shell, encoding=None)
        announced = asyncssh.generate_private_key('ssh-ed25519') if wrong_host else host
        if expire_authorization:
            self.cli.auth_lease = .2
        await agent.send_json({'type': 'ready', 'host_key': announced.export_public_key().decode()})
        # Confirm the state transition has been processed before opening the browser.
        for _ in range(20):
            if self.cli.sessions[ses['id']].state == 'ready': break
            await asyncio.sleep(.01)
        browser = await self.browser(ses)
        self.assertEqual((await agent.receive_json())['type'], 'open')
        reader, writer = await asyncio.open_connection('127.0.0.1', ssh_server.get_port())
        async def uplink():
            while val := await reader.read(32768): await agent.send_bytes(val)
        async def downlink():
            async for msg in agent:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    writer.write(msg.data);await writer.drain()
                else: break
        tasks = [asyncio.create_task(uplink()), asyncio.create_task(downlink())]
        try:
            if wrong_host:
                msg = await asyncio.wait_for(browser.receive(), 5)
                self.assertIn(msg.type, [aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED])
                self.assertNotIn(ses['id'], self.cli.sessions)
                return
            ready = await asyncio.wait_for(browser.receive_json(), 10)
            self.assertEqual(ready['type'], 'ready')
            # Model a full clipboard paste as one terminal input frame.
            await browser.send_bytes(paste_payload)
            buf = b''
            while b'ECHO:' + paste_payload not in buf:
                msg = await asyncio.wait_for(browser.receive(), 10)
                self.assertEqual(msg.type, aiohttp.WSMsgType.BINARY)
                buf += msg.data
            self.assertIn('café ñ'.encode(), buf)
            if not expire_authorization:
                await agent.send_json({'type': 'revoke'})
            await asyncio.wait_for(browser.receive(), 5)
            self.assertNotIn(ses['id'], self.cli.sessions)
        finally:
            for task in tasks: task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            writer.close();await writer.wait_closed()
            ssh_server.close();await ssh_server.wait_closed()
            await browser.close();await agent.close()


if __name__ == '__main__':
    unittest.main()
