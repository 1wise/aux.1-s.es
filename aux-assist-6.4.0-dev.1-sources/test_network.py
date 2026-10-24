#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 1.0.0
# Author and Credits: https://www.alawise.es/1-s
"""Exercise Live image network preparation using real isolated filesystem state."""
import base64
import configparser
import json
import os
from pathlib import Path
import shlex
import tempfile
import unittest

from payload.network_setup import prepara_red
import prepare


class RedLive(unittest.TestCase):
    def setUp(self):
        self.sys_tmp = tempfile.TemporaryDirectory()
        self.sys_rad = Path(self.sys_tmp.name) / 'image'
        (self.sys_rad / 'etc/NetworkManager/system-connections').mkdir(parents=True)
        (self.sys_rad / 'var/lib/NetworkManager').mkdir(parents=True)

    def tearDown(self):
        self.sys_tmp.cleanup()

    def test_installer_resolver_symlink_is_replaced_without_changing_its_target(self):
        self.sys_dst = Path(self.sys_tmp.name) / 'builder-resolv.conf'
        self.sys_dst.write_text('nameserver 192.0.2.53\n')
        self.sys_res = self.sys_rad / 'etc/resolv.conf'
        self.sys_res.symlink_to(self.sys_dst)
        prepara_red(self.sys_rad)
        self.assertEqual(os.readlink(self.sys_res), '/run/NetworkManager/resolv.conf')
        self.assertEqual(self.sys_dst.read_text(), 'nameserver 192.0.2.53\n')
        self.assertFalse((self.sys_rad / 'run/NetworkManager/resolv.conf').exists())

    def test_missing_dangling_and_regular_resolvers_are_safe_and_repeatable(self):
        self.sys_res = self.sys_rad / 'etc/resolv.conf'
        for self.sys_tip in ('missing', 'dangling', 'regular'):
            with self.subTest(resolver=self.sys_tip):
                self.sys_res.unlink(missing_ok=True)
                if self.sys_tip == 'dangling':
                    self.sys_res.symlink_to('/run/systemd/resolve/stub-resolv.conf')
                elif self.sys_tip == 'regular':
                    self.sys_res.write_text('nameserver 192.0.2.53\n')
                prepara_red(self.sys_rad)
                prepara_red(self.sys_rad)
                self.assertEqual(os.readlink(self.sys_res), '/run/NetworkManager/resolv.conf')

    def test_image_preparation_discards_installer_profiles_and_disabled_state(self):
        self.sys_per = self.sys_rad / 'etc/NetworkManager/system-connections'
        (self.sys_per / 'builder.nmconnection').write_text(
            '[connection]\ninterface-name=ens3\n[802-3-ethernet]\nmac-address=52:54:00:00:00:01\n'
        )
        self.sys_dst = Path(self.sys_tmp.name) / 'outside-profile'
        self.sys_dst.write_text('preserve symlink target')
        (self.sys_per / 'builder-link').symlink_to(self.sys_dst)
        for self.sys_nom in ('NetworkManager.state', 'NetworkManager-intern.conf', 'no-auto-default.state'):
            (self.sys_rad / 'var/lib/NetworkManager' / self.sys_nom).write_text('builder-only')
        prepara_red(self.sys_rad)
        self.assertEqual(list(self.sys_per.iterdir()), [])
        self.assertEqual(list((self.sys_rad / 'var/lib/NetworkManager').iterdir()), [])
        self.assertEqual(self.sys_dst.read_text(), 'preserve symlink target')
        self.sys_cfg = configparser.ConfigParser()
        self.sys_cfg.read(self.sys_rad / 'etc/NetworkManager/conf.d/90-aux-live.conf')
        self.assertEqual(dict(self.sys_cfg['main']), {
            'dhcp': 'internal', 'dns': 'default', 'rc-manager': 'symlink', 'no-auto-default': ''
        })

    def test_generated_recipe_delivers_and_calls_network_setup_inside_post(self):
        self.sys_sal = Path(self.sys_tmp.name) / 'recipe'
        prepare.render(self.sys_sal)
        self.sys_txt = (self.sys_sal / 'assist.ks').read_text()
        self.sys_cod = self.sys_txt.split('%post ', 1)[1].split('\n', 1)[1].rsplit('%end', 1)[0]
        self.sys_b64 = self.sys_cod.split("base64.b64decode('", 1)[1].split("')", 1)[0]
        self.sys_dat = {self.sys_ent['path']: base64.b64decode(self.sys_ent['data']).decode()
                        for self.sys_ent in json.loads(base64.b64decode(self.sys_b64))}
        self.assertIn('/usr/share/aux-assist/network_setup.py', self.sys_dat)
        self.assertIn("prepara_red(Path('/'))", self.sys_cod)
        self.assertIn('nm-online', prepare.COMANDOS)
        # A timeout is non-fatal so the root console and nmtui still open offline.
        self.sys_uni = self.sys_dat['/etc/systemd/system/aux-assist.service']
        self.sys_exe = [self.sys_lin.split('=', 1)[1] for self.sys_lin in self.sys_uni.splitlines()
                        if self.sys_lin.startswith('ExecStartPre=')]
        self.assertEqual(shlex.split(self.sys_exe[0]),
                         ['-/usr/bin/nm-online', '--quiet', '--timeout=15'])
        self.assertEqual(shlex.split(self.sys_exe[1]), ['/usr/bin/chvt', '6'])
        self.assertEqual(self.sys_cod.count('prepara_red('), 1)


if __name__ == '__main__':
    unittest.main()
