#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Run the real Live agent twice through a local HTTPS/WSS gateway with fake SSH startup."""
import asyncio
import os
from pathlib import Path
import secrets
import ssl
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import aiohttp
from aiohttp.test_utils import TestClient, TestServer
import asyncssh

DIR_APP=Path(__file__).resolve().parent
sys.path[:0]=[str(DIR_APP/'payload'),str(DIR_APP.parent/'usb/portable'),str(DIR_APP.parent/'cli')]
import runtime as portable_usb
sys.modules['portable_usb']=portable_usb
import agent
import assist
import support_case
from server import CLI, firma


@unittest.skipUnless(os.geteuid()==0,'private root case contract requires root')
class WebResume(unittest.IsolatedAsyncioTestCase):
    async def test_real_agent_reconnects_without_second_local_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp);secret=secrets.token_bytes(32)
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                '-keyout',str(pth/'tls.key'),'-out',str(pth/'tls.crt'),'-subj','/CN=127.0.0.1',
                '-addext','subjectAltName=IP:127.0.0.1'],check=True,capture_output=True)
            ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(pth/'tls.crt',pth/'tls.key')
            trusted=ssl.create_default_context(cafile=str(pth/'tls.crt'))
            cli=CLI(secret,'fixture',['https://tec.example.test'],pth_est=pth/'server-cases')
            srv=TestServer(cli.app(),scheme='https');await srv.start_server(ssl=ctx)
            url=str(srv.make_url('/')).rstrip('/')
            cls=aiohttp.ClientSession
            real=subprocess.run
            host=asyncssh.generate_private_key('ssh-ed25519')
            def orden(args,**cfg):
                return SimpleNamespace(returncode=0) if args[0]=='systemctl' else real(args,**cfg)
            def sesion(*args,**cfg):
                cfg['connector']=aiohttp.TCPConnector(ssl=trusted)
                return cls(*args,**cfg)
            def abre(*args,**cfg):
                (pth/'host_ed25519').write_bytes(host.export_private_key())
                return host.export_public_key().decode()
            async def espera(txt):
                for idx in range(300):
                    if cli.sessions and next(iter(cli.sessions.values())).state==txt:return
                    await asyncio.sleep(.01)
                self.fail('Agent did not reach '+txt)
            uid_usb='8dc593dc-29b5-4484-b85d-91ab980810a5'
            with patch.object(support_case,'ruta',return_value=(uid_usb,pth/'case.json')), \
                 patch.object(support_case,'equipo',return_value='a'*64),patch.object(support_case,'portatil',return_value=True), \
                 patch.object(assist,'DIR_RUN',pth),patch.object(assist,'estado'),patch.object(assist,'limpia'), \
                 patch.object(agent,'abre_ssh',side_effect=abre) as ssh,patch.object(agent.subprocess,'run',side_effect=orden), \
                 patch.object(agent.aiohttp,'ClientSession',side_effect=sesion), \
                 patch.object(agent,'pregunta',new=AsyncMock(side_effect=['SOLICITO','AUTORIZO'])) as entrada:
                task=asyncio.create_task(agent.run(url))
                try:
                    await espera('pending')
                    ses=next(iter(cli.sessions.values()))
                    for idx in range(100):
                        if ses.agent:break
                        await asyncio.sleep(.01)
                    tok=firma({'aud':'fixture','scope':'control','sub':'tec_fixture','name':'Fixture',
                        'contact':'fixture@example.test','exp':int(time.time())+60,'nonce':secrets.token_hex(24)},secret)
                    async with cls(connector=aiohttp.TCPConnector(ssl=trusted)) as client:
                        async with client.post(url+'/api/sessions/'+ses.id+'/claim',headers={'Authorization':'Bearer '+tok}) as rsp:
                            self.assertEqual(rsp.status,200)
                    await espera('ready')
                    cas=support_case.carga();self.assertTrue(cas)
                    await cli.close(ses,'agent_disconnected')
                    await espera('ready')
                    self.assertEqual(entrada.await_count,2)
                    self.assertEqual(ssh.call_count,2)
                    self.assertEqual(ssh.call_args.args[2],cas['host_key'])
                    self.assertEqual(ses.expires,cas['expires'])
                    await cli.close(ses,'technician_closed')
                    await asyncio.wait_for(task,3)
                    self.assertFalse((pth/'case.json').exists())
                finally:
                    task.cancel();await asyncio.gather(task,return_exceptions=True)
                    await srv.close()


if __name__=='__main__':unittest.main()
