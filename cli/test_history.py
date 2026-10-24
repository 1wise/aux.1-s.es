#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Exercise consent-bound identity, durable history and technician isolation over WSS."""
import asyncio
import json
from pathlib import Path
import secrets
import tempfile
import time
import unittest
from unittest.mock import patch
import sqlite3
from aiohttp.test_utils import TestClient, TestServer
import asyncssh
from server import CLI, firma


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name) / 'cases'
        self.secret = secrets.token_bytes(32)
        await self.inicia()

    async def inicia(self):
        self.cli = CLI(self.secret, 'fixture', pth_est=self.pth)
        self.client = TestClient(TestServer(self.cli.app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    def ticket(self, tec_id='tec_fixture'):
        return {'Authorization': 'Bearer ' + firma({'aud':'fixture','scope':'control','sub':tec_id,
            'name':'Fixture','contact':'fixture@example.test','exp':int(time.time())+60,
            'nonce':secrets.token_hex(24)},self.secret)}

    async def autoriza(self, uid_usb='12345678-1234-4321-8765-123456789abc'):
        ses = await (await self.client.post('/api/sessions')).json()
        ws = await self.client.ws_connect('/agent/'+ses['id'],headers={'Authorization':'Bearer '+ses['token']})
        dat = await self.client.post('/api/sessions/'+ses['id']+'/claim',headers=self.ticket())
        self.assertEqual(dat.status,200);await ws.receive_json()
        clv_host = asyncssh.generate_private_key('ssh-ed25519')
        ses['expires'] = int(time.time())+120
        await ws.send_json({'type':'ready','host_key':clv_host.export_public_key().decode(),
            'resume':True,'expires':ses['expires'],'device':{'usb_uuid':uid_usb,'hardware_id':'a'*64}})
        await ws.receive_json()
        return ses,ws

    async def test_history_survives_revoke_restart_and_contains_no_capabilities(self):
        ses,ws = await self.autoriza()
        dat = await (await self.client.get('/api/history',headers=self.ticket())).json()
        self.assertEqual([evt['event'] for evt in dat['events']],['claimed','authorized'])
        self.assertEqual(dat['events'][-1]['session']['device']['hardware_id'],'a'*64)
        await self.client.post('/api/sessions/'+ses['id']+'/close',headers=self.ticket())
        await ws.close();await self.client.close();await self.inicia()
        dat = await (await self.client.get('/api/history',headers=self.ticket())).json()
        self.assertEqual(dat['events'][-1]['session']['state'],'closed')
        self.assertEqual(dat['events'][-1]['reason'],'technician_closed')
        self.assertNotIn(ses['id'],self.cli.sessions)
        self.assertNotIn(ses['token'],json.dumps(dat))
        self.assertNotIn('PRIVATE KEY',json.dumps(dat))
        self.assertEqual((self.pth.parent/'history.sqlite3').stat().st_mode&0o777,0o600)

    async def test_unrelated_technician_and_unsigned_reads_cannot_see_history(self):
        ses,ws = await self.autoriza()
        dat = await (await self.client.get('/api/history',headers=self.ticket('tec_other'))).json()
        self.assertEqual(dat['events'],[])
        dat = await (await self.client.get('/api/sessions',headers=self.ticket('tec_other'))).json()
        self.assertEqual(dat['sessions'],[])
        self.assertEqual((await self.client.get('/api/history')).status,401)
        self.assertEqual((await self.client.get('/api/history?cursor=-1',headers=self.ticket())).status,400)
        await ws.close()

    async def test_identity_cannot_change_on_reconnect(self):
        ses,ws = await self.autoriza();await ws.close()
        for idx in range(100):
            if not self.cli.sessions[ses['id']].susp and not self.cli.sessions[ses['id']].agent:break
            await asyncio.sleep(.01)
        await self.client.close();await self.inicia()
        self.assertEqual(self.cli.sessions[ses['id']].eqp_id,'a'*64)
        ws = await self.client.ws_connect('/agent/'+ses['id'],headers={'Authorization':'Bearer '+ses['token']})
        await ws.receive_json()
        await ws.send_json({'type':'ready','host_key':asyncssh.generate_private_key('ssh-ed25519').export_public_key().decode(),
            'resume':True,'expires':ses['expires'],'device':{'usb_uuid':'12345678-1234-4321-8765-123456789abc','hardware_id':'b'*64}})
        await ws.receive()
        self.assertNotIn(ses['id'],self.cli.sessions)
        dat = await (await self.client.get('/api/history',headers=self.ticket())).json()
        self.assertEqual(dat['events'][-1]['reason'],'agent_protocol_error')
        await ws.close()

    async def test_pagination_and_revocation_work_when_audit_disk_fails(self):
        for idx in range(205):self.cli.history.append('tec_fixture',{'event':'fixture'})
        dat = await (await self.client.get('/api/history',headers=self.ticket())).json()
        self.assertEqual(len(dat['events']),200);self.assertTrue(dat['more'])
        dat = await (await self.client.get('/api/history?cursor='+str(dat['cursor']),headers=self.ticket())).json()
        self.assertEqual(len(dat['events']),5);self.assertFalse(dat['more'])
        ses,ws = await self.autoriza()
        with patch.object(self.cli.history,'append',side_effect=sqlite3.OperationalError('fixture disk full')):
            with self.assertLogs('aux.cli',level='ERROR'):
                dat = await self.client.post('/api/sessions/'+ses['id']+'/close',headers=self.ticket())
            self.assertEqual(dat.status,200)
        self.assertNotIn(ses['id'],self.cli.sessions);await ws.close()
        self.assertEqual((await self.client.get('/api/history',headers=self.ticket())).status,503)


if __name__=='__main__':unittest.main()
