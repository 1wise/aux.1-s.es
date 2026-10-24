#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Simulate reboot and gateway restart over real WebSocket and SSH transports."""
import asyncio
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import unittest
import aiohttp
from aiohttp.test_utils import TestClient, TestServer
import asyncssh
from server import CLI, firma


class Resume(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name) / 'cases'
        self.secret = secrets.token_bytes(32)
        await self.inicia()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    async def inicia(self):
        self.cli = CLI(self.secret, 'fixture', ['https://tec.example.test'], pth_est=self.pth)
        self.client = TestClient(TestServer(self.cli.app()))
        await self.client.start_server()

    def ticket(self, scope='control', cas_id='', usr='tec_fixture'):
        return firma({'aud': 'fixture', 'scope': scope, 'sub': usr, 'session': cas_id,
                      'name': 'Fixture', 'contact': 'fixture@example.test',
                      'exp': int(time.time()) + 60, 'nonce': secrets.token_hex(24)}, self.secret)

    async def crea(self):
        ses = await (await self.client.post('/api/sessions')).json()
        ws = await self.conecta(ses)
        dat = await self.client.post('/api/sessions/' + ses['id'] + '/claim',
            headers={'Authorization': 'Bearer ' + self.ticket()})
        self.assertEqual(dat.status, 200)
        cas = await ws.receive_json()
        self.host = asyncssh.generate_private_key('ssh-ed25519')
        ses['expires'] = int(time.time()) + 120
        await self.autoriza(ws, ses)
        return ses, ws, cas

    async def conecta(self, ses):
        return await self.client.ws_connect('/agent/' + ses['id'],
            headers={'Authorization': 'Bearer ' + ses['token']})

    async def autoriza(self, ws, ses):
        await ws.send_json({'type': 'ready', 'host_key': self.host.export_public_key().decode(),
                           'resume': True, 'expires': ses['expires']})
        self.assertEqual(await ws.receive_json(), {'type': 'authorized', 'expires': ses['expires']})

    async def desconecta(self, ws, ses):
        await ws.close()
        for idx in range(100):
            if not self.cli.sessions[ses['id']].agent and not self.cli.sessions[ses['id']].susp:
                break
            await asyncio.sleep(.01)
        self.assertEqual(self.cli.sessions[ses['id']].state, 'reconnecting')

    async def test_case_survives_client_and_gateway_restart_with_fixed_identity(self):
        ses, ws, cas = await self.crea()
        arc = self.pth / (ses['id'] + '.json')
        self.assertEqual(arc.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(ses['token'], arc.read_text())
        await self.desconecta(ws, ses)
        await self.client.close()
        await self.inicia()
        ws = await self.conecta(ses)
        dat = await ws.receive_json()
        self.assertEqual(dat['type'], 'resume')
        self.assertEqual(dat['key'], cas['key'])
        self.assertEqual(dat['technician']['sub'], cas['technician']['sub'])
        self.assertEqual(dat['expires'], ses['expires'])
        await self.autoriza(ws, ses)
        self.assertEqual(self.cli.sessions[ses['id']].expires, ses['expires'])
        await ws.close()

    async def test_offline_revocation_removes_durable_capability(self):
        ses, ws, cas = await self.crea()
        await self.desconecta(ws, ses)
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/close',
            headers={'Authorization': 'Bearer ' + self.ticket(usr='other_technician')})
        self.assertEqual(rsp.status, 403)
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/close',
            headers={'Authorization': 'Bearer ' + self.ticket()})
        self.assertEqual(rsp.status, 200)
        self.assertFalse((self.pth / (ses['id'] + '.json')).exists())
        with self.assertRaises(aiohttp.WSServerHandshakeError):
            await self.conecta(ses)
        await self.client.close();await self.inicia()
        self.assertNotIn(ses['id'], self.cli.sessions)

    async def test_reconnection_cannot_extend_deadline_and_client_can_revoke(self):
        ses, ws, cas = await self.crea()
        await self.desconecta(ws, ses)
        ws = await self.conecta(ses);await ws.receive_json()
        await ws.send_json({'type': 'ready', 'host_key': self.host.export_public_key().decode(),
                           'resume': True, 'expires': ses['expires'] + 60})
        await ws.receive()
        self.assertNotIn(ses['id'], self.cli.sessions)
        self.assertFalse((self.pth / (ses['id'] + '.json')).exists())
        ses, ws, cas = await self.crea()
        rsp = await self.client.post('/api/sessions/' + ses['id'] + '/agent-close',
            headers={'Authorization': 'Bearer ' + ses['token']})
        self.assertEqual(rsp.status, 200)
        self.assertNotIn(ses['id'], self.cli.sessions)

    async def test_expired_cases_are_not_restored_from_disk(self):
        ses, ws, cas = await self.crea()
        await self.desconecta(ws, ses)
        arc = self.pth / (ses['id'] + '.json')
        dat = json.loads(arc.read_text());dat['expires'] = time.time() - 1
        arc.write_text(json.dumps(dat))
        await self.client.close();await self.inicia()
        self.assertNotIn(ses['id'], self.cli.sessions)
        self.assertFalse(arc.exists())

    async def test_two_real_ssh_terminals_use_the_same_case_after_reconnect(self):
        ses, ws, cas = await self.crea()
        clv_pub = asyncssh.import_public_key(cas['key'])
        class SSH(asyncssh.SSHServer):
            def begin_auth(self, usr):return True
            def public_key_auth_supported(self):return True
            def validate_public_key(self, usr, key):return usr == 'root' and key == clv_pub
        async def shell(proc):
            proc.stdout.write(await proc.stdin.readexactly(15))
            await proc.stdout.drain()
            await proc.stdin.read()
        srv = await asyncssh.create_server(SSH, '127.0.0.1', 0, server_host_keys=[self.host],
                                          process_factory=shell, encoding=None)
        try:
            for idx in range(2):
                if idx:
                    ws = await self.conecta(ses);dat = await ws.receive_json()
                    self.assertEqual(dat['type'], 'resume')
                    await self.autoriza(ws, ses)
                trn_act = await self.client.ws_connect('/terminal/' + ses['id'], origin='https://tec.example.test')
                await trn_act.send_json({'ticket': self.ticket('terminal', ses['id'])})
                self.assertEqual((await ws.receive_json())['type'], 'open')
                reader, writer = await asyncio.open_connection('127.0.0.1', srv.get_port())
                async def upload():
                    while dat := await reader.read(32768):await ws.send_bytes(dat)
                async def download():
                    async for dat in ws:
                        if dat.type != aiohttp.WSMsgType.BINARY:break
                        writer.write(dat.data);await writer.drain()
                task = [asyncio.create_task(upload()), asyncio.create_task(download())]
                try:
                    self.assertEqual((await asyncio.wait_for(trn_act.receive_json(), 5))['type'], 'ready')
                    await trn_act.send_bytes(b'RESUMED-SHELL-' + str(idx).encode())
                    dat = await asyncio.wait_for(trn_act.receive(), 5)
                    self.assertEqual(dat.data, b'RESUMED-SHELL-' + str(idx).encode())
                    await trn_act.close()
                    await self.desconecta(ws, ses)
                finally:
                    for dat in task:dat.cancel()
                    await asyncio.gather(*task, return_exceptions=True)
                    writer.close();await writer.wait_closed()
        finally:
            srv.close();await srv.wait_closed()


if __name__ == '__main__':unittest.main()
