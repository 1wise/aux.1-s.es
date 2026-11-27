# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Check Alpine trust boundaries, exported plans and published SEO consistency."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from auxlib import alpine, branding, profiles, setup, software

class AlpineMetadataTests(unittest.TestCase):
    def test_native_manifest_and_new_root_keep_signed_apk(self):
        nat=software.defecto('alpine');nat['groups']=['desktop','network']
        cmd=setup.comandos_base('alpine',Path('/tmp/aux-alpine-test'),True,['base'], 'edge',nat)[0]
        self.assertEqual(cmd[0],'apk');self.assertIn('--initdb',cmd)
        self.assertIn('xfce4',cmd);self.assertIn('iproute2',cmd)
        self.assertNotIn('--allow-untrusted',cmd)
        self.assertEqual(cmd.count('--repository'),2)
        act=setup.comandos_base('alpine',Path('/'),False,['base'],'edge',nat)[0]
        self.assertNotIn('--repository',act);self.assertNotIn('--root',act)
        with self.assertRaises(ValueError):setup.comandos_base('alpine',Path('/'),True,['base'],'edge')
        with self.assertRaises(ValueError):alpine.repositorios('edge;reboot')
        nat['environment']='unknown'
        with self.assertRaises(ValueError):software.resuelve('alpine',nat)

    def test_generated_profile_is_inert_without_apply_and_checks_media_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp);profiles.genera('alpine',['base','network'],dst,build_id='a'*32,native=software.defecto('alpine'))
            arc=dst/'apply-alpine.sh';txt=arc.read_text()
            self.assertLess(txt.index('sha256sum -c'),txt.index('apk add'))
            self.assertNotIn('--allow-untrusted',txt)
            subprocess.run(['sh','-n',str(arc)],check=True)
            res=subprocess.run(['sh',str(arc)],text=True,capture_output=True,check=True)
            self.assertIn('--apply',res.stdout)
            self.assertEqual(json.loads((dst/'selection.json').read_text())['repository_check'],'not-run')

    def test_missing_trusted_keys_does_not_create_a_root(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(Path,'glob',return_value=iter([])):
            dst=Path(tmp)/'target'
            with self.assertRaises(ValueError):alpine.prepara_raiz(dst,'edge')
            self.assertFalse(dst.exists())

    def test_registry_and_repeat_application_have_one_canonical_and_description(self):
        dat=branding.registro()
        self.assertEqual(len(dat['architecture']['target_os']),3)
        self.assertIn('Alpine',dat['structured_data_json_ld']['@graph'][0]['operatingSystem'])
        txt='<html><head><title>AUX</title><meta name="description" content="old"><link rel="canonical" href="https://old.invalid/"></head></html>'
        url='https://aux-netboot.workspace-441958.chatgpt.site/index.html'
        for _ in range(2):txt=branding.aplica_metadata(txt,'https://aux.1-s.es',url,'AUX')
        self.assertEqual(txt.count('rel="canonical"'),1)
        self.assertEqual(txt.count('name="description"'),1)
        self.assertEqual(txt.count('data-aux-seo'),1)
        self.assertIn('href="https://aux.1-s.es/"',txt)
        self.assertIn('content="1254"',txt)
        self.assertIn('notranslate, noimageindex',txt)

if __name__=='__main__':unittest.main()
