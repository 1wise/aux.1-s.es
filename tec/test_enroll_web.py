#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Exercise the real PHP enrollment page with isolated sessions and fake HTTPS metadata."""
import argparse
import base64
import hashlib
import hmac
import http.client
import json
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import tempfile
import time
from urllib.parse import urlencode


def main():
    par=argparse.ArgumentParser()
    par.add_argument('--php',default='php')
    args=par.parse_args()
    root=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='aux-totp-web-') as tmp:
        pth=Path(tmp);(pth/'sessions').mkdir();(pth/'private').mkdir()
        env=os.environ|{'AUX_ASSIST_DATA_DIR':str(pth/'private'),'AUX_TEST_WEB':str(root/'web')}
        init=pth/'fixture.php'
        init.write_text('''<?php
define('AUX_ASSIST_ENTRY',true);require getenv('AUX_TEST_WEB').'/lib.php';
$usr=['id'=>'usr_fixture','correo'=>'fixture@example.test','nombre'=>'Fixture','estado'=>'activo',
      'email_confirmado'=>true,'password_hash'=>password_hash('fixture-password-long',PASSWORD_DEFAULT)];
$tec=['id'=>'tec_fixture','usuario_id'=>$usr['id'],'correo'=>$usr['correo'],'nombre'=>'Fixture',
      'estado'=>'activo','email_confirmado'=>true];
datos(function(&$dat)use($usr,$tec){$dat['usuarios']=[$usr];$dat['tecnicos']=[$tec];},true);
session_name('tec_assist');session_id('fixture-session-62');session_start();
$_SESSION=['usuario'=>$usr['id'],'csrf'=>'fixture-csrf'];session_write_close();
''')
        php=[args.php,'-d','session.save_path='+str(pth/'sessions')]
        subprocess.run(php+[str(init)],env=env,check=True,capture_output=True)
        router=pth/'router.php'
        router.write_text("<?php $_SERVER['HTTPS']='on'; require getenv('AUX_TEST_WEB').'/totp.php';")
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        log=(pth/'server.log').open('w+')
        proc=subprocess.Popen(php+['-S','127.0.0.1:'+str(port),str(router)],env=env,stdout=log,stderr=log)
        def request(data=None,authenticated=True):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=5)
            headers={'Content-Type':'application/x-www-form-urlencoded'}
            if authenticated:headers['Cookie']='tec_assist=fixture-session-62'
            conn.request('POST' if data is not None else 'GET','/totp.php',
                         urlencode(data) if data is not None else None,headers)
            rsp=conn.getresponse();result=rsp.status,dict(rsp.getheaders()),rsp.read().decode()
            conn.close();return result
        def post(**data):return request({'csrf':'fixture-csrf',**data})
        try:
            for _ in range(100):
                try:request();break
                except OSError:
                    if proc.poll() is not None:raise RuntimeError('PHP test server did not start')
                    time.sleep(.03)
            else:raise RuntimeError('PHP test server timeout')
            assert '<code>' not in request(authenticated=False)[2]
            assert 'Contraseña' in request()[2]
            bad=request({'csrf':'wrong','action':'begin','password':'fixture-password-long'})
            assert 'Formulario caducado' in bad[2] and '<code>' not in bad[2]
            bad=post(action='begin',password='incorrect')
            assert 'incorrecta' in bad[2] and '<code>' not in bad[2]
            assert post(action='begin',password='fixture-password-long')[0]==303
            page=request()[2]
            seed=re.search(r'<code>([A-Z2-7]{32})</code>',page)[1]
            assert '30 segundos' in page and 'SHA-1' in page
            assert 'totp_seed' not in json.loads((pth/'private/tecnicos.json').read_text())[0]
            mac=hmac.new(base64.b32decode(seed),struct.pack('>Q',int(time.time())//30),hashlib.sha1).digest()
            off=mac[-1]&15
            code=str((struct.unpack('>I',mac[off:off+4])[0]&0x7fffffff)%1000000).zfill(6)
            result=post(action='confirm',code=code)
            assert result[0]==303 and result[1]['Location']=='cli.php'
            assert '<code>' not in request()[2]
            stored=json.loads((pth/'private/tecnicos.json').read_text())[0]
            assert stored['totp_seed']==seed and stored['totp_step']>0
            # The administrative CLI must not silently rotate an existing factor.
            cmd=[args.php,str(root/'manage.php'),'totp','tec_fixture']
            assert subprocess.run(cmd,env=env,capture_output=True).returncode==1
            subprocess.run([args.php,str(root/'manage.php'),'totp-reset','tec_fixture'],env=env,check=True,capture_output=True)
            assert 'totp_seed' not in json.loads((pth/'private/tecnicos.json').read_text())[0]
            assert 'Contraseña' in request()[2]
            print('PASS: real PHP page, session, CSRF, password, pending seed, code, redirect, existing-factor guard and reset')
        finally:
            proc.terminate();proc.wait(timeout=5);log.close()


if __name__=='__main__':main()
