#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author and Credits: https://www.alawise.es/1-s
"""Validate the complete release and exercise its independently extracted recipe and installer."""
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

DIR_APP = Path(__file__).resolve().parent
VERSION = '6.4.0-dev.1'
ARC_SUITE = DIR_APP / 'dist/downloads' / ('aux-suite-' + VERSION + '.zip')


class Suite(unittest.TestCase):
    def setUp(self):
        self.arc = zipfile.ZipFile(ARC_SUITE)
        self.addCleanup(self.arc.close)

    def componente(self, nom):
        return zipfile.ZipFile(io.BytesIO(self.arc.read(nom)))

    def test_complete_suite_has_unique_entries_and_valid_checksums(self):
        self.assertIsNone(self.arc.testzip())
        self.assertEqual(len(self.arc.namelist()), len(set(self.arc.namelist())))
        self.assertEqual(self.arc.read('README.md'), (DIR_APP / 'packaging/README-SUITE.md').read_bytes())
        for lin in self.arc.read('SHA256SUMS').decode().splitlines():
            suma, nom = lin.split('  ', 1)
            self.assertEqual(hashlib.sha256(self.arc.read(nom)).hexdigest(), suma, nom)
        for nom in ('aux-pxe-', 'tec-platform-', 'aux-cli-', 'aux-assist-', 'aux-portable-'):
            self.assertEqual(len([arc for arc in self.arc.namelist() if arc.startswith(nom) and arc.endswith('.zip')]), 1)
        for nom in (arc for arc in self.arc.namelist() if arc.endswith('.zip')):
            with self.componente(nom) as cmp:
                self.assertIsNone(cmp.testzip(), nom)
                self.assertEqual(len(cmp.namelist()), len(set(cmp.namelist())), nom)
                if nom.startswith('aux-pxe-'):
                    self.assertEqual(cmp.read('README.md'),
                                     (DIR_APP / 'packaging/README-AUX-PXE.md').read_bytes())

    def test_tec_workspace_and_assets_match_the_verified_sources(self):
        with self.componente('tec-platform-' + VERSION + '.zip') as cmp:
            for nom in ('web/cli.php', 'web/cli.js', 'web/terminal.php', 'web/terminal.js',
                        'web/terminal.css', 'web/cases.php', 'web/vendor/xterm.js', 'web/vendor/xterm.css',
                        'web/vendor/xterm-LICENSE.txt', 'test_terminal_ui.cjs', 'test_registry_web.py'):
                self.assertEqual(cmp.read(nom), (DIR_APP / 'tec' / nom).read_bytes(), nom)
            self.assertIn('6.4.0-dev.1', cmp.read('web/lib.php').decode())

    def test_gateway_and_portable_shell_selector_match(self):
        with self.componente('aux-cli-' + VERSION + '.zip') as cmp:
            for nom in ('server.py', 'history.py', 'requirements.txt', 'test_cli.py'):
                self.assertEqual(cmp.read(nom), (DIR_APP / 'cli' / nom).read_bytes(), nom)
        with self.componente('aux-portable-' + VERSION + '-kit.zip') as cmp:
            for nom in ('assist.py', 'agent.py', 'remote-shell.sh'):
                self.assertEqual(cmp.read('live-patch/' + nom),
                                 (DIR_APP / 'iso-assist/payload' / nom).read_bytes(), nom)

    def test_standalone_iso_sources_generate_the_current_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)
            with self.componente('aux-assist-' + VERSION + '-sources.zip') as cmp:
                cmp.extractall(pth / 'sources')
            res = subprocess.run([sys.executable, 'prepare.py', '--output', str(pth / 'recipe'),
                                  '--config', 'fast-boot.json.example'], cwd=pth / 'sources',
                                 check=True, capture_output=True, text=True)
            self.assertIn('Prepared', res.stdout)
            self.assertEqual(json.loads((pth / 'recipe/source-manifest.json').read_text())['version'], VERSION)
            txt = (pth / 'recipe/assist.ks').read_text()
            payload = txt.split("base64.b64decode('", 1)[1].split("')", 1)[0]
            dat = {ent['path']: base64.b64decode(ent['data']) for ent in json.loads(base64.b64decode(payload))}
            for nom in ('network_setup.py', 'remote-shell.sh', 'assist.py', 'agent.py'):
                self.assertEqual(dat['/usr/share/aux-assist/' + nom],
                                 (DIR_APP / 'iso-assist/payload' / nom).read_bytes(), nom)

    def test_extracted_installer_plan_uses_all_current_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)
            self.arc.extractall(pth)
            res = subprocess.run([sys.executable, 'install-web.py'], cwd=pth,
                                 check=True, capture_output=True, text=True)
            self.assertIn('AUX ' + VERSION, res.stdout)
            self.assertIn('plan;', res.stdout)
            self.assertIn('INSTALL-6.4.md', res.stdout)
            self.assertFalse((pth / 'web').exists())


if __name__ == '__main__':
    unittest.main()
