#!/usr/bin/env python3
# Timestamp: 2026-10-16 | Version: 6.0.0-dev.3
# Author & Credits: https://www.alawise.es/1-s
"""Verify the release-specific operational contracts using real command processes."""
import contextlib
import http.server
import io
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import threading
from types import ModuleType
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
import common


def module(nom):
    arc = ROOT / (nom + '.sh')
    eng = ModuleType('v6_' + nom);eng.__file__ = str(arc)
    txt = arc.read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
    exec(compile(txt, str(arc), 'exec'), eng.__dict__)
    return eng


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aux-v6-')
        self.pth = Path(self.tmp.name)
        self.arc = self.pth / 'config.json'
        self.cfg_dat = json.loads((ROOT / 'fast-boot.json').read_text())
        self.cfg_dat.update(output=str(self.pth / 'html'), cache=str(self.pth / 'cache'))
        self.cfg_dat['tec']['web_dir'] = str(ROOT / 'tec/web')
        self.write()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.arc.write_text(json.dumps(self.cfg_dat))

    def args(self, *flags):
        with patch('sys.argv', ['generate.sh', '--config', str(self.arc), *flags]):
            return common.obt_args('generate', ROOT)

    def test_user_primary_group_and_old_flag_error(self):
        cfg = self.args('--user', str(os.geteuid()))
        self.assertEqual(cfg.gid_pub, pwd.getpwuid(os.geteuid()).pw_gid)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as err:
            self.args('--owner', 'root')
        self.assertEqual(err.exception.code, 2)

    def test_public_ai_config_rejects_credentials_before_generation(self):
        for dat in [{'api_key': 'fixture'}, {'openai': {'model': 'ok', 'key': 'fixture'}},
                    {'enabled': 'false'}, {'gemini': {'model': '../elsewhere'}},
                    {'timeout_seconds': False}]:
            self.cfg_dat['ai'] = dat
            self.write()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.args()

    def test_new_assistance_names_enter_chapter_zero_without_marking_boot_verified(self):
        rec = common.obt_meta('https://example.test/aux-assist-6.0.0-dev.3-final-x86_64.iso')
        self.assertEqual(rec['category'], 'assistance')
        self.assertFalse(rec['pxe_ready'])
        self.assertFalse(rec['published'])

    def test_tec_auto_off_on_and_bastion_profile(self):
        self.assertTrue(self.args('--target', 'bastion').tec_enabled)
        self.assertFalse(self.args('--tec', 'off').tec_enabled)
        self.cfg_dat['tec']['web_dir'] = str(self.pth / 'missing')
        self.write()
        self.assertFalse(self.args().tec_enabled)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.args('--tec', 'on')
        cfg = self.args('--target', 'bastion')
        self.assertEqual(cfg.base_url, 'https://b.1-s.es')
        self.assertEqual(cfg.pxe_url, 'http://p.1-s.es')
        self.assertEqual(cfg.tec['public_url'], 'https://t.1-s.es')

    def test_generated_tec_links_disappear_but_work_remains_exact(self):
        eng = module('generate');eng.carga_recursos()
        cfg = self.args('--tec', 'off', '--target', 'bastion')
        eng.gen_pages([], cfg, state='synced')
        for nom in ['index.html', 'cli.html', 'cli-all.html']:
            txt = (cfg.output / nom).read_text()
            self.assertNotIn('href="https://t.1-s.es', txt)
        self.assertEqual((cfg.output / 'downloads/work.py').read_bytes(), (ROOT / 'iso/payload/work.py').read_bytes())
        self.assertIn('RewriteCond', (cfg.output / '.htaccess').read_text())
        self.assertFalse(json.loads((cfg.output / 'catalog.json').read_text())['tec_enabled'])

    def test_quiet_download_lists_every_failure_and_keeps_private_log(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self): self.send_error(404)
            def log_message(self, *_): pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        urls = self.pth / 'url.txt'
        urls.write_text(''.join(f'http://127.0.0.1:{server.server_port}/{nom}.iso\n' for nom in ['missing-one', 'missing-two']))
        try:
            rsp = subprocess.run(['bash', str(ROOT / 'download.sh'), '--config', str(self.arc),
                '--url-file', str(urls), '--quiet'], capture_output=True, text=True)
            self.assertEqual(rsp.returncode, 1)
            self.assertIn('2 failed', rsp.stdout)
            for nom in ['missing-one.iso', 'missing-two.iso']:
                self.assertIn('FAIL: ' + nom, rsp.stderr)
            logs = list((self.pth / 'cache/logs').glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].stat().st_mode & 0o777, 0o600)
            self.assertIn('404', logs[0].read_text())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_ram_budget_explicit_disk_fallback(self):
        eng = module('deploy')
        cfg = self.args();cfg.mode = 'ram';cfg.ram_dir = self.pth / 'ram'
        cfg.ram_budget_gib = .000001;cfg.quiet = True
        rec = {'filename': 'tiny.efi', 'size': 16384, 'status': 'cached', 'sha256': '0' * 64}
        with patch.object(eng, 'arc_valido', return_value=False), patch.object(eng, 'prep_disk') as disk, \
             patch.object(eng.subprocess, 'run', return_value=type('Rsp', (), {'stdout': 'tmpfs'})()):
            eng.prep_ram(rec, cfg)
        disk.assert_called_once()
        self.assertEqual(rec['deployment'], 'disk-fallback')
        self.assertEqual(disk.call_args.args[1].mode, 'extract')

    def test_release_packages_include_gateway_and_vendor(self):
        cfg = json.loads((ROOT / 'fast-boot.json').read_text())
        self.assertIn('cli', cfg)
        self.assertEqual(cfg['cli']['nodes']['excalibur']['url'], 'https://cli.1-s.es')
        with zipfile.ZipFile(ROOT / 'dist/downloads/tec-platform-6.0.0-dev.3.zip') as arc:
            for nom in ['web/cli.php', 'web/cli.js', 'web/cli-lib.php', 'web/vendor/xterm.js', 'web/vendor/xterm-LICENSE.txt']:
                self.assertIn(nom, arc.namelist())
        with zipfile.ZipFile(ROOT / 'dist/downloads/aux-assist-6.0.0-dev.3-sources.zip') as arc:
            self.assertIn('payload/agent.py', arc.namelist())
        with zipfile.ZipFile(ROOT / 'dist/downloads/aux-fast-boot.zip') as arc:
            self.assertIn('cli/server.py', arc.namelist())
            self.assertIn('ovh/shared.htaccess', arc.namelist())
            self.assertNotIn('cli-excalibur.secret', arc.namelist())


if __name__ == '__main__':
    unittest.main()
