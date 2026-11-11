# Timestamp: 2026-11-09 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Check native choices survive export and reach the real package-manager plan."""
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

from auxlib import interactive, profiles, setup, software, webapps


class SoftwareNativo(unittest.TestCase):
    def test_snapshots_complete_and_all_references_known(self):
        deb = software.carga('debian')
        fed = software.carga('fedora')
        self.assertEqual(len(deb['groups']), 230)
        self.assertEqual(len(fed['groups']), 155)
        self.assertEqual(len(fed['environments']), 20)
        for ent in fed['environments']:
            nat = {'catalog_sha256':fed['digest_sha256'], 'environment':ent['id'], 'groups':ent['default']}
            dat = software.resuelve('fedora', nat)
            self.assertTrue(set(ent['required']).issubset(dat['groups']))

    def test_debian_subtask_preserves_native_parent(self):
        nat = software.defecto('debian')
        nat['tasks'] = ['xfce-desktop']
        dat = profiles.seleccion('debian', ['base'], nat)
        self.assertEqual(dat['native']['tasks'], ['xfce-desktop', 'desktop'])
        self.assertIn('task-xfce-desktop', dat['packages'])
        self.assertIn('task-desktop', dat['packages'])

    def test_standard_is_priority_packages_not_invented_metapackage(self):
        nat = software.defecto('debian')
        nat['tasks'] = ['standard']
        dat = software.resuelve('debian', nat)
        self.assertIn('apt', dat['packages'])
        self.assertNotIn('task-standard', dat['packages'])

    def test_server_environment_does_not_add_desktop(self):
        nat = software.defecto('fedora')
        nat.update(environment='server-product-environment', groups=['container-management'])
        dat = profiles.seleccion('fedora', ['base'], nat)
        self.assertIn('@server-product', dat['packages'])
        self.assertIn('@container-management', dat['packages'])
        self.assertNotIn('@xfce-desktop', dat['packages'])
        with tempfile.TemporaryDirectory() as tmp:
            profiles.genera('fedora', ['base'], Path(tmp), native=nat)
            txt = (Path(tmp) / 'installed.ks').read_text()
            self.assertNotIn('startxonboot', txt)
            self.assertIn('@server-product', txt)

    def test_unknown_choice_stale_catalog_and_execution_fields_rejected(self):
        for campo, val in [('groups',['unknown']), ('groups',['core;reboot']),
                           ('environment','missing'), ('catalog_sha256','0'*64), ('apply',True)]:
            nat = software.defecto('fedora')
            nat[campo] = val
            with self.subTest(campo=campo, val=val), self.assertRaises(ValueError):
                software.resuelve('fedora', nat)

    def test_web_manifest_roundtrip_to_dnf_plan_and_kickstart(self):
        nat = software.defecto('fedora')
        nat.update(environment='server-product-environment', groups=['virtualization'])
        dat = {'schema':'aux-install-v1', 'distribution':'fedora', 'roles':['base','network'],
               'native':nat, 'mode':'root', 'root':'/tmp/aux-test-root'}
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp) / 'aux-selection.json'
            pth.write_text(json.dumps(dat))
            sel = interactive.lee_seleccion(pth)
            cmd = setup.comandos_base(sel['distro'], Path(sel['root']), True,
                                     sel['roles'].split(','), 'rawhide', sel['native'])[0]
            self.assertIn('@virtualization', cmd)
            self.assertIn('@server-product', cmd)
            profiles.genera(sel['distro'],sel['roles'].split(','),Path(tmp)/'profile',native=sel['native'])
            txt = (Path(tmp)/'profile/installed.ks').read_text()
            self.assertIn('@virtualization',txt)

    def test_debian_profile_respects_selected_tasksel_tasks(self):
        nat = software.defecto('debian')
        nat['tasks'] = ['standard','ssh-server']
        with tempfile.TemporaryDirectory() as tmp:
            profiles.genera('debian',['base'],Path(tmp),native=nat)
            txt = (Path(tmp)/'preseed.cfg').read_text()
            self.assertIn('tasksel tasksel/first multiselect standard, ssh-server',txt)
            self.assertNotIn('task-xfce-desktop',txt)

    def test_web_and_console_use_the_same_catalog(self):
        dat = webapps.modelo()
        self.assertEqual(dat['software']['fedora'], software.carga('fedora'))
        self.assertEqual(dat['software']['debian'], software.carga('debian'))

    def test_command_line_consumes_manifest_and_only_prints_plan(self):
        nat = software.defecto('fedora')
        nat.update(environment='server-product-environment', groups=[])
        dat = {'schema':'aux-install-v1', 'distribution':'fedora', 'roles':['base'],
               'native':nat, 'mode':'existing', 'root':'/'}
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)/'selection.json'
            pth.write_text(json.dumps(dat))
            res = subprocess.run(['python3',str(setup.DIR_APP/'aux-setup'),'--selection',str(pth)],
                                 capture_output=True,text=True)
            self.assertEqual(res.returncode,0,res.stderr)
            self.assertIn('+ dnf -y install',res.stdout)
            self.assertIn('@server-product',res.stdout)
            self.assertNotIn('@xfce-desktop',res.stdout)
            dat['apply'] = True
            pth.write_text(json.dumps(dat))
            with self.assertRaises(ValueError):
                interactive.lee_seleccion(pth)


if __name__ == '__main__':
    unittest.main()
