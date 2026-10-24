#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Validate shared-root materialization and USB guards without touching any device."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

ROOT = Path(__file__).resolve().parent


def modulo(nom, rel):
    spec = importlib.util.spec_from_file_location(nom, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ovh = modulo('ovh61', 'ovh/assemble.py')
usb = modulo('usb61', 'usb/create-usb.py')
prep = modulo('prep61', 'iso-assist/prepare.py')


def iso_gpt(pth, hybrid=False):
    # A small synthetic GPT parser fixture, deliberately not a bootable ISO.
    buf = bytearray(1024 * 1024)
    buf[510:512] = b'\x55\xaa'
    buf[450] = 0xee
    if hybrid:
        buf[466] = 0x83
    tabla = bytearray(128 * 128)
    tabla[:16] = b'\x42' * 16
    struct.pack_into('<QQ', tabla, 32, 64, 128)
    cab = bytearray(512)
    cab[:8] = b'EFI PART'
    struct.pack_into('<I', cab, 8, 0x10000)
    struct.pack_into('<I', cab, 12, 92)
    struct.pack_into('<QIII', cab, 72, 2, 128, 128, zlib.crc32(tabla) & 0xffffffff)
    struct.pack_into('<I', cab, 16, zlib.crc32(cab[:92]) & 0xffffffff)
    buf[512:1024] = cab
    buf[1024:1024+len(tabla)] = tabla
    pth.write_bytes(buf)


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def arbol(self):
        web, iso, tec = [self.pth / n for n in ('web', 'isos', 'tec-web')]
        for pth in (web, iso, tec):
            pth.mkdir()
        (web / 'index.html').write_text('AUX')
        (web / 'cli.html').write_text('PXE')
        (iso / 'sample.iso').write_bytes(b'fixture-image')
        (web / 'sample.iso').symlink_to(iso / 'sample.iso')
        (tec / 'index.php').write_text('<?php echo "TEC";')
        (tec / 'vendor').mkdir()
        (tec / 'vendor/xterm.js').write_text('// fixture')
        return web, iso, tec

    def test_ovh_one_physical_root_for_everything(self):
        web, iso, tec = self.arbol()
        out = self.pth / 'output'
        plan = ovh.prepara(web, iso, tec, out)
        self.assertFalse(out.exists())
        self.assertEqual(plan['iso_count'], 1)
        rsp = ovh.prepara(web, iso, tec, out, aplicar=True)
        self.assertTrue(rsp['applied'])
        self.assertEqual((out / 'sample.iso').read_bytes(), b'fixture-image')
        self.assertFalse((out / 'sample.iso').is_symlink())
        self.assertTrue((out / 'tec/vendor/xterm.js').is_file())
        self.assertTrue((out / '.htaccess').is_file())
        self.assertEqual(len(list(out.rglob('*.iso'))), 1)

    def test_ovh_refuses_overwrite_escape_private_and_cycles(self):
        web, iso, tec = self.arbol()
        externo = self.pth / 'private.txt'
        externo.write_text('private')
        (web / 'escape.txt').symlink_to(externo)
        with self.assertRaisesRegex(ValueError, 'fuera'):
            ovh.prepara(web, iso, tec, self.pth / 'new')
        (web / 'escape.txt').unlink()
        (web / 'usuarios.json').write_text('[]')
        with self.assertRaisesRegex(ValueError, 'privado'):
            ovh.prepara(web, iso, tec, self.pth / 'new')
        (web / 'usuarios.json').unlink()
        (web / 'cycle').symlink_to(web, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Bucle'):
            ovh.prepara(web, iso, tec, self.pth / 'new')
        with self.assertRaisesRegex(ValueError, 'nuevo'):
            ovh.prepara(web, iso, tec, web)

    def test_ovh_rejects_administrative_tec_root(self):
        web, iso, tec = self.arbol()
        (tec / 'manage.php').write_text('<?php')
        with self.assertRaises(ValueError):
            ovh.prepara(web, iso, tec, self.pth / 'out')

    def test_ovh_blocks_iso_name_collision(self):
        web, iso, tec = self.arbol()
        (web / 'sample.iso').unlink()
        (web / 'sample.iso').write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'Colisión'):
            ovh.prepara(web, iso, tec, self.pth / 'out')

    def test_ovh_routing_has_t_endpoints_and_vendor(self):
        txt = (ROOT / 'ovh/shared.htaccess').read_text()
        self.assertIn('(?:t|tec)', txt)
        self.assertIn('tec/index.php', txt)
        self.assertIn('vendor', txt)
        self.assertIn('cli.html', txt)
        self.assertNotIn('[R=', txt)

    def test_usb_native_gpt_first_free_slot(self):
        pth = self.pth / 'fixture.iso'
        iso_gpt(pth)
        self.assertEqual(usb.estructura(pth), 2)

    def test_usb_hybrid_and_corrupt_crc_abort(self):
        pth = self.pth / 'fixture.iso'
        iso_gpt(pth, hybrid=True)
        with self.assertRaisesRegex(ValueError, 'híbrida'):
            usb.estructura(pth)
        iso_gpt(pth)
        buf = bytearray(pth.read_bytes());buf[512 + 40] ^= 1;pth.write_bytes(buf)
        with self.assertRaisesRegex(ValueError, 'CRC'):
            usb.estructura(pth)
        iso_gpt(pth)
        buf = bytearray(pth.read_bytes());buf[1024] ^= 1;pth.write_bytes(buf)
        with self.assertRaisesRegex(ValueError, 'CRC'):
            usb.estructura(pth)

    def test_usb_rejects_regular_files_as_devices(self):
        pth = self.pth / 'not-a-device'
        pth.write_text('not a device')
        with self.assertRaises(ValueError), patch.object(usb.subprocess, 'run', side_effect=AssertionError('no commands')):
            usb.info_dispositivo(pth)

    def test_usb_checksum_failure_precedes_all_disk_commands(self):
        pth = self.pth / 'fixture.iso'
        iso_gpt(pth)
        with patch.object(sys, 'argv', ['usb', '--iso', str(pth), '--sha256', '0'*64,
                                      '--device', '/dev/DO-NOT-TOUCH', '--apply']), \
             patch.object(usb.subprocess, 'run', side_effect=AssertionError('disk command')), \
             patch.object(usb, 'print'):
            self.assertEqual(usb.main(), 1)

    def test_new_kickstart_contains_every_agent_part_without_credentials(self):
        out = self.pth / 'recipe'
        prep.render(out, pth_cfg=ROOT / 'fast-boot.json')
        txt = (out / 'assist.ks').read_text()
        raw = txt.split("base64.b64decode('", 1)[1].split("')", 1)[0]
        files = {ent['path']: base64.b64decode(ent['data']).decode() for ent in json.loads(base64.b64decode(raw))}
        for nom in ('ai_agent.py', 'aux_exec.py', 'storage.py'):
            self.assertIn('/usr/share/aux-assist/' + nom, files)
        for nom in ('aux-exec.service', 'aux-gpt.service', 'aux-gemini.service'):
            self.assertIn('/etc/systemd/system/' + nom, files)
        self.assertIn("'aux-ai'", txt)
        self.assertNotIn('/var/lib/aux-assist/cli-excalibur.secret', str(files))

    def test_service_contract_and_no_ai_proxy_claim(self):
        txt = (ROOT / 'iso-assist/payload/aux-exec.service').read_text()
        self.assertIn('User=root', txt)
        self.assertIn('ReadWritePaths=/run/aux-exec', txt)
        self.assertNotIn('ReadWritePaths=/work', txt)
        guia = (ROOT / 'RELEASE-6.1.md').read_text()
        self.assertIn('no API de IA', guia)
        self.assertFalse(json.loads((ROOT / 'CHECKLIST-6.1.json').read_text())['stable_ready'])


if __name__ == '__main__':
    unittest.main()
