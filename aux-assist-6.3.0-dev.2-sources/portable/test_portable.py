#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Test menu contracts and isolated kernel publication without mounting or flashing."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import contextlib
import io
import sys
import unittest
from unittest.mock import patch
import build
import portable_menu as menu
import runtime

UID='8dc593dc-29b5-4484-b85d-91ab980810a5'


class Portable(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.pth=Path(self.tmp.name)

    def tearDown(self):self.tmp.cleanup()

    def test_menu_uses_one_base_and_distinct_persistence_profiles(self):
        cfg=menu.menu(UID)
        for nom in ('aux-persistent','aux-clean','aux-network'):
            self.assertIn('--id '+nom,cfg)
        self.assertIn('rd.live.overlay=UUID='+UID+':/AUX/persist/upper',cfg)
        self.assertNotIn('rd.live.overlay=',menu.parametros(UID,False))
        self.assertIn('rd.live.dir=/LiveOS/clean',cfg)
        self.assertIn('chainloader /AUX/ipxe/ipxe.efi',cfg)
        self.assertIn('linux16 /AUX/ipxe/ipxe.lkrn',cfg)
        self.assertEqual(cfg.count('set timeout=5'),1)
        # A named default must keep selecting the writable profile after kernel publication.
        self.assertIn('set default=aux-persistent\n',cfg)
        self.assertLess(cfg.index('--id aux-persistent'),cfg.index('--id aux-clean'))
        self.assertLess(cfg.index('--id aux-clean'),cfg.index('--id aux-network'))
        actual={'version':'6.3-fixture','path':'/AUX/boot/6.3-fixture'}
        anterior={'version':'6.2-fixture','path':'/AUX/boot/6.2-fixture'}
        publicado=cfg.replace('source /AUX/boot/entries.cfg',menu.kernels(UID,actual,anterior))
        self.assertLess(publicado.index('--id aux-persistent'),publicado.index('--id aux-previous'))
        self.assertLess(publicado.index('--id aux-previous'),publicado.index('--id aux-clean'))
        with self.assertRaises(ValueError):menu.menu("UUID'; reboot")
        with self.assertRaises(ValueError):menu.entrada('x','x','/../escape','/good','args')

    def test_plan_checksum_capacity_and_regular_file_guards(self):
        iso=self.pth/'fixture.iso';iso.write_bytes(b'fixture-not-a-bootable-iso')
        sha=hashlib.sha256(iso.read_bytes()).hexdigest()
        with patch.object(build,'orden',side_effect=AssertionError('no commands in plan')):
            dat=build.plan(iso,sha,32_000_000_000,False)
            self.assertEqual(dat['capacity_bytes'],32_000_000_000)
            self.assertEqual(dat['default_boot'],'aux-persistent')
            self.assertEqual(dat['boot_timeout_seconds'],5)
            self.assertEqual(dat['support_resume'],{'required_for_release':True,'implemented':True,'live_verified':False})
            with self.assertRaises(ValueError):build.plan(iso,'0'*64,32_000_000_000,False)
            with self.assertRaises(ValueError):build.plan(iso,sha,100,False)
            link=self.pth/'link';link.symlink_to(iso)
            with self.assertRaises(ValueError):build.plan(link,sha,32_000_000_000,False)

    def test_loop_must_belong_to_the_new_image(self):
        img=self.pth/'new.img';img.touch()
        with patch.object(build,'orden',return_value=SimpleNamespace(stdout=json.dumps(
             {'loopdevices':[{'back-file':str(img)}]}))):
            build.verifica_loop('/dev/loop42',img)
            with self.assertRaises(ValueError):build.verifica_loop('/dev/sda',img)
            with self.assertRaises(ValueError):build.verifica_loop('/dev/loop42',self.pth/'other.img')

    def test_persistent_identity_and_real_upper_directory_are_required(self):
        live=self.pth/'live';upper=live/'AUX/persist/upper';upper.mkdir(parents=True)
        (live/'AUX/manifest.json').write_text(json.dumps({'schema':menu.SCHEMA,'filesystem_uuid':UID}))
        cmd=self.pth/'cmdline';cmd.write_text('aux.usb='+UID+' aux.persist=1')
        def orden(*args,**kwargs):
            return SimpleNamespace(stdout=json.dumps({'filesystems':[{'uuid':UID,'fstype':'ext4','target':str(live)}]})
                if '--json' in args else 'rw,lowerdir=/base,upperdir='+str(upper)+',workdir=/tmp/work')
        with patch.object(runtime,'CMDLINE',cmd),patch.object(runtime.os,'geteuid',return_value=0),\
             patch.object(Path,'is_mount',return_value=True),patch.object(runtime,'orden',side_effect=orden):
            self.assertEqual(runtime.verifica(live),UID)
            cmd.write_text('aux.usb='+UID+' aux.persist=0')
            with self.assertRaises(ValueError):runtime.verifica(live)
            cmd.write_text('aux.usb='+UID+' aux.persist=1')
            (live/'AUX/manifest.json').write_text(json.dumps({'schema':'unknown','filesystem_uuid':UID}))
            with self.assertRaises(ValueError):runtime.verifica(live)

    def test_kernel_publication_is_committed_after_initramfs_validation(self):
        live=self.pth/'live';(live/'AUX/boot').mkdir(parents=True)
        mods=self.pth/'modules'
        for ver in ('6.1-fixture','6.2-fixture','6.3-fixture'):
            (mods/ver).mkdir(parents=True);(mods/ver/'vmlinuz').write_bytes(b'kernel-fixture'*1024)
        def orden(*args,**kwargs):
            if args[0]=='dracut':Path(args[-1]).write_bytes(b'initrd-fixture'*1024)
            return SimpleNamespace(stdout='dmsquash-live\nnetwork-manager\n')
        with patch.object(runtime,'LIVE',live),patch.object(runtime,'MODULOS',mods),\
             patch.object(runtime,'verifica',return_value=UID),patch.object(runtime,'orden',side_effect=orden),\
             patch.object(runtime.os,'sync'):
            runtime.publica('6.1-fixture')
            cfg=live/'AUX/boot/entries.cfg'
            first=cfg.read_bytes();self.assertIn(b'6.1-fixture',first)
            with patch.object(runtime,'orden',side_effect=subprocess.CalledProcessError(1,'dracut')):
                with self.assertRaises(subprocess.CalledProcessError):runtime.publica('6.2-fixture')
            self.assertEqual(cfg.read_bytes(),first)
            runtime.publica('6.3-fixture')
            estado=json.loads(cfg.read_text().splitlines()[0][len('# AUXSTATE '):])
            self.assertEqual(estado['current']['version'],'6.3-fixture')
            self.assertEqual(estado['previous']['version'],'6.1-fixture')
            self.assertIn('--id aux-previous',cfg.read_text())

    def test_atomic_failure_preserves_existing_boot_file(self):
        cfg=self.pth/'entries.cfg';cfg.write_bytes(b'previous')
        with patch.object(runtime.os,'replace',side_effect=OSError('fixture interruption')):
            with self.assertRaises(OSError):runtime.atomic(cfg,b'new')
        self.assertEqual(cfg.read_bytes(),b'previous')
        self.assertEqual(sorted(p.name for p in self.pth.iterdir()),['entries.cfg'])

    @unittest.skipUnless(os.geteuid() == 0, 'private source owner contract requires root')
    def test_api_stage_is_private_selected_and_refreshes_missing_keys(self):
        live=self.pth/'live';(live/'AUX').mkdir(parents=True)
        dst=self.pth/'run-api'
        with patch.object(runtime,'LIVE',live),patch.object(runtime,'API_RUN',dst), \
             patch.object(runtime,'verifica',return_value=UID),contextlib.redirect_stdout(io.StringIO()) as out:
            src=runtime.fuentes_api(True)
            runtime.atomic(src/'openai.key',b'fixture-openai-secret\n')
            runtime.atomic(src/'gemini.key',b'fixture-gemini-secret\n')
            runtime.prepara_api('openai')
            self.assertEqual((dst/'openai.key').read_bytes(),b'fixture-openai-secret')
            self.assertFalse((dst/'gemini.key').exists())
            self.assertEqual(dst.stat().st_mode & 0o777,0o700)
            self.assertEqual((dst/'openai.key').stat().st_mode & 0o777,0o600)
            (src/'openai.key').unlink()
            runtime.prepara_api('openai')
            self.assertEqual((dst/'openai.key').read_bytes(),b'')
            runtime.limpia_api()
            self.assertFalse((dst/'openai.key').exists())
            self.assertTrue((src/'gemini.key').exists())
        self.assertNotIn('fixture-',out.getvalue())

    @unittest.skipUnless(os.geteuid() == 0, 'private source owner contract requires root')
    def test_api_sources_reject_public_permissions_symlinks_and_special_files(self):
        live=self.pth/'live';(live/'AUX').mkdir(parents=True)
        with patch.object(runtime,'LIVE',live),patch.object(runtime,'API_RUN',self.pth/'run-api'), \
             patch.object(runtime,'verifica',return_value=UID),contextlib.redirect_stdout(io.StringIO()):
            src=runtime.fuentes_api(True);key=src/'openai.key'
            runtime.atomic(key,b'fixture-secret')
            key.chmod(0o644)
            with self.assertRaises(ValueError):runtime.lee_api(key)
            key.chmod(0o600)
            link=src/'other.key';link.symlink_to(key)
            with self.assertRaises(OSError):runtime.lee_api(link)
            os.link(key,src/'hardlink.key')
            with self.assertRaises(ValueError):runtime.lee_api(key)
            (src/'hardlink.key').unlink();key.unlink();os.mkfifo(key,0o600)
            with self.assertRaises(ValueError):runtime.lee_api(key)
            runtime.prepara_api('openai')
            self.assertEqual((runtime.API_RUN/'openai.key').read_bytes(),b'')
            key.unlink();src.chmod(0o755)
            with self.assertRaises(ValueError):runtime.fuentes_api()

    @unittest.skipUnless(os.geteuid() == 0, 'private source owner contract requires root')
    def test_local_key_manager_stops_old_session_before_replacing_or_deleting(self):
        live=self.pth/'live';(live/'AUX').mkdir(parents=True)
        with patch.object(runtime,'LIVE',live),patch.object(runtime,'API_RUN',self.pth/'run-api'), \
             patch.object(runtime,'verifica',return_value=UID),patch.object(runtime,'orden') as run, \
             patch.object(runtime.os,'sync'),patch.dict(sys.modules,{'ai':SimpleNamespace(pide_clave=lambda:'fixture-secret')}), \
             patch('builtins.input',side_effect=['g','s','']),contextlib.redirect_stdout(io.StringIO()) as out:
            runtime.gestiona_api()
            key=live/'AUX/private/api/openai.key'
            self.assertEqual(key.read_bytes(),b'fixture-secret\n')
            self.assertIn(('systemctl','stop','aux-gpt.service'),[c.args for c in run.call_args_list])
            with patch('builtins.input',side_effect=['g','b','']):runtime.gestiona_api()
            self.assertFalse(key.exists())
            self.assertNotIn('fixture-secret',out.getvalue())

    def test_overlay_installs_public_readers_and_provider_specific_credentials(self):
        upper=self.pth/'upper';medium=self.pth/'medium';(medium/'AUX').mkdir(parents=True)
        build.instala_api(upper,medium)
        self.assertIn('lee_clave_preparada',(upper/'usr/share/aux-assist/ai.py').read_text())
        for prov,uni in (('openai','aux-gpt'),('gemini','aux-gemini')):
            unit=(upper/('etc/systemd/system/'+uni+'.service.d/api-keys.conf')).read_text()
            self.assertIn('LoadCredential='+prov+'.key:/run/aux-api-source/'+prov+'.key',unit)
            self.assertNotIn('Environment=',unit)
        self.assertEqual(list((medium/'AUX/private/api').iterdir()),[])


if __name__=='__main__':unittest.main()
