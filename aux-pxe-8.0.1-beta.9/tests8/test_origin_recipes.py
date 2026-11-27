# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Check local-media menu reachability independently of a login test."""
import re
import unittest
from auxlib.catalog_v8 import carga
from auxlib.origin_recipes import menus, plantilla


class OriginRecipes(unittest.TestCase):
    def test_origin_profiles_have_only_intended_boot_actions(self):
        rows = [r for r in carga()['entries'] if r['id'].startswith('origin-') and
                r.get('provenance', {}).get('document_url','').endswith('1Lj_fzO0wjBFwfUUX6eBEQOo_22RSs8F5qojEGDoiDYY')]
        self.assertEqual(len(rows), 11)
        self.assertEqual(sum(bool(plantilla(r)) for r in rows), 9)
        for r in rows:
            self.assertEqual(r['policy'], '004')
            self.assertTrue(r['remote_only'])
            self.assertFalse(r['resolved'])
            self.assertEqual(r['verification']['uefi_boot'], 'not-tested')
        scripts = menus({'entries':rows})
        for script in scripts.values():
            labels = re.findall(r'^:([\w-]+)$', script, re.M)
            self.assertEqual(len(labels), len(set(labels)))
            for target in re.findall(r'\bgoto ([\w-]+)', script):
                self.assertIn(target, labels)
            for item in re.findall(r'\bitem ([\w-]+) ', script):
                self.assertIn(item, labels)
        self.assertEqual(menus({'entries':[]}), {})
        only = menus({'entries':[{'id':'origin-winserv-2025'}]})
        self.assertEqual(set(only), {'sub_win'})
        self.assertNotIn('item win11-26h2', only['sub_win'])
        self.assertFalse(plantilla({'id':'origin-macos-27-goldengate'}))
        self.assertFalse(plantilla({'id':'origin-mist-cli-2.3'}))
