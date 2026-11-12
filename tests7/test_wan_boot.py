# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Exercise real iPXE extraction and ISO replay without mounting client disks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from auxlib import wan_boot as wan

RAIZ = Path(__file__).resolve().parents[1]


class MenusWAN(unittest.TestCase):
    def test_default_and_existing_entries_survive_repeated_rendering(self):
        txt = "set default=local\nset timeout=19\nmenuentry 'Local rescue' --id local { echo local; }\n"
        nuevo = wan.agrega_grub(txt)
        self.assertTrue(nuevo.startswith(txt))
        self.assertEqual(wan.agrega_grub(nuevo), nuevo)
        self.assertEqual(nuevo.count('--id aux-wan-arsenal'), 1)
        self.assertIn('linux16 /aux/wan/ipxe.lkrn', nuevo)
        self.assertIn('chainloader /aux/wan/ipxe.efi', nuevo)
        self.assertIn('"$grub_cpu" = "x86_64"', nuevo)
        self.assertNotIn('set default=aux-wan', nuevo)

    def test_isolinux_preserves_default_and_does_not_duplicate(self):
        txt = 'default vesamenu.c32\ninclude stdmenu.cfg\ninclude txt.cfg\n'
        nuevo = wan.agrega_isolinux(txt)
        self.assertTrue(nuevo.startswith(txt))
        self.assertEqual(wan.agrega_isolinux(nuevo), nuevo)
        self.assertIn('kernel /aux/wan/ipxe.lkrn', nuevo)

    def test_incomplete_or_unmarked_block_is_rejected(self):
        for txt in (wan.INICIO + '\n', "menuentry 'Other' --id aux-wan-arsenal { echo x; }"):
            with self.subTest(config=txt), self.assertRaises(ValueError):
                wan.agrega_grub(txt)

    def test_bundled_image_declares_the_correct_excalibur_url(self):
        _, dat = wan.informacion()
        self.assertEqual(dat['menu_url'], wan.MENU_URL)
        self.assertFalse(dat['uefi_signed'])

    def test_custom_image_with_mismatched_digest_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            wan.informacion(sha_img='0' * 64)


@unittest.skipUnless(shutil.which('xorriso'), 'xorriso is required')
class ImagenesWAN(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def iso(self, archivos):
        raiz = self.pth / 'tree'
        for rel, txt in archivos.items():
            pth = raiz / rel
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_text(txt)
            pth.chmod(0o444)
        iso = self.pth / 'source.iso'
        subprocess.run(['xorriso', '-as', 'mkisofs', '-R', '-o', str(iso), str(raiz)],
                       check=True, capture_output=True)
        return iso

    def test_actual_binaries_match_both_firmware_hashes(self):
        cap = wan.prepara_payload(self.pth / 'payload')
        for nom, clave in (('ipxe.lkrn', 'bios_sha256'), ('ipxe.efi', 'uefi_sha256')):
            self.assertEqual(wan.suma(self.pth / 'payload' / nom), cap[clave])
        self.assertFalse(cap['boot_verified'])

    def test_iso_maps_real_menu_and_payload_and_leaves_efi_stub_unchanged(self):
        txt = "set default=local\nset timeout=17\nmenuentry 'Local' --id local { echo local; }\n"
        stub = 'configfile /boot/grub2/grub.cfg\n'
        iso = self.iso({'boot/grub2/grub.cfg': txt, 'EFI/BOOT/grub.cfg': stub})
        mapas, cola, archivos, cap = wan.prepara_iso(iso, self.pth / 'work')
        self.assertEqual(cap['configs'], ['/boot/grub2/grub.cfg'])
        nuevo = self.pth / 'final.iso'
        subprocess.run(['xorriso', '-indev', str(iso), '-outdev', str(nuevo), *mapas,
                        '-boot_image', 'any', 'replay', *cola, '-commit', '-end'], check=True, capture_output=True)
        wan.verifica_iso(nuevo, archivos, self.pth / 'readback')
        cfg = self.pth / 'cfg'
        wan.extrae(nuevo, '/boot/grub2/grub.cfg', cfg)
        self.assertTrue(cfg.read_text().startswith(txt))
        cfg.unlink()
        wan.extrae(nuevo, '/EFI/BOOT/grub.cfg', cfg)
        self.assertEqual(cfg.read_text(), stub)

    def test_debian_grub_and_bios_isolinux_get_the_same_destination(self):
        iso = self.iso({'boot/grub/grub.cfg': "menuentry 'Install' { echo install; }\n",
                        'isolinux/menu.cfg': 'include txt.cfg\n'})
        mapas, cola, archivos, cap = wan.prepara_iso(iso, self.pth / 'work')
        self.assertEqual(cap['configs'], ['/boot/grub/grub.cfg', '/isolinux/menu.cfg'])
        self.assertEqual(cap['menu_url'], wan.MENU_URL)
        self.assertIn('/aux/wan/ipxe.efi', archivos)
        self.assertIn('/aux/wan/ipxe.lkrn', archivos)
        nuevo = self.pth / 'final.iso'
        subprocess.run(['xorriso', '-indev', str(iso), '-outdev', str(nuevo), *mapas,
                        '-boot_image', 'any', 'replay', *cola, '-commit', '-end'], check=True, capture_output=True)
        wan.verifica_iso(nuevo, archivos, self.pth / 'readback')

    def test_iso_without_reachable_grub_menu_is_rejected(self):
        iso = self.iso({'EFI/BOOT/grub.cfg': 'configfile /unknown/grub.cfg\n'})
        with self.assertRaisesRegex(ValueError, 'No hay un menú GRUB compatible'):
            wan.prepara_iso(iso, self.pth / 'work')

    def test_final_readback_detects_wrong_payload(self):
        iso = self.iso({'boot/grub/grub.cfg': "menuentry 'Install' { echo install; }\n"})
        with self.assertRaisesRegex(ValueError, 'no contiene'):
            wan.verifica_iso(iso, {'/boot/grub/grub.cfg': '0' * 64}, self.pth / 'readback')

    def test_corrupt_binary_is_rejected_even_if_container_matches_metadata(self):
        # A valid container hash alone cannot stand in for both executable hashes.
        pth_img = RAIZ / 'usb/aux-ipxe-usb.img'
        dat = json.loads((RAIZ / 'usb/build-info.json').read_text())
        dat['uefi_sha256'] = '0' * 64
        with patch.object(wan, 'informacion', return_value=(pth_img, dat)):
            with self.assertRaisesRegex(ValueError, 'ejecutable iPXE'):
                wan.prepara_payload(self.pth / 'payload')

    def test_bundled_key_has_a_valid_native_gpt_for_the_usb_writer(self):
        spec = importlib.util.spec_from_file_location('wan_usb_writer', RAIZ / 'usb/create-usb.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertGreater(mod.estructura(RAIZ / 'usb/aux-ipxe-usb.img'), 2)

    @unittest.skipUnless(all(shutil.which(n) for n in ('mcopy', 'mdir', 'implantisomd5', 'checkisomd5')),
                         'mtools and isomd5sum are required')
    def test_full_finisher_updates_appended_efi_config_and_preserves_source(self):
        key = RAIZ / 'usb/aux-ipxe-usb.img'
        boot = self.pth / 'boot'
        subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(key),
                        '-extract_boot_images', str(boot)], check=True, capture_output=True)
        efi = next(boot.glob('*_uefi.img'))
        efi.chmod(0o644)
        cfg = self.pth / 'old.cfg'
        cfg.write_text("menuentry 'Stale EFI-only menu' { echo stale; }\n")
        subprocess.run(['mcopy', '-o', '-i', str(efi), str(cfg), '::/EFI/BOOT/grub.cfg'], check=True)
        ori, dst = self.pth / 'source.iso', self.pth / 'final.iso'
        subprocess.run(['xorriso', '-indev', str(key), '-outdev', str(ori),
                        '-boot_image', 'any', 'replay', '-append_partition', '2', '0xef', str(efi),
                        '-commit', '-end'], check=True, capture_output=True)
        sha = wan.suma(ori)
        subprocess.run([sys.executable, str(RAIZ / 'iso-assist/finish.py'),
                        '--input', str(ori), '--output', str(dst)], check=True, capture_output=True)
        self.assertEqual(wan.suma(ori), sha)
        self.assertTrue(dst.with_suffix('.iso.sha256').is_file())
        final_boot = self.pth / 'final-boot'
        subprocess.run(['xorriso', '-osirrox', 'on', '-indev', str(dst),
                        '-extract_boot_images', str(final_boot)], check=True, capture_output=True)
        cfg.unlink()
        subprocess.run(['mcopy', '-i', str(next(final_boot.glob('*_uefi.img'))),
                        '::/EFI/BOOT/grub.cfg', str(cfg)], check=True)
        self.assertIn('search --no-floppy --file --set=aux_wan_media /aux/wan/media-', cfg.read_text())
        self.assertIn('configfile /boot/grub/grub.cfg', cfg.read_text())
        self.assertNotIn('Stale', cfg.read_text())
