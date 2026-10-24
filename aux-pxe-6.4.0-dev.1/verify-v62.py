#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Check release contracts and real isolated installer file operations."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('install62', ROOT / 'install-web.py')
inst = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inst)
sys.path.insert(0, str(ROOT / 'iso-assist'))
import prepare


class Release(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_renamed_service_and_payload_are_consistent(self):
        out = self.pth / 'recipe'
        prepare.render(out, pth_cfg=ROOT / 'fast-boot.json')
        txt = (out / 'assist.ks').read_text()
        raw = txt.split("base64.b64decode('",1)[1].split("')",1)[0]
        files = {e['path']:base64.b64decode(e['data']).decode() for e in json.loads(base64.b64decode(raw))}
        self.assertIn('/etc/systemd/system/aux-exec.service',files)
        self.assertIn('/usr/share/aux-assist/aux_exec.py',files)
        self.assertNotIn('aux-executor',str(files))
        self.assertIn("'4242'",txt)
        self.assertNotIn('/var/lib/aux-assist/cli-excalibur.secret',str(files))
        for uni in ('aux-gpt.service','aux-gemini.service'):
            src=files['/etc/systemd/system/'+uni]
            self.assertIn('Requires=aux-exec.service',src)
            self.assertIn('SupplementaryGroups=tty',src)
            self.assertIn('PrivateDevices=no',src)

    def test_install_configuration_enables_gateway_without_touching_original(self):
        base=json.loads((ROOT/'fast-boot.json').read_text())
        cfg=inst.configura(base,self.pth)
        self.assertTrue(cfg['cli']['enabled'])
        self.assertFalse(base['cli']['enabled'])
        self.assertEqual(cfg['_meta']['Version'],inst.VERSION)
        self.assertEqual(cfg['cli']['nodes']['excalibur']['secret_file'],
                         str(Path(cfg['tec']['data_dir'])/'cli-excalibur.secret'))
        base['tec']['data_dir']=str(self.pth/'web/private')
        with self.assertRaises(ValueError):inst.configura(base,self.pth)

    def test_secret_generation_copy_permissions_preservation_and_rejection(self):
        src,dst=self.pth/'gateway.secret',self.pth/'tec.secret'
        ent=pwd.getpwuid(os.geteuid())
        with patch.object(inst.pwd,'getpwnam',return_value=ent):
            inst.secreto_cli(src,dst)
            original=src.read_bytes()
            self.assertEqual(dst.read_bytes(),original)
            self.assertEqual(len(original.strip()),64)
            self.assertEqual(src.stat().st_mode&0o777,0o600)
            self.assertEqual(dst.stat().st_mode&0o777,0o600)
            inst.secreto_cli(src,dst)
            self.assertEqual(src.read_bytes(),original)
            src.write_bytes(b'bad')
            with self.assertRaises(ValueError):inst.secreto_cli(src,dst)
            self.assertEqual(src.read_bytes(),b'bad')
            self.assertEqual(dst.read_bytes(),original)

    def test_archive_checksum_traversal_and_symlink_guards(self):
        arc=self.pth/'source.zip'
        for nom,mode in [('good.txt',0o100644),('../escape',0o100644),('link',0o120777)]:
            with zipfile.ZipFile(arc,'w') as z:
                ent=zipfile.ZipInfo(nom);ent.external_attr=mode<<16;z.writestr(ent,'fixture')
            arc.with_suffix('.zip.sha256').write_text(hashlib.sha256(arc.read_bytes()).hexdigest()+'  source.zip\n')
            if nom=='good.txt':
                inst.extrae(arc,self.pth/'extracted')
                self.assertEqual((self.pth/'extracted/good.txt').read_text(),'fixture')
            else:
                with self.assertRaises(ValueError):inst.extrae(arc,self.pth/'extracted')
        arc.with_suffix('.zip.sha256').write_text('0'*64+'  source.zip\n')
        with self.assertRaises(ValueError):inst.extrae(arc,self.pth/'extracted')

    def test_suite_contains_independent_complete_packages(self):
        suite=ROOT/'dist/downloads'/('aux-suite-'+inst.VERSION+'.zip')
        if not suite.exists():self.skipTest('Run build.py before package verification')
        with zipfile.ZipFile(suite) as z:
            for nom in ('install-web.py','INSTALL-6.2.md','RELEASE-6.2.md'):
                self.assertIn(nom,z.namelist())
            z.extractall(self.pth/'suite')
        with inst.fuentes(self.pth/'suite') as src:
            for nom in ('tec/web/totp.php','tec/web/vendor/xterm.js','cli/server.py',
                        'iso-assist/payload/aux-exec.service','src/common.py'):
                self.assertTrue((src/nom).is_file(),nom)
            self.assertIn(inst.VERSION,(src/'tec/web/lib.php').read_text())


if __name__=='__main__':
    unittest.main()
