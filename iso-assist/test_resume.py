#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Verify USB case identity, expiry, stable SSH host keys and shutdown behavior."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

DIR_APP = Path(__file__).resolve().parent
pth = DIR_APP.parent / 'usb/portable'
if not pth.is_dir():pth = DIR_APP / 'portable'
sys.path[:0] = [str(DIR_APP / 'payload'), str(pth)]
import agent
import assist
import runtime as portable_usb
sys.modules['portable_usb'] = portable_usb
import support_case


@unittest.skipUnless(os.geteuid() == 0, 'private case ownership contract requires root')
class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)
        self.arc = self.pth / 'case.json'
        self.uid_usb = '8dc593dc-29b5-4484-b85d-91ab980810a5'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.pth/'host')], check=True)
        self.ctx = patch.object(support_case, 'ruta', return_value=(self.uid_usb, self.arc));self.ctx.start()
        self.eqp = patch.object(support_case, 'equipo', return_value='a'*64);self.eqp.start()
        self.sel = patch.object(support_case, 'portatil', return_value=True);self.sel.start()
        self.cas = support_case.nuevo('web')
        self.cas.update(id='b'*32, code='AUX-FIXTURE', url='https://cli.example.test', token='k'*43,
            technician={'sub':'fixture','name':'Fixture','contact':'fixture@example.test'},
            key=(self.pth/'host.pub').read_text(), direct_key='', host_key=(self.pth/'host').read_text())

    def tearDown(self):
        self.sel.stop();self.eqp.stop();self.ctx.stop();self.tmp.cleanup()

    def test_case_survives_reload_without_extending_expiry(self):
        support_case.guarda(self.cas)
        self.assertEqual(self.arc.stat().st_mode & 0o777, 0o600)
        with patch.object(support_case.time, 'time', return_value=self.cas['created']+600):
            cas = support_case.carga()
        self.assertEqual(cas['expires'], self.cas['expires'])
        self.assertEqual(cas['host_key'], self.cas['host_key'])
        self.assertEqual(cas['token'], self.cas['token'])

    def test_other_equipment_expired_clock_rollback_and_public_file_are_rejected(self):
        for nom in ('equipment','expiry','clock','permissions'):
            support_case.guarda(self.cas)
            if nom == 'permissions':self.arc.chmod(0o644)
            with patch.object(support_case, 'equipo', return_value='c'*64 if nom=='equipment' else 'a'*64), \
                 patch.object(support_case.time, 'time', return_value=(
                     self.cas['expires']+1 if nom=='expiry' else self.cas['created']-301 if nom=='clock' else self.cas['created'])):
                self.assertIsNone(support_case.carga(),nom)
            self.assertFalse(self.arc.exists(),nom)

    def test_clean_profile_does_not_read_or_delete_a_saved_case(self):
        support_case.guarda(self.cas)
        with patch.object(support_case, 'portatil', return_value=False),patch.object(support_case, 'ruta') as ruta:
            self.assertIsNone(support_case.carga())
        ruta.assert_not_called()
        self.assertTrue(self.arc.exists())

    def test_stable_host_and_only_approved_keys_are_restored(self):
        def orden(args, **cfg):
            if args[0] == 'ssh-keygen':return subprocess.run(args, check=True, **cfg)
            return SimpleNamespace(returncode=0,stdout='')
        for idx in range(2):
            pth = self.pth/str(idx);pth.mkdir()
            with patch.object(assist,'DIR_RUN',pth),patch.object(assist,'SOC_TMX',pth/'tmux.sock'), \
                 patch.object(assist,'etiqueta'),patch.object(assist,'ejecuta',side_effect=orden):
                clv_pub = agent.abre_ssh(self.cas['key'],host_key=self.cas['host_key'],directo=True)
            self.assertEqual((pth/'host_ed25519').read_text(),self.cas['host_key'])
            self.assertEqual((pth/'authorized_keys').read_text(),assist.valida_clave(self.cas['key']))
            self.assertIn('ListenAddress 0.0.0.0',(pth/'sshd.conf').read_text())
            self.assertEqual(assist.valida_clave(clv_pub),assist.valida_clave(self.cas['key']))

    def test_shutdown_preserves_grant_but_local_cancel_removes_it(self):
        self.cas['mode']='direct'
        for nom in ('shutdown','cancel'):
            support_case.guarda(self.cas)
            with patch.object(agent,'abre_ssh'),patch.object(assist,'estado'),patch.object(assist,'red',return_value=[]), \
                 patch.object(assist,'limpia'),patch.object(support_case.subprocess,'run',return_value=SimpleNamespace(returncode=0)), \
                 patch.object(support_case.select,'select',side_effect=SystemExit(0) if nom=='shutdown' else KeyboardInterrupt):
                if nom=='shutdown':
                    with self.assertRaises(SystemExit):support_case.reanuda_directa(self.cas)
                    self.assertTrue(self.arc.exists())
                else:
                    support_case.reanuda_directa(self.cas)
                    self.assertFalse(self.arc.exists())


if __name__=='__main__':unittest.main()
