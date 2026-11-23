# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Exercise explicit inventory activation, password SSH and mapped FTP fallback."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from auxlib import bastion_status as bastion, checkstatus as status
from auxlib import mirror_transport as net, settings, catalog_v8 as catalog, resource_board


class BastionConnection(unittest.TestCase):
    def setUp(self):
        self.cfg={'base_url':'https://aux.example.test','ftp_host':'ftp.example.test','ftp_user':'account',
            'ftp_root':'/site','ftp_tls':True,'targets':{'bastion':{'base_url':'https://b.example.test'}},
            'mirror':{'ssh_host':'ssh.example.test','ssh_user':'account','remote_root':'/home/account/www','ssh_auth':'auto'},
            'checkstatus':{'bastion':{'enabled':False,'transport':'ftps','directories':[{'path':'/','public_url':'https://b.example.test'}]}}}
        self.sec={'ftp_password':'test-private-password'}
    def enabled(self,mode='rsync'):
        return bastion.activa(self.cfg,mode)
    def test_disabled_configuration_makes_no_attempt_and_explains_b_key(self):
        with patch.object(status,'inventario_ftp') as ftp,patch.object(status,'inventario_rsync') as rsync,patch.object(status,'lee_secretos') as secrets:
            result=status.remoto(self.cfg)
        self.assertEqual(result['status'],'disabled');self.assertIn('B en el tablero',result['reason'])
        for fn in (ftp,rsync,secrets):fn.assert_not_called()
    def test_quick_activation_reuses_ftp_root_and_preserves_original_settings(self):
        original=copy.deepcopy(self.cfg);cfg=self.enabled('ftps')
        self.assertEqual(self.cfg,original)
        est=cfg['checkstatus']['bastion'];self.assertTrue(est['enabled'])
        self.assertEqual(est['directories'],[{'path':'/site','public_url':'https://b.example.test'}])
        self.assertEqual(cfg['mirror'],original['mirror'])
    def test_quick_rsync_activation_records_the_distinct_ftp_namespace(self):
        cfg=self.enabled();ent=cfg['checkstatus']['bastion']['directories'][0]
        self.assertEqual((ent['path'],ent['ftp_path']),('/home/account/www','/site'))
    def test_incomplete_connections_cannot_be_activated(self):
        for key in ('ftp_host','ftp_user'):
            cfg={**self.cfg,key:None}
            with self.subTest(key=key),self.assertRaises(ValueError):bastion.activa(cfg,'ftps')
    def test_auto_ssh_can_ask_for_a_password_in_terminal(self):
        with patch.object(net.sys.stdin,'isatty',return_value=True):cmd,host=net.ssh_args(self.cfg)
        self.assertIn('BatchMode=no',cmd);self.assertIn('StrictHostKeyChecking=yes',cmd)
        self.assertEqual(host,'account@ssh.example.test');self.assertNotIn(self.sec['ftp_password'],' '.join(cmd))
    def test_password_mode_needs_no_identity_file(self):
        cfg=copy.deepcopy(self.cfg);cfg['mirror']['ssh_auth']='password'
        with patch.object(net.sys.stdin,'isatty',return_value=True):cmd,_=net.ssh_args(cfg)
        self.assertIn('PubkeyAuthentication=no',cmd);self.assertIn('BatchMode=no',cmd);self.assertNotIn('-i',cmd)
    def test_password_mode_without_terminal_fails_with_actionable_message(self):
        cfg=copy.deepcopy(self.cfg);cfg['mirror']['ssh_auth']='password'
        with patch.object(net.sys.stdin,'isatty',return_value=False),self.assertRaisesRegex(ValueError,'FTPS'):net.ssh_args(cfg)
    def test_key_mode_and_nonterminal_auto_keep_batch_mode(self):
        for mode,tty in [('key',True),('auto',False)]:
            cfg=copy.deepcopy(self.cfg);cfg['mirror']['ssh_auth']=mode
            with self.subTest(mode=mode),patch.object(net.sys.stdin,'isatty',return_value=tty):cmd,_=net.ssh_args(cfg)
            self.assertIn('BatchMode=yes',cmd);self.assertIn('StrictHostKeyChecking=yes',cmd)
    def test_rsync_success_does_not_read_ftp_credentials_or_try_ftp(self):
        with patch.object(status,'inventario_rsync',return_value=[{'relative':'file.iso','size':12}]),patch.object(status,'inventario_ftp') as ftp,patch.object(status,'lee_secretos') as secrets:
            result=status.remoto(self.enabled())
        self.assertEqual(result['status'],'observed');ftp.assert_not_called();secrets.assert_not_called()
    def test_rsync_failure_uses_ftps_credentials_and_mapped_root(self):
        with patch.object(status,'inventario_rsync',side_effect=ValueError('SSH unavailable')),patch.object(status,'lee_secretos',return_value=self.sec),patch.object(status,'inventario_ftp',return_value=[{'relative':'images/file.iso','size':12}]) as ftp:
            result=status.remoto(self.enabled())
        self.assertEqual(result['status'],'observed');self.assertEqual(result['errors'],[])
        self.assertEqual(ftp.call_args.args[1],'/site');self.assertTrue(ftp.call_args.args[0]['ftp_tls'])
        self.assertEqual(ftp.call_args.args[3],self.sec)
        self.assertEqual(result['files'][0]['public_url'],'https://b.example.test/images/file.iso')
        self.assertEqual([e['status'] for e in result['attempts']],['error','ok'])
        self.assertNotIn(self.sec['ftp_password'],json.dumps(result))
    def test_unmapped_ssh_root_cannot_be_reused_as_ftp_path(self):
        cfg=self.enabled();cfg['checkstatus']['bastion']['directories']=[{'path':'/other/tree','public_url':'https://b.example.test'}]
        with patch.object(status,'inventario_rsync',side_effect=ValueError('SSH unavailable')),patch.object(status,'inventario_ftp') as ftp:
            result=status.remoto(cfg)
        self.assertEqual(result['status'],'error');ftp.assert_not_called();self.assertIn('ftp_path',result['errors'][0]['error'])
    def test_configured_root_mapping_covers_nested_directories(self):
        ent={'path':'/home/account/www/isos'}
        self.assertEqual(status._ruta_ftp(self.cfg,ent),'/site/isos')
    def test_explicitly_disabled_fallback_is_respected(self):
        cfg=self.enabled();cfg['checkstatus']['bastion']['fallback_ftp']=False
        with patch.object(status,'inventario_rsync',side_effect=ValueError('SSH unavailable')),patch.object(status,'inventario_ftp') as ftp:
            result=status.remoto(cfg)
        ftp.assert_not_called();self.assertEqual(result['status'],'error')
    def test_failed_ftps_does_not_downgrade_tls_or_certify_empty_inventory(self):
        with patch.object(status,'inventario_rsync',side_effect=ValueError('SSH unavailable')),patch.object(status,'lee_secretos',return_value=self.sec),patch.object(status,'inventario_ftp',side_effect=ValueError('certificate failed')) as ftp:
            result=status.remoto(self.enabled())
        self.assertEqual(ftp.call_count,1);self.assertTrue(ftp.call_args.args[0]['ftp_tls'])
        self.assertEqual(result['status'],'error');self.assertEqual(result['files'],[])
    def test_enabled_inventory_with_no_directories_is_error(self):
        cfg=self.enabled();cfg['checkstatus']['bastion']['directories']=[]
        self.assertEqual(status.remoto(cfg)['status'],'error')
    def test_inventory_settings_validate_auth_and_optional_ftp_path(self):
        self.assertEqual(settings.convierte('mirror.ssh_auth','password'),'password')
        self.assertEqual(settings.convierte('checkstatus.bastion.transport','auto'),'auto')
        self.assertEqual(settings.convierte('checkstatus.bastion.transport','ftp'),'ftp')
        val=[{'path':'/home/www','ftp_path':'/site','public_url':'https://b.example.test'}]
        self.assertEqual(settings.convierte('checkstatus.bastion.directories',json.dumps(val)),val)
        val[0]['ftp_path']='/../secret'
        with self.assertRaises(ValueError):settings.convierte('checkstatus.bastion.directories',json.dumps(val))
    def test_board_exposes_bastion_action(self):
        self.assertEqual(resource_board.TAREAS['b'],'bastion')
        self.assertIn('desactivado',bastion.resumen(self.cfg))
    def test_board_setup_saves_activation_using_the_existing_ftp_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            arc=Path(tmp)/'config.json';arc.write_text(json.dumps(self.cfg))
            with patch('auxlib.interactive.elige',side_effect=['ftp','back']),patch('auxlib.console_ui.campo',return_value='APLICAR'):
                bastion.configura(arc)
            cfg=json.loads(arc.read_text());est=cfg['checkstatus']['bastion']
            self.assertTrue(est['enabled']);self.assertEqual(est['transport'],'ftps')
            self.assertEqual(est['directories'][0]['path'],'/site');self.assertEqual(cfg['ftp_user'],self.cfg['ftp_user'])
            self.assertNotIn(self.sec['ftp_password'],arc.read_text())
    def test_board_setup_leaves_settings_unchanged_when_not_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            arc=Path(tmp)/'config.json';arc.write_text(json.dumps(self.cfg));original=arc.read_bytes()
            with patch('auxlib.interactive.elige',side_effect=['ftp','back']),patch('auxlib.console_ui.campo',return_value=''):
                bastion.configura(arc)
            self.assertEqual(arc.read_bytes(),original)
    def test_cli_one_run_override_keeps_config_digest_and_saved_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg={**self.cfg,'output':str(root/'web'),'cache':str(root/'cache'),'ram_dir':str(root/'ram'),
                'catalog_file':str(root/'catalog.json'),'status_file':str(root/'status.json')}
            catalog.guarda(cfg['catalog_file'],{'schema':catalog.SCHEMA,'entries':[]})
            arc=root/'config.json';arc.write_text(json.dumps(cfg));original=arc.read_bytes()
            with patch.object(status,'lee_secretos',return_value=self.sec),patch.object(status,'inventario_ftp',return_value=[{'relative':'image.iso','size':12}]) as ftp,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(status.main(['--config',str(arc),'--bastion','ftps']),0)
            self.assertEqual(ftp.call_args.args[1],'/site');self.assertEqual(arc.read_bytes(),original)
            snap=json.loads((root/'status.json').read_text())
            self.assertEqual(snap['configuration_sha256'],status.config_digest(cfg))
            self.assertTrue(status.vigente(snap,catalog.carga(cfg['catalog_file']),cfg))
    def test_cli_dry_run_override_stays_offline_and_does_not_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg={**self.cfg,'catalog_file':str(root/'catalog.json'),'status_file':str(root/'status.json')}
            catalog.guarda(cfg['catalog_file'],{'schema':catalog.SCHEMA,'entries':[]})
            arc=root/'config.json';arc.write_text(json.dumps(cfg))
            with patch.object(status,'remoto') as remote,contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(status.main(['--config',str(arc),'--bastion','ftps','--dry-run']),0)
            remote.assert_not_called();self.assertFalse((root/'status.json').exists())


if __name__=='__main__':unittest.main()
