#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.2
# Author & Credits: https://www.alawise.es/1-s
"""Run the real PHP dashboard against a real TLS gateway and isolated account fixtures."""
import argparse
import asyncio
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlencode
import aiohttp
from aiohttp.test_utils import TestServer
import asyncssh
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'cli'))
from server import CLI, firma


async def main(php):
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='aux-registry-web-') as tmp:
        pth=Path(tmp);(pth/'sessions').mkdir();(pth/'private').mkdir()
        clv_host=pth/'tls.key';arc=pth/'tls.crt'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
            '-keyout',str(clv_host),'-out',str(arc),'-subj','/CN=127.0.0.1',
            '-addext','subjectAltName=IP:127.0.0.1'],check=True,capture_output=True)
        cfg=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);cfg.load_cert_chain(arc,clv_host)
        res=ssl.create_default_context(cafile=str(arc));txt=secrets.token_hex(32)
        (pth/'secret').write_text(txt);(pth/'secret').chmod(0o600)
        tec=CLI(txt.encode(),'fixture',pth_est=pth/'gateway/cases')
        reg=TestServer(tec.app(),scheme='https');await reg.start_server(ssl=cfg)
        (pth/'config.json').write_text(json.dumps({'cli':{'enabled':True,'primary':'fixture',
            'nodes':{'fixture':{'url':str(reg.make_url('')).rstrip('/'),'secret_file':str(pth/'secret')}}}}))
        env=os.environ|{'AUX_ASSIST_DATA_DIR':str(pth/'private'),'AUX_TEST_WEB':str(root/'web'),
                        'AUX_ASSIST_CONFIG':str(pth/'config.json')}
        init=pth/'fixture.php'
        init.write_text('''<?php
define('AUX_ASSIST_ENTRY',true);require getenv('AUX_TEST_WEB').'/lib.php';
$tec=['id'=>'tec_fixture','usuario_id'=>'usr_fixture','nombre'=>'Tech Fixture','correo'=>'tech@example.test',
 'contacto'=>'https://example.test','estado'=>'activo','email_confirmado'=>true,'totp_seed'=>'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'];
$usr=['id'=>'usr_fixture','nombre'=>'Tech Fixture','correo'=>'tech@example.test','estado'=>'activo','email_confirmado'=>true];
$ent=$tec;$ent['id']='tec_other';$ent['usuario_id']='usr_other';$ent['nombre']='Other Tech';
$dat=$usr;$dat['id']='usr_other';$dat['correo']='other@example.test';
datos(function(&$reg)use($tec,$usr,$ent,$dat){$reg['usuarios']=[$usr,$dat];$reg['tecnicos']=[$tec,$ent];},true);
session_name('tec_assist');session_id('registry-fixture');session_start();
$_SESSION=['usuario'=>$usr['id'],'csrf'=>'fixture-csrf','cli_2fa'=>time(),'cli_2fa_tec'=>$tec['id'],'cli_2fa_seed'=>hash('sha256',$tec['totp_seed'])];session_write_close();
session_id('registry-other');session_start();$_SESSION=['usuario'=>$dat['id'],'csrf'=>'fixture-csrf','cli_2fa'=>time(),'cli_2fa_tec'=>$ent['id'],'cli_2fa_seed'=>hash('sha256',$tec['totp_seed'])];session_write_close();
session_id('registry-no-factor');session_start();$_SESSION=['usuario'=>$usr['id'],'csrf'=>'fixture-csrf'];session_write_close();
''')
        cfg=[php,'-d','session.save_path='+str(pth/'sessions'),'-d','openssl.cafile='+str(arc)]
        subprocess.run(cfg+[str(init)],env=env,check=True,capture_output=True)
        arc=pth/'router.php';arc.write_text("<?php $_SERVER['HTTPS']='on'; require getenv('AUX_TEST_WEB').'/cases.php';")
        with socket.socket() as fd:fd.bind(('127.0.0.1',0));nom=fd.getsockname()[1]
        fd=(pth/'server.log').open('w+')
        ent=subprocess.Popen(cfg+['-S','127.0.0.1:'+str(nom),str(arc)],env=env,stdout=fd,stderr=fd)
        def request(dat=None,url='/cases.php',ses='registry-fixture'):
            clt=http.client.HTTPConnection('127.0.0.1',nom,timeout=15)
            clt.request('POST' if dat is not None else 'GET',url,urlencode(dat) if dat is not None else None,
                {'Content-Type':'application/x-www-form-urlencoded','Cookie':'tec_assist='+ses})
            res=clt.getresponse();dat=res.status,dict(res.getheaders()),res.read().decode();clt.close();return dat
        async def post(**dat):return await asyncio.to_thread(request,{'csrf':'fixture-csrf',**dat})
        try:
            for idx in range(100):
                try:await asyncio.to_thread(request);break
                except OSError:await asyncio.sleep(.03)
            else:raise RuntimeError('PHP fixture did not start')
            assert 'Client register' not in (await asyncio.to_thread(request,ses='anonymous'))[2]
            assert 'Client register' not in (await asyncio.to_thread(request,ses='registry-no-factor'))[2]
            assert (await post(action='client_save',name='<script>client</script>',email='client@example.test'))[0]==303
            dat=json.loads((pth/'private/registry.json').read_text());clt_id=next(iter(dat['clients']))
            assert (await post(action='usb_save',label='Field USB',usb_uuid='12345678-1234-4321-8765-123456789abc',client_id=clt_id,lifecycle='active'))[0]==303
            async with aiohttp.ClientSession() as clt:
                async with clt.post(reg.make_url('/api/sessions'),ssl=res) as dat:ses=await dat.json()
                ws=await clt.ws_connect(reg.make_url('/agent/'+ses['id']),ssl=res,headers={'Authorization':'Bearer '+ses['token']})
                dat=firma({'aud':'fixture','scope':'control','sub':'tec_fixture','name':'Tech Fixture','contact':'fixture@example.test',
                    'exp':int(time.time())+60,'nonce':secrets.token_hex(24)},txt.encode())
                async with clt.post(reg.make_url('/api/sessions/'+ses['id']+'/claim'),ssl=res,headers={'Authorization':'Bearer '+dat}) as dat:assert dat.status==200
                await ws.receive_json()
                await ws.send_json({'type':'ready','host_key':asyncssh.generate_private_key('ssh-ed25519').export_public_key().decode(),
                    'resume':True,'expires':int(time.time())+120,'device':{'usb_uuid':'12345678-1234-4321-8765-123456789abc','hardware_id':'a'*64}})
                await ws.receive_json();cas_id='fixture:'+ses['id']
                dat=await post(action='sync',format='json');assert dat[0]==200,dat
                dat=json.loads(dat[2]);assert dat['nodes']=={'fixture':'online'} and dat['cases'][0]['connection']=='ready',dat
                dat=await asyncio.to_thread(request,url='/cases.php?case='+cas_id)
                assert '&lt;script&gt;client&lt;/script&gt;' in dat[2] and '<script>client</script>' not in dat[2]
                assert 'Field USB' in dat[2] and 'Gateway connected' in dat[2]
                assert (await post(action='note_add',id=cas_id,note='<img src=x onerror=alert(1)>'))[0]==303
                dat=await asyncio.to_thread(request,url='/cases.php?case='+cas_id)
                assert '&lt;img src=x onerror=alert(1)&gt;' in dat[2] and '<img src=x onerror=alert(1)>' not in dat[2]
                dat=await asyncio.to_thread(request,url='/cases.php?case='+cas_id,ses='registry-other')
                assert 'Record unavailable' in dat[2] and 'Field USB' not in dat[2]
                dat=await asyncio.to_thread(request,{'csrf':'wrong','action':'note_add','id':cas_id,'note':'CSRF fixture'})
                assert 'Expired form' in dat[2]
                assert 'CSRF fixture' not in (pth/'private/registry.json').read_text()
                assert (await post(action='end_access',id=cas_id))[0]==303
                dat=await asyncio.to_thread(request,url='/cases.php?case='+cas_id)
                assert 'Authorization closed' in dat[2] and '&lt;img' in dat[2]
                assert ses['token'] not in (pth/'private/registry.json').read_text()
                dat=await asyncio.to_thread(request,{'csrf':'fixture-csrf','action':'sync','format':'json'},ses='registry-other')
                assert json.loads(dat[2])['cases']==[]
                await ws.close()
            await reg.close()
            dat=await post(action='sync',format='json')
            assert json.loads(dat[2])['nodes']=={'fixture':'unavailable'}
            fd.flush();fd.seek(0);assert 'Fatal error' not in fd.read()
            print('PASS: real PHP dashboard + TLS gateway; identity import, private views, CSRF/TOTP, escaped notes, revoke/history retention and offline state')
        finally:
            ent.terminate();ent.wait(timeout=5);fd.close();await reg.close()


if __name__=='__main__':
    reg=argparse.ArgumentParser();reg.add_argument('--php',default='php');asyncio.run(main(reg.parse_args().php))
