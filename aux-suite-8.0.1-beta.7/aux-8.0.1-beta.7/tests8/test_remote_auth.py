# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Exercise real loopback SSH password authentication and chrooted FTP/FTPS."""
import asyncio
import contextlib
import datetime
import io
import ipaddress
import json
import logging
import os
from pathlib import Path
import ssl
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from auxlib import ssh_auth,ftp_connection,mirror_transport as net,checkstatus,bastion_status,settings
try:
    import asyncssh
except ImportError:asyncssh=None
try:
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler,TLS_FTPHandler
    from pyftpdlib.servers import FTPServer
    from pyftpdlib.ioloop import IOLoop
except ImportError:FTPServer=None


class PasswordBridge(unittest.TestCase):
    def cfg(self):return {'mirror':{'ssh_host':'example.test','ssh_user':'account','ssh_auth':'password'}}
    def test_askpass_reads_password_without_storing_it_in_helper_or_environment(self):
        secret='private-test-ssh-secret'
        with patch.object(net.sys.stdin,'isatty',return_value=False),ssh_auth.autenticacion(self.cfg(),{'ssh_password':secret}) as auth:
            helper=Path(auth['run']['env']['SSH_ASKPASS']);self.assertNotIn(secret,helper.read_text())
            self.assertFalse(any(secret in str(v) for v in auth['run']['env'].values()))
            self.assertNotIn(secret,' '.join(auth['ssh']))
            result=subprocess.run([str(helper),'password:'],capture_output=True,text=True,check=True)
            self.assertEqual(result.stdout,secret+'\n');self.assertEqual(helper.stat().st_mode&0o777,0o700)
            directory=helper.parent;self.assertEqual(directory.stat().st_mode&0o777,0o700)
            self.assertEqual({p.name for p in directory.iterdir()},{'askpass','auth.pipe'})
        self.assertFalse(directory.exists())
    def test_password_prompt_is_explicit_when_not_stored(self):
        with patch.object(net.sys.stdin,'isatty',return_value=True),patch.object(ssh_auth.getpass,'getpass',return_value='temporary-test') as prompt:
            with ssh_auth.autenticacion(self.cfg(),{}) as auth:self.assertEqual(auth['secrets']['ssh_password'],'temporary-test')
        prompt.assert_called_once()
    def test_missing_password_without_terminal_names_the_secret_menu(self):
        with patch.object(net.sys.stdin,'isatty',return_value=False),self.assertRaisesRegex(ValueError,'ssh_password'):
            with ssh_auth.autenticacion(self.cfg(),{}):pass
    def test_key_mode_does_not_send_a_stored_password(self):
        cfg=self.cfg();cfg['mirror']['ssh_auth']='key'
        with ssh_auth.autenticacion(cfg,{'ssh_password':'unused-test'}) as auth:self.assertEqual(auth['run'],{})
    def test_error_classification_explains_host_key_and_redacts_passwords(self):
        text=ssh_auth.error_ssh(255,'Host key verification failed. secret',{'ssh_password':'secret'})
        self.assertIn('known_hosts',text);self.assertNotIn('secret',text)
        self.assertIn('contraseña SSH',ssh_auth.error_ssh(255,'Permission denied'))
    def test_private_pipe_is_removed_after_a_failed_operation(self):
        with self.assertRaisesRegex(ValueError,'operation failed'):
            with ssh_auth.autenticacion(self.cfg(),{'ssh_password':'temporary-test'}) as auth:
                path=Path(auth['run']['env']['SSH_ASKPASS']).parent
                raise ValueError('operation failed')
        self.assertFalse(path.exists())
    def test_bastion_menu_stores_ssh_password_and_selects_password_authentication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=root/'config.json';cfg.write_text(json.dumps(self.cfg()));private=root/'private/credentials.json'
            with patch('auxlib.interactive.elige',side_effect=['ssh_password','back']),patch.object(bastion_status.getpass,'getpass',return_value='stored-ssh-test'):
                bastion_status.configura(cfg,private)
            self.assertEqual(settings.lee_secretos(private,cfg)['ssh_password'],'stored-ssh-test')
            self.assertEqual(settings.lee_config(cfg)['mirror']['ssh_auth'],'password')
            self.assertNotIn('stored-ssh-test',cfg.read_text());self.assertEqual(private.stat().st_mode&0o777,0o600)
    def test_bastion_ftp_password_entry_keeps_ssh_password_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=root/'config.json';cfg.write_text(json.dumps(self.cfg()));private=root/'private/credentials.json'
            settings.guarda_secreto('ssh_password','different-ssh-test',private,cfg)
            with patch('auxlib.interactive.elige',side_effect=['ftp_password','back']),patch.object(bastion_status.getpass,'getpass',return_value='stored-ftp-test'):
                bastion_status.configura(cfg,private)
            self.assertEqual(settings.lee_secretos(private,cfg),{'ssh_password':'different-ssh-test','ftp_password':'stored-ftp-test'})


@unittest.skipIf(asyncssh is None,'Optional asyncssh test dependency is unavailable')
class RealSSH(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.received=[];received=self.received
        class Server(asyncssh.SSHServer):
            def begin_auth(self,username):return True
            def password_auth_supported(self):return True
            def validate_password(self,username,password):received.append(password);return username=='account' and password=='loopback-secret'
        def process(proc):
            if proc.command=='printf AUX_SSH_OK':proc.stdout.write('AUX_SSH_OK');proc.exit(0)
            else:proc.exit(1)
        key=asyncssh.generate_private_key('ssh-ed25519')
        self.server=await asyncssh.create_server(Server,'127.0.0.1',0,server_host_keys=[key],process_factory=process)
        port=self.server.get_port();known=self.root/'known_hosts';known.write_text('[127.0.0.1]:'+str(port)+' '+key.export_public_key().decode())
        self.cfg={'mirror':{'ssh_host':'127.0.0.1','ssh_user':'account','ssh_port':port,'ssh_auth':'password','ssh_known_hosts':str(known)}}
        # Isolate the test client from executor-owned system SSH configuration.
        original=net.ssh_args
        def isolated(*args,**kwargs):
            cmd,host=original(*args,**kwargs);return cmd+['-F','/dev/null'],host
        self.isolate=patch.object(net,'ssh_args',side_effect=isolated);self.isolate.start();self.addCleanup(self.isolate.stop)
    async def asyncTearDown(self):
        self.server.close();await self.server.wait_closed()
    async def test_real_openssh_authenticates_without_a_terminal(self):
        with patch.object(net.sys.stdin,'isatty',return_value=False):
            result=await asyncio.to_thread(ssh_auth.prueba,self.cfg,{'ssh_password':'loopback-secret'})
        self.assertIn('correctos',result[0]);self.assertEqual(self.received,['loopback-secret'])
    async def test_real_wrong_password_reports_authentication_failure(self):
        with self.assertRaisesRegex(ValueError,'autenticación rechazada'):
            await asyncio.to_thread(ssh_auth.prueba,self.cfg,{'ssh_password':'wrong-test-password'})
    async def test_untrusted_host_is_rejected_before_password_is_sent(self):
        Path(self.cfg['mirror']['ssh_known_hosts']).write_text('')
        with self.assertRaisesRegex(ValueError,'known_hosts'):
            await asyncio.to_thread(ssh_auth.prueba,self.cfg,{'ssh_password':'loopback-secret'})
        self.assertEqual(self.received,[])


@unittest.skipIf(FTPServer is None,'Optional pyftpdlib TLS test dependency is unavailable')
class RealFTP(unittest.TestCase):
    def setUp(self):
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes,serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'bastion').mkdir();(self.root/'bastion/image.iso').write_bytes(b'image-bytes')
        key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'localhost')]);now=datetime.datetime.now(datetime.timezone.utc)
        cert=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(1).not_valid_before(now-datetime.timedelta(days=1)).not_valid_after(now+datetime.timedelta(days=1)).add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),critical=False).sign(key,hashes.SHA256())
        self.cert=self.root/'cert.pem';self.cert.write_bytes(cert.public_bytes(serialization.Encoding.PEM));private=self.root/'key.pem';private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.TraditionalOpenSSL,serialization.NoEncryption()));private.chmod(0o600)
        authorizer=DummyAuthorizer();authorizer.add_user('account','ftp-test-secret',str(self.root),perm='elr')
        class Handler(TLS_FTPHandler):pass
        Handler.authorizer=authorizer;Handler.certfile=str(self.cert);Handler.keyfile=str(private);Handler.auth_failed_timeout=0
        logging.getLogger('pyftpdlib').setLevel(logging.CRITICAL)
        self.loop=IOLoop();self.server=FTPServer(('127.0.0.1',0),Handler,ioloop=self.loop)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'timeout':.05,'handle_exit':False},daemon=True);self.thread.start()
        self.cfg={'ftp_host':'127.0.0.1','ftp_user':'account','ftp_port':self.server.socket.getsockname()[1],
            'ftp_root':'/bastion','ftp_tls':True,'base_url':'https://aux.example.test',
            'mirror':{'transport':'rsync','remote_root':'/home/wiseesx/bastion'},
            'checkstatus':{'bastion':{'transport':'rsync','directories':[{'path':'/home/wiseesx/bastion','ftp_path':'/home/wiseesx/bastion','public_url':'https://b.example.test'}]}}}
        self.sec={'ftp_password':'ftp-test-secret'}
        ctx=ssl.create_default_context(cafile=str(self.cert));self.trust=patch.object(ftp_connection.ssl,'create_default_context',return_value=ctx)
        self.trust.start();self.addCleanup(self.trust.stop);self.addCleanup(self.stop)
    def stop(self):self.server.close_all();self.thread.join(timeout=2);self.loop.close()
    def test_real_ftps_login_listing_and_metadata_inventory(self):
        result=ftp_connection.prueba(self.cfg,self.sec)
        self.assertEqual(result['login_directory'],'/');self.assertIn('bastion',result['directories']);self.assertEqual(result['root_status'],'ok')
        rows=checkstatus.inventario_ftp(self.cfg,'/bastion',{'timeout_seconds':2,'max_files':10,'max_depth':4},self.sec)
        self.assertEqual(rows,[{'relative':'image.iso','size':11}])
    def test_actual_ssh_path_is_rejected_with_the_ftp_login_directory(self):
        with self.assertRaisesRegex(ValueError,r'\[directorio\].*PWD tras login /'):
            ftp_connection.abre(self.cfg,self.sec,'/home/wiseesx/bastion')
    def test_wrong_ftp_password_is_identified_as_login_failure(self):
        with self.assertRaisesRegex(ValueError,r'\[login\].*530'):
            ftp_connection.abre(self.cfg,{'ftp_password':'wrong-test'})
    def test_ftp_connection_uses_ftp_root_even_with_rsync_selected(self):
        conn=net.conecta_ftp(self.cfg,self.sec)
        try:self.assertEqual(conn.pwd(),'/bastion')
        finally:conn.close()
    def test_browser_selects_real_ftp_root_and_repairs_fallback_mapping(self):
        cfg=self.root/'config.json';cfg.write_text(json.dumps(self.cfg));private=self.root/'private/credentials.json'
        settings.guarda_secreto('ftp_password',self.sec['ftp_password'],private,cfg)
        with patch('auxlib.interactive.elige',side_effect=[('dir','bastion'),'use']),patch('auxlib.console_ui.campo',return_value='APLICAR'):
            bastion_status.explora_ftp(cfg,private)
        saved=json.loads(cfg.read_text());self.assertEqual(saved['ftp_root'],'/bastion')
        self.assertEqual(saved['checkstatus']['bastion']['directories'][0]['ftp_path'],'/bastion')
    def test_untrusted_ftps_certificate_fails_without_plaintext_downgrade(self):
        self.trust.stop()
        with self.assertRaisesRegex(ValueError,r'\[TLS\]'):
            ftp_connection.abre(self.cfg,self.sec)
    def test_probe_distinguishes_successful_login_from_wrong_root(self):
        cfg={**self.cfg,'ftp_root':'/home/wiseesx/bastion'}
        result=ftp_connection.prueba(cfg,self.sec)
        self.assertEqual(result['login_directory'],'/');self.assertEqual(result['root_status'],'error');self.assertIn('bastion',result['directories'])


if __name__=='__main__':unittest.main()
