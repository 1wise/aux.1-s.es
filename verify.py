#!/usr/bin/env python3
# Timestamp: 2026-10-13 | Version: 5.1.0
# Author & Credits: https://www.alawise.es/1-s
"""Test independent commands with isolated HTTP, RAM and filesystem fixtures."""

import contextlib
import csv
import hashlib
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import io
import re
from pathlib import Path
import shlex
import socket
import socketserver
import stat
import subprocess
import tempfile
import tarfile
import threading
import unittest
from unittest.mock import patch
from types import ModuleType, SimpleNamespace
from urllib.parse import urlsplit, unquote, quote
import xml.etree.ElementTree as ET
import zipfile

pth_repo = Path(__file__).resolve().parent
def carga_programa(nom):
    arc = pth_repo / nom
    cuerpo = arc.read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
    mod = ModuleType(nom[:-3])
    mod.__file__ = str(arc)
    exec(compile(cuerpo, str(arc), 'exec'), mod.__dict__)
    return mod


eng = carga_programa('generate.sh')
dep = carga_programa('deploy.sh')


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='aux-test-')
        self.pth_tmp = Path(self.tmp.name)
        self.pth_web = self.pth_tmp / 'html'
        self.pth_cac = self.pth_tmp / 'cache'
        self.pth_web.mkdir()
        self.pth_cac.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, cmd, urls, *flags, rc=0, umask=-1):
        args = ['--output', str(self.pth_web), '--cache', str(self.pth_cac),
                '--base-url', 'https://mirror.example.test', '--pxe-url', 'http://127.0.0.1:8080']
        if cmd == 'download':
            arc_urls = self.pth_tmp / 'url.txt'
            arc_urls.write_text('\n'.join(urls) + '\n')
            args += ['--url-file', str(arc_urls)]
        script, extra = ('deploy.sh', [cmd[7:]]) if cmd.startswith('deploy-') else (cmd + '.sh', [])
        res = subprocess.run(['bash', str(pth_repo / script), *extra, *args, *flags], text=True, capture_output=True, umask=umask)
        self.assertEqual(res.returncode, rc, res.stdout + res.stderr)
        return res

    def make_iso(self, nom):
        byt = bytearray(40000)
        byt[32769:32774] = b'CD001'
        (self.pth_cac / nom).write_bytes(byt)
        return byt

    def make_private_tar(self):
        nom = 'debian-netboot-amd64.tar.gz'
        with tarfile.open(self.pth_cac / nom, 'w:gz') as arc:
            for name in ['debian-installer', 'debian-installer/amd64']:
                ent = tarfile.TarInfo(name)
                ent.type = tarfile.DIRTYPE
                ent.mode = 0o700
                arc.addfile(ent)
            for name, data, mode in [('linux', b'network-kernel', 0o600),
                                     ('initrd.gz', b'network-initrd', 0o600),
                                     ('helper.sh', b'#!/bin/sh\nexit 0\n', 0o700)]:
                ent = tarfile.TarInfo('debian-installer/amd64/' + name)
                ent.size, ent.mode = len(data), mode
                arc.addfile(ent, io.BytesIO(data))
        (self.pth_cac / nom).chmod(0o600)
        return nom

    def test_read_only_files_and_subdirectories_never_change_ownership_or_modes(self):
        tree = self.pth_web / 'mounted-media'
        tree.mkdir()
        binary = tree / 'isolinux.bin'
        binary.write_bytes(b'boot sector')
        binary.chmod(0o444)
        link = tree / 'boot-link'
        link.symlink_to(binary)
        with patch.object(eng.os, 'statvfs', return_value=SimpleNamespace(f_flag=eng.os.ST_RDONLY)), \
             patch.object(eng.os.path, 'ismount', return_value=False), \
             patch.dict(eng.ajusta_publico.__globals__, {'uid_pub': 1234, 'gid_pub': 1235}), \
             patch.object(eng.os, 'chmod') as mode, patch.object(eng.os, 'chown') as owner:
            eng.ajusta_publico(binary)
            eng.ajusta_publico(link, enlace=True)
            eng.ajusta_tree(tree)
            mode.assert_not_called()
            owner.assert_not_called()
        self.assertEqual(stat.S_IMODE(binary.stat().st_mode), 0o444)

    def test_generate_read_only_dban_tree_keeps_internals_only_in_contents_browser(self):
        import errno
        name = 'dban-2.3.0_i586.iso'
        image = self.make_iso(name)
        (self.pth_web / name).write_bytes(image)
        tree = self.pth_web / name[:-4]
        tree.mkdir()
        (tree / 'isolinux.bin').write_bytes(b'boot sector')
        (tree / 'nested.iso').write_bytes(image)
        (tree / 'EFI').mkdir()
        (tree / 'EFI/BOOTX64.EFI').write_bytes(b'MZinternal EFI')
        (self.pth_web / 'netboot.xyz.efi').write_bytes(b'MZpublic EFI')
        before = {path: path.read_bytes() for path in tree.rglob('*') if path.is_file()}
        statfs, chmod = eng.os.statvfs, eng.os.chmod
        def filesystem(path):
            return SimpleNamespace(f_flag=eng.os.ST_RDONLY) if Path(path).is_relative_to(tree) else statfs(path)
        def change_mode(path, *args, **kwargs):
            if Path(path).is_relative_to(tree):
                raise OSError(errno.EROFS, 'Read-only file system', str(path))
            return chmod(path, *args, **kwargs)
        argv = ['generate.sh', '--output', str(self.pth_web), '--cache', str(self.pth_cac),
                '--base-url', 'https://aux.example.test', '--pxe-url', 'http://pxe.example.test']
        with patch.object(eng.sys, 'argv', argv), patch.object(eng.os, 'statvfs', side_effect=filesystem), \
             patch.object(eng.os, 'chmod', side_effect=change_mode), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(eng.main(), 0)
        records = json.loads((self.pth_web / 'catalog.json').read_text())['resources']
        self.assertEqual({rec['path'] for rec in records}, {name, 'netboot.xyz.efi'})
        dban = next(rec for rec in records if rec['filename'] == name)
        self.assertTrue(dban['contents_ready'])
        self.assertFalse(dban['pxe_ready'])
        browser = self.pth_web / 'contents' / dban['id'] / 'index.html'
        self.assertIn('isolinux.bin', browser.read_text())
        self.assertIn('nested.iso', browser.read_text())
        self.assertTrue((self.pth_web / 'menu.ipxe').is_file())
        self.assertTrue((self.pth_web / 'sitemaps.xml').is_file())
        for path, data in before.items():
            self.assertEqual(path.read_bytes(), data)

    def test_i386_netboot_cloud_and_architecture_switch(self):
        cfg = SimpleNamespace(output=self.pth_web, pxe_url='http://pxe.test', base_url='https://aux.test')
        urls = ['https://deb.debian.org/debian/dists/bookworm/main/installer-i386/current/images/netboot/netboot.tar.gz',
                'https://example.test/alpine-netboot-3.24.2-x86.tar.gz',
                'https://example.test/debian-13-genericcloud-amd64.qcow2']
        records = eng.obt_catalog('\n'.join(urls))
        self.assertEqual([r['arch'] for r in records], ['i386', 'i386', 'x86_64'])
        self.assertEqual(eng.obt_rama(records[2]), 'cloud')
        for rec in records:
            rec.update(published=True, status='ready')
            (self.pth_web / rec['filename']).write_bytes(b'fixture')
            tree = self.pth_web / rec['tree']
            if rec['format'] == 'QCOW2':
                self.assertIsNone(eng.gen_boot(rec, cfg))
                continue
            tree.mkdir()
            sub = tree / ('debian-installer/i386' if rec['family'] == 'debian' else 'boot')
            sub.mkdir(parents=True)
            names = ['linux', 'initrd.gz'] if rec['family'] == 'debian' else ['vmlinuz-lts', 'initramfs-lts', 'modloop-lts']
            for name in names:
                (sub / name).write_bytes(b'fixture')
            rec['_boot'] = eng.gen_boot(rec, cfg)
            self.assertIsNotNone(rec['_boot'])
            if rec['family'] == 'alpine':
                self.assertIn('modloop=http://pxe.test/', rec['_boot']['commands'][0])
                (sub / 'modloop-lts').unlink()
                self.assertIsNone(eng.gen_boot(rec, cfg))
        menu = eng.gen_ipxe(records, cfg)
        self.assertIn('set menu_arch ${cpu_arch}', menu)
        self.assertIn('item arch_menu Architecture:', menu)
        self.assertIn('iseq ${menu_arch} i386 && iseq ${buildarch} i386 && item', menu)
        self.assertIn('iseq ${buildarch} i386 || goto incompatible', menu)
        self.assertNotIn('kernel http://pxe.test/debian-13-genericcloud', menu)
        self.assertIn(':boards', menu)

    def test_all_alpine_editions_use_local_release_matched_dependencies(self):
        records = eng.obt_catalog((pth_repo / 'url.txt').read_text(), 'alpine')
        self.assertEqual(len(records), 7)
        self.assertEqual(len({r['name'] for r in records}), 3)
        self.assertEqual({r['arch'] for r in records}, {'i386', 'x86_64', 'arm64'})
        cfg = SimpleNamespace(output=self.pth_web, pxe_url='http://pxe.test')
        for rec in records:
            rec.update(published=True, status='ready')
            (self.pth_web / rec['filename']).write_bytes(b'fixture')
            boot = self.pth_web / rec['tree'] / 'boot'
            boot.mkdir(parents=True)
            for name in ['vmlinuz-lts', 'initramfs-lts', 'modloop-lts']:
                (boot / name).write_bytes(b'fixture')
            recipe = eng.gen_boot(rec, cfg)
            self.assertIsNotNone(recipe)
            self.assertIn('/' + rec['tree'] + '/boot/modloop-lts', recipe['commands'][0])
            rec['release'] = '3.25.1'
            self.assertIn('/alpine/v3.25/main', eng.gen_boot(rec, cfg)['commands'][0])
            (boot / 'modloop-lts').unlink()
            outside = self.pth_tmp / 'external-modloop'
            outside.write_bytes(b'wrong image')
            (boot / 'modloop-lts').symlink_to(outside)
            self.assertIsNone(eng.gen_boot(rec, cfg))

    def test_verified_cache_clears_stale_partial_files(self):
        name = 'alpine-test.efi'
        data = b'MZ' + b'x' * 2048
        (self.pth_cac / name).write_bytes(data)
        partial = self.pth_cac / (name + '.part')
        headers = self.pth_cac / (name + '.part.headers')
        partial.write_bytes(b'partial')
        headers.write_text('etag: older')
        checksums = self.pth_tmp / 'SHA256SUMS'
        checksums.write_text(hashlib.sha256(data).hexdigest() + '  ' + name + '\n')
        self.run_cmd('download', ['http://127.0.0.1:1/' + name], '--checksums', str(checksums))
        self.assertFalse(partial.exists())
        self.assertFalse(headers.exists())
        self.assertEqual((self.pth_cac / name).read_bytes(), data)

    @unittest.skipUnless(eng.os.geteuid() == 0 and Path('/dev/shm').is_dir(), 'RAM repair needs tmpfs')
    def test_ram_redeploy_repairs_replaced_managed_link(self):
        name = self.make_private_tar()
        with tempfile.TemporaryDirectory(prefix='aux-ram-link-', dir='/dev/shm') as tmp:
            self.run_cmd('deploy-ram', [], '--ram-dir', tmp)
            tree = self.pth_web / eng.obt_meta('http://test/' + name)['tree']
            self.assertTrue(tree.is_symlink())
            tree.unlink()
            tree.mkdir()
            (tree / 'placeholder').write_text('stale managed tree')
            self.run_cmd('deploy-ram', [], '--ram-dir', tmp)
            self.assertTrue(tree.is_symlink())
            self.assertFalse((tree / 'placeholder').exists())

    def test_split_lists_cover_catalog_without_overlap(self):
        light = eng.obt_catalog((pth_repo / 'light-url.txt').read_text())
        heavy = eng.obt_catalog((pth_repo / 'heavy-url.txt').read_text())
        all_rec = eng.obt_catalog((pth_repo / 'url.txt').read_text())
        names = lambda recs: {rec['filename'] for rec in recs}
        self.assertEqual((len(light), len(heavy)), (29, 20))
        self.assertFalse(names(light) & names(heavy))
        self.assertEqual(names(light) | names(heavy), names(all_rec))
        self.assertEqual({rec['arch'] for rec in light if rec['family'] == 'fedora'}, {'x86_64', 'arm64'})
        self.assertTrue(all('netinst' in rec['filename'].lower() for rec in light if rec['family'] == 'fedora'))
        self.assertTrue(all(rec['format'] != 'ISO' for rec in light if rec['family'] == 'arch'))

    @unittest.skipUnless(eng.os.geteuid() == 0 and Path('/dev/shm').is_dir(), 'Mixed deployment requires tmpfs')
    def test_two_download_lists_merge_sources_and_generate_ram_disk_together(self):
        light_name = self.make_private_tar()
        heavy_name = 'debian-live-amd64.tar.gz'
        with tarfile.open(self.pth_cac / heavy_name, 'w:gz') as archive:
            for name, data in [('live/vmlinuz', b'kernel'), ('live/initrd.img', b'initrd'),
                               ('live/filesystem.squashfs', b'rootfs')]:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        payloads = {name: (self.pth_cac / name).read_bytes() for name in (light_name, heavy_name)}
        for name in payloads:
            (self.pth_cac / name).unlink()
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                body = payloads[self.path.lstrip('/')]
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory(prefix='aux-mixed-', dir='/dev/shm') as ram:
                settings = self.pth_tmp / 'settings'
                settings.mkdir()
                base = f'http://127.0.0.1:{server.server_port}'
                for tier, name in [('light', light_name), ('heavy', heavy_name)]:
                    (settings / (tier + '.txt')).write_text(base + '/' + name + '\n')
                config = settings / 'config.json'
                config.write_text(json.dumps({'cache': str(self.pth_cac), 'output': str(self.pth_web),
                    'ram_dir': ram, 'url_file': 'absent-legacy.txt', 'light_url_file': 'light.txt',
                    'heavy_url_file': 'heavy.txt', 'base_url': 'https://mirror.example.test', 'pxe_url': base}))
                def command(script, *flags):
                    result = subprocess.run(['bash', str(pth_repo / (script + '.sh')), '--config',
                                             str(config), *flags], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return result
                command('download', '--list', 'light')
                self.assertFalse((self.pth_cac / heavy_name).exists())
                command('download', '--list', 'heavy')
                command('download', '--list', 'light')
                self.assertEqual(requests, ['/' + light_name, '/' + heavy_name])
                records = json.loads((self.pth_cac / 'downloads.json').read_text())['resources']
                self.assertEqual({rec['filename']: rec['url'] for rec in records},
                                 {name: base + '/' + name for name in payloads})
                (self.pth_cac / 'unused.efi').write_bytes(b'MZunselected')
                command('deploy', 'ram', '--list', 'light')
                command('deploy', 'disk', '--list', 'heavy')
                self.assertTrue((self.pth_web / light_name).is_symlink())
                self.assertTrue((self.pth_web / light_name[:-7]).is_symlink())
                self.assertFalse((self.pth_web / heavy_name).is_symlink())
                self.assertFalse((self.pth_web / heavy_name[:-7]).is_symlink())
                self.assertFalse((self.pth_web / 'unused.efi').exists())
                command('generate')
                catalog = json.loads((self.pth_web / 'catalog.json').read_text())['resources']
                self.assertEqual({rec['filename'] for rec in catalog}, set(payloads))
                self.assertTrue(all(rec['contents_ready'] and rec['pxe_ready'] for rec in catalog))
                menu = (self.pth_web / 'menu.ipxe').read_text()
                self.assertIn(light_name[:-7] + '/debian-installer/amd64/linux', menu)
                self.assertIn(heavy_name[:-7] + '/live/vmlinuz', menu)
                # Listless deployment still discovers the cache when every list is absent.
                for path in settings.glob('*.txt'):
                    path.unlink()
                result = command('deploy', 'disk', '--dry-run')
                self.assertIn('resources=3', result.stdout)
                self.assertEqual(requests, ['/' + light_name, '/' + heavy_name])
        finally:
            server.shutdown()
            server.server_close()

    def test_explicit_deploy_list_reports_missing_files_without_publishing_unselected_cache(self):
        (self.pth_cac / 'chosen.efi').write_bytes(b'MZselected')
        (self.pth_cac / 'other.efi').write_bytes(b'MZunselected')
        urls = self.pth_tmp / 'selection.txt'
        urls.write_text('https://source.invalid/chosen.efi\nhttps://source.invalid/missing.efi\n')
        result = self.run_cmd('deploy-disk', [], '--url-file', str(urls), rc=1)
        self.assertIn('1 OK | 1 failed', result.stdout)
        self.assertTrue((self.pth_web / 'chosen.efi').is_file())
        self.assertFalse((self.pth_web / 'other.efi').exists())
        self.assertFalse((self.pth_web / 'missing.efi').exists())

    def test_list_selectors_are_exclusive_and_ftp_remains_complete(self):
        result = self.run_cmd('deploy-disk', [], '--list', 'light', '--url-file', 'unused.txt', rc=2)
        self.assertIn('not allowed with argument', result.stderr)
        result = self.run_cmd('deploy-ftp', [], '--list', 'heavy', '--dry-run', rc=2)
        self.assertIn('complete public tree', result.stderr)
        self.assertEqual(list(self.pth_web.iterdir()), [])
        self.assertEqual(list(self.pth_cac.iterdir()), [])

    def test_cached_download_and_all_phases_apply_selected_owner_and_modes(self):
        nom = 'netboot.xyz.efi'
        arc = self.pth_cac / nom
        arc.write_bytes(b'MZcached-efi')
        arc.chmod(0o600)
        self.pth_cac.chmod(0o700)
        flags = ('--user', str(eng.os.geteuid()), '--group', str(eng.os.getegid()))
        self.run_cmd('download', ['https://source.invalid/' + nom], *flags)
        self.assertEqual(stat.S_IMODE(arc.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(self.pth_cac.stat().st_mode), 0o755)
        self.run_cmd('deploy-disk', [], *flags)
        (self.pth_web / nom).chmod(0o600)
        self.run_cmd('generate', [], *flags)
        for rel in [nom, 'index.php', 'assets/portal.css', 'downloads/aux-fast-boot.zip']:
            inf = (self.pth_web / rel).stat()
            self.assertEqual((inf.st_uid, inf.st_gid), (eng.os.geteuid(), eng.os.getegid()))
            self.assertEqual(stat.S_IMODE(inf.st_mode), 0o644)
        self.assertEqual(stat.S_IMODE((self.pth_web / 'downloads/download.sh').stat().st_mode), 0o755)

    def test_permission_helper_changes_owner_without_following_external_links(self):
        arc = self.pth_tmp / 'managed'
        arc.write_text('public')
        arc.chmod(0o600)
        link = self.pth_web / 'outside'
        link.symlink_to(arc)
        with patch.dict(eng.ajusta_publico.__globals__, {'uid_pub': 1234, 'gid_pub': 1235}), patch.object(eng.os, 'chown') as own:
            eng.ajusta_publico(link)
            own.assert_not_called()
            self.assertEqual(stat.S_IMODE(arc.stat().st_mode), 0o600)
            eng.ajusta_publico(link, enlace=True)
            own.assert_called_once_with(link, 1234, 1235, follow_symlinks=False)
            own.reset_mock()
            eng.ajusta_publico(arc)
            own.assert_called_once_with(arc, 1234, 1235, follow_symlinks=False)
            self.assertEqual(stat.S_IMODE(arc.stat().st_mode), 0o644)

    def test_ftp_permission_support_and_denied_modes_are_distinguished(self):
        from unittest.mock import Mock
        cfg = SimpleNamespace()
        conn = Mock()
        dep.ftp_perm(conn, 'file.iso', '644', cfg)
        conn.sendcmd.assert_called_once_with('SITE CHMOD 644 file.iso')
        conn.reset_mock()
        conn.sendcmd.side_effect = dep.ftplib.error_perm('502 unsupported')
        with contextlib.redirect_stderr(io.StringIO()) as output:
            dep.ftp_perm(conn, '.', '755', cfg)
            dep.ftp_perm(conn, 'file.iso', '644', cfg)
        self.assertEqual(conn.sendcmd.call_count, 1)
        self.assertIn('hosting account umask', output.getvalue())
        conn.sendcmd.side_effect = dep.ftplib.error_perm('550 denied')
        with self.assertRaises(dep.ftplib.error_perm):
            dep.ftp_perm(conn, 'file.iso', '644', SimpleNamespace())

    def assert_public_read(self, *paths):
        self.pth_tmp.chmod(0o755)
        for pth in paths:
            self.assertTrue(pth.stat().st_mode & stat.S_IROTH, str(pth))
            # Check the target's complete traversal path; root reads alone cannot verify public access.
            for des in pth.resolve().parents:
                self.assertTrue(des.stat().st_mode & stat.S_IXOTH, str(des))

    def test_disk_permissions_and_matching_tree_repair_without_following_links(self):
        nom = self.make_private_tar()
        self.pth_cac.chmod(0o700)
        self.pth_web.rmdir()
        self.run_cmd('deploy-disk', [], umask=0o077)
        tree = self.pth_web / nom[:-7]
        kernel = tree / 'debian-installer/amd64/linux'
        helper = tree / 'debian-installer/amd64/helper.sh'
        ino = tree.stat().st_ino
        external = self.pth_tmp / 'private'
        external.mkdir(mode=0o700)
        private = external / 'secret'
        private.write_bytes(b'not published')
        private.chmod(0o600)
        (tree / 'outside').symlink_to(external, target_is_directory=True)
        (tree / 'outside-file').symlink_to(private)
        for path in [tree, kernel.parent]:
            path.chmod(0o700)
        for path in [kernel, self.pth_web / nom]:
            path.chmod(0o600)
        self.run_cmd('deploy-disk', [], umask=0o077)
        self.assertEqual(tree.stat().st_ino, ino)
        for path in [self.pth_web, tree, tree / 'debian-installer', kernel.parent]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(helper.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(kernel.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(external.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.pth_cac.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.pth_cac / nom).stat().st_mode), 0o600)
        self.assert_public_read(self.pth_web / nom, kernel, helper)
        with patch.object(dep.os.path, 'ismount', return_value=True), patch.object(Path, 'chmod') as change:
            dep.ajusta_tree(tree)
            change.assert_not_called()

    @unittest.skipUnless(eng.os.geteuid() == 0 and Path('/dev/shm').is_dir(), 'RAM requires tmpfs')
    def test_ram_permissions_and_matching_copy_repair(self):
        nom = self.make_private_tar()
        with tempfile.TemporaryDirectory(prefix='aux-perm-test-', dir='/dev/shm') as ram:
            self.run_cmd('deploy-ram', [], '--ram-dir', ram, umask=0o077)
            tree = Path(ram) / nom[:-7]
            kernel = tree / 'debian-installer/amd64/linux'
            for path in [Path(ram), tree, kernel.parent]:
                path.chmod(0o700)
            (Path(ram) / nom).chmod(0o600)
            kernel.chmod(0o600)
            self.run_cmd('deploy-ram', [], '--ram-dir', ram, umask=0o077)
            for path in [Path(ram), tree, kernel.parent]:
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755)
            self.assert_public_read(self.pth_web / nom, self.pth_web / nom[:-7] / 'debian-installer/amd64/linux')

    def test_generated_directories_and_bundle_are_readable_with_private_umask(self):
        (self.pth_web / 'netboot.xyz.efi').write_bytes(b'MZpermissions')
        self.pth_web.chmod(0o700)
        (self.pth_web / 'assets').mkdir(mode=0o700)
        self.pth_cac.chmod(0o700)
        self.run_cmd('generate', [], umask=0o077)
        for nom in ['', 'assets', 'files', 'downloads', 'downloads/src']:
            self.assertEqual(stat.S_IMODE((self.pth_web / nom).stat().st_mode), 0o755, nom)
        self.assertEqual(stat.S_IMODE((self.pth_web / 'downloads/deploy.sh').stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(self.pth_cac.stat().st_mode), 0o700)
        self.assert_public_read(self.pth_web / 'index.php', self.pth_web / 'assets/portal.css',
                                self.pth_web / 'downloads/src/common.py', self.pth_web / 'downloads/aux-fast-boot.zip')

    def test_generation_publishes_the_prebuilt_usb_and_matching_checksums(self):
        image = (pth_repo / 'usb/aux-ipxe-usb.img').read_bytes()
        self.assertEqual(image[510:512], b'\x55\xaa')
        self.run_cmd('generate', [], umask=0o077)
        published = self.pth_web / 'downloads/usb/aux-ipxe-usb.img'
        self.assertEqual(published.read_bytes(), image)
        self.assertEqual(stat.S_IMODE(published.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(published.parent.stat().st_mode), 0o755)
        self.assert_public_read(published)
        res = subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=published.parent,
                             text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        for nom in ['index.html', 'cli.html', 'index-pxe.html', 'sitemaps-aux.xml', 'sitemaps-pxe.xml']:
            self.assertIn('downloads/usb/aux-ipxe-usb.img', (self.pth_web / nom).read_text())
        with zipfile.ZipFile(self.pth_web / 'downloads/aux-fast-boot.zip') as arc:
            self.assertEqual(arc.read('usb/aux-ipxe-usb.img'), image)
            self.assertIn('usb/build.sh', arc.namelist())
        self.assertEqual(json.loads((self.pth_web / 'catalog.json').read_text())['resources'], [])

    def test_generation_without_usb_does_not_advertise_an_image(self):
        des = self.pth_tmp / 'generate-only'
        for nom in ['generate.sh', 'src/common.py', 'src/index.html', 'src/operations.html', 'src/chroot.html', 'src/portal.css',
                    'src/portal.js', 'src/DEPLOYMENT.md', 'assets/aux-logo.png', 'assets/favicon.png']:
            pth = des / nom
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes((pth_repo / nom).read_bytes())
        res = subprocess.run(['bash', str(des / 'generate.sh'), '--output', str(self.pth_web),
                              '--cache', str(self.pth_cac)], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        for nom in ['index.html', 'cli.html', 'sitemaps.xml', 'sitemaps-pxe.xml']:
            self.assertNotIn('downloads/usb/aux-ipxe-usb.img', (self.pth_web / nom).read_text())
        self.assertFalse((self.pth_web / 'downloads/usb/aux-ipxe-usb.img').exists())

    def test_dry_run_is_read_only_and_urls_are_normalized(self):
        urls = ['https://sourceforge.net/project/example/test-amd64.iso/download'] * 2
        res = self.run_cmd('download', urls, '--dry-run')
        self.assertIn('resources=1', res.stdout)
        self.assertIn('test-amd64.iso', res.stdout)
        self.assertEqual(list(self.pth_web.iterdir()), [])
        self.assertEqual(list(self.pth_cac.iterdir()), [])

    def test_basename_collision_fails_before_writes(self):
        res = self.run_cmd('download', ['https://one.test/file.iso', 'https://two.test/file.iso'], '--dry-run', rc=1)
        self.assertIn('collision', res.stderr)
        self.assertEqual(list(self.pth_web.iterdir()), [])

    def test_generate_only_preserves_files_and_gates_missing_initrd(self):
        nom = 'debian-testing-amd64-netinst.iso'
        byt = self.make_iso(nom)
        (self.pth_web / nom).write_bytes(byt)
        (self.pth_web / 'keep.txt').write_text('unrelated content')
        tree = self.pth_web / nom[:-4] / 'debian-installer/amd64'
        tree.mkdir(parents=True)
        (tree / 'linux').write_bytes(b'kernel fixture')
        self.run_cmd('generate', ['https://example.test/' + nom])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertFalse(cat['resources'][0]['pxe_ready'])
        (tree / 'initrd.gz').write_bytes(b'initrd fixture')
        self.run_cmd('generate', ['https://example.test/' + nom])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertTrue(cat['resources'][0]['pxe_ready'])
        self.assertTrue(cat['resources'][0]['contents_ready'])
        self.assertIn('browse contents', (self.pth_web / 'cli.html').read_text())
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('cpuid --ext 29', menu)
        self.assertIn('/debian-installer/amd64/initrd.gz', menu)
        self.assertIn('initrd=initrd', menu)
        self.assertNotIn('\\n', menu)
        labels = {lin[1:] for lin in menu.splitlines() if lin.startswith(':')}
        for lin in menu.splitlines():
            if ' && item r_' in lin:
                self.assertIn(lin.split(' && item ')[1].split()[0], labels)
        self.assertEqual((self.pth_web / 'keep.txt').read_text(), 'unrelated content')
        self.assertTrue((self.pth_web / 'downloads/index.php.txt').exists())
        with zipfile.ZipFile(self.pth_web / 'downloads/aux-fast-boot.zip') as arc:
            self.assertIsNone(arc.testzip())
            self.assertIn('generate.sh', arc.namelist())
            self.assertNotIn('fast-boot.sh', arc.namelist())
            self.assertNotIn(nom, arc.namelist())
        locs = {node.text for node in ET.parse(self.pth_web / 'sitemaps.xml').getroot().iter()
                if node.tag.endswith('}loc')}
        self.assertIn('https://mirror.example.test/files/' + cat['resources'][0]['id'] + '.html', locs)
        self.assertFalse(any('keep.txt' in loc for loc in locs))

    def test_trusted_checksum_mismatch_blocks_publication_and_menu(self):
        nom = 'debian-testing-amd64-netinst.iso'
        byt = self.make_iso(nom)
        (self.pth_web / nom).write_bytes(byt)
        arc_sum = self.pth_tmp / 'trusted.txt'
        arc_sum.write_text('0' * 64 + '  ' + nom + '\n')
        self.run_cmd('generate', ['https://example.test/' + nom], '--checksums', str(arc_sum), rc=1)
        self.assertEqual((self.pth_web / nom).read_bytes(), byt)
        self.assertFalse(json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]['published'])
        self.assertEqual((self.pth_web / 'SHA256SUMS').read_text(), '')
        locs = {node.text for node in ET.parse(self.pth_web / 'sitemaps.xml').getroot().iter()
                if node.tag.endswith('}loc')}
        self.assertFalse(any('/files/' in loc or nom in loc for loc in locs))
        self.assertNotIn('kernel ', (self.pth_web / 'menu.ipxe').read_text())

    def test_native_download_and_failed_refresh_reuse_valid_cache(self):
        body = bytearray(b'MZ' + b'A' * 1022)
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_):
                pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thr = threading.Thread(target=srv.serve_forever, daemon=True)
        thr.start()
        try:
            nom = 'netboot.xyz.efi'
            url = f'http://127.0.0.1:{srv.server_port}/{nom}'
            self.run_cmd('download', [url])
            self.run_cmd('deploy-disk', [url])
            self.run_cmd('generate', [url])
            self.assertFalse((self.pth_web / nom).is_symlink())
            dig = hashlib.sha256(body).hexdigest()
            self.assertEqual(eng.obt_sha(self.pth_web / nom), dig)
            cat = json.loads((self.pth_web / 'catalog.json').read_text())
            self.assertTrue(cat['resources'][0]['pxe_ready'])
            menu = (self.pth_web / 'menu.ipxe').read_text()
            self.assertIn('iseq ${platform} efi', menu)
            self.assertIn('chain --autofree', menu)
            body[:] = b'MZ' + b'B' * 1022
            self.run_cmd('download', [url], '--refresh')
            self.run_cmd('deploy-disk', [url])
            dig = hashlib.sha256(body).hexdigest()
            self.assertEqual(eng.obt_sha(self.pth_web / nom), dig)
            body[:] = b'<!DOCTYPE html><html>invalid download</html>'
            self.run_cmd('download', [url], '--refresh', rc=1)
            self.assertEqual(eng.obt_sha(self.pth_cac / nom), dig)
            self.assertEqual(eng.obt_sha(self.pth_web / nom), dig)
            cat = json.loads((self.pth_cac / 'downloads.json').read_text())
            self.assertEqual(cat['resources'][0]['status'], 'cached-after-error')
        finally:
            srv.shutdown()
            srv.server_close()

    def test_archive_escape_is_rejected(self):
        arc = self.pth_tmp / 'bad.zip'
        with zipfile.ZipFile(arc, 'w') as z:
            z.writestr('../outside.txt', 'escape')
        des = self.pth_tmp / 'extract'
        des.mkdir()
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            dep.ext_archive(arc, des)
        self.assertFalse((self.pth_tmp / 'outside.txt').exists())

    def test_download_stage_only_writes_cache(self):
        nom = 'debian-testing-amd64-netinst.iso'
        self.make_iso(nom)
        self.run_cmd('download', ['https://example.test/' + nom])
        self.assertEqual(list(self.pth_web.iterdir()), [])
        dat = json.loads((self.pth_cac / 'downloads.json').read_text())
        self.assertEqual(dat['stage'], 'download')
        self.assertEqual(dat['resources'][0]['status'], 'cached')

    def test_disk_stage_does_not_download_or_generate(self):
        nom = 'netboot.xyz.efi'
        (self.pth_cac / nom).write_bytes(b'MZ' + b'A' * 1022)
        self.run_cmd('deploy-disk', ['https://example.test/' + nom])
        self.assertFalse((self.pth_web / nom).is_symlink())
        self.assertEqual((self.pth_web / nom).read_bytes(), (self.pth_cac / nom).read_bytes())
        self.assertFalse((self.pth_web / 'index.php').exists())
        self.assertFalse((self.pth_cac / 'downloads.json').exists())

    def test_disk_stage_missing_cache_is_an_error(self):
        self.run_cmd('deploy-disk', ['https://example.test/netboot.xyz.efi'], rc=1)
        self.assertEqual(list(self.pth_web.iterdir()), [])

    def test_generator_does_not_publish_cached_images(self):
        nom = 'debian-testing-amd64-netinst.iso'
        self.make_iso(nom)
        self.run_cmd('generate', ['https://example.test/' + nom])
        self.assertFalse((self.pth_web / nom).exists())
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual(cat['resources'], [])
        self.assertNotIn('kernel ', (self.pth_web / 'menu.ipxe').read_text())

    def test_crawler_discovers_local_images_and_fedora_boot_files(self):
        nom = 'Fedora-Server-netinst-x86_64-44-1.7.iso'
        byt = self.make_iso(nom)
        (self.pth_web / nom).write_bytes(byt)
        tree = self.pth_web / nom[:-4]
        (tree / 'images/pxeboot').mkdir(parents=True)
        (tree / 'images/pxeboot/vmlinuz').write_bytes(b'kernel')
        (tree / 'images/pxeboot/initrd.img').write_bytes(b'initrd')
        (tree / 'images/install.img').write_bytes(b'stage2')
        (tree / '.treeinfo').write_text('[stage2]\nmainimage = images/install.img\n')
        extra = 'debian-extra-amd64-netinst.iso'
        (self.pth_web / extra).write_bytes(byt)
        (self.pth_cac / 'downloads.json').write_text(json.dumps({'resources': [{'filename': nom, 'url': 'https://example.test/releases/44/Server/x86_64/iso/' + nom}]}))
        self.run_cmd('generate', [])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual(len(cat['resources']), 2)
        self.assertTrue(cat['resources'][0]['pxe_ready'])
        self.assertTrue(cat['resources'][0]['contents_ready'])
        self.assertIn('inst.stage2=http://127.0.0.1:8080/', (self.pth_web / 'menu.ipxe').read_text())
        self.assertIn('inst.repo=https://example.test/releases/44/Server/x86_64/os/', (self.pth_web / 'menu.ipxe').read_text())

    def test_fedora_netinst_without_treeinfo_for_both_architectures(self):
        resources = []
        for arq, menu_arq in [('x86_64', 'x86_64'), ('aarch64', 'arm64')]:
            nom = f'Fedora-Server-netinst-{arq}-44-1.7.iso'
            (self.pth_web / nom).write_bytes(self.make_iso(nom))
            tree = self.pth_web / nom[:-4]
            for path, data in [('images/pxeboot/vmlinuz', b'original-kernel'),
                               ('images/pxeboot/initrd.img', b'original-initrd'),
                               ('images/install.img', b'original-stage2')]:
                pth = tree / path
                pth.parent.mkdir(parents=True, exist_ok=True)
                pth.write_bytes(data)
            resources.append({'filename': nom, 'url': f'https://mirror.example.test/releases/44/Server/{arq}/iso/{nom}'})
        (self.pth_cac / 'downloads.json').write_text(json.dumps({'resources': resources}))
        self.run_cmd('generate', [])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertEqual(len(cat['resources']), 2)
        self.assertTrue(all(rec['pxe_ready'] and rec['boot_group'] == 'netboot' for rec in cat['resources']))
        for rec in cat['resources']:
            arq = 'aarch64' if rec['arch'] == 'arm64' else rec['arch']
            self.assertIn(f'inst.repo=https://mirror.example.test/releases/44/Server/{arq}/os/', menu)
            self.assertIn(f'iseq ${{cpu_arch}} {rec["arch"]} && item {rec["id"]}', menu)
            self.assertEqual(rec['boot_files']['stage2'], 'images/install.img')
            self.assertFalse((self.pth_web / rec['tree'] / '.treeinfo').exists())

    def test_fedora_assistance_keeps_selector_and_its_own_http_runtime(self):
        nom = 'pxe-fedora44-assist-0.1.0-x86_64.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4]
        for rel in ['images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img', 'images/install.img']:
            pth = tree / rel
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'custom-assistance-media')
        conf = tree / 'EFI/BOOT/grub.cfg'
        conf.parent.mkdir(parents=True)
        conf.write_text('linux /images/pxeboot/vmlinuz inst.stage2=hd:LABEL=Fedora '
                        'aux.assist inst.rescue ip=dhcp rd.neednet=1 quiet\n'
                        'initrd /images/pxeboot/initrd.img\n')
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertTrue(rec['pxe_ready'])
        self.assertEqual(rec['category'], 'assistance')
        self.assertIn('0. Remote assistance', menu)
        self.assertIn('inst.stage2=http://127.0.0.1:8080/' + nom[:-4] + '/ aux.assist inst.rescue', menu)
        self.assertNotIn('hd:LABEL=', menu)
        self.assertNotIn('inst.repo=', menu)
        # Missing custom runtime must never fall back to a normal installer or Live image.
        (tree / 'images/install.img').unlink()
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])
        # A name alone cannot enable remote assistance.
        (tree / 'images/install.img').write_bytes(b'normal-runtime')
        conf.write_text(conf.read_text().replace('aux.assist ', ''))
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertEqual(rec['category'], 'distribution')
        self.assertNotIn('aux.assist', (self.pth_web / 'menu.ipxe').read_text())

    def test_fedora_live_assistance_uses_its_own_rootfs_and_ram_overlay(self):
        nom = 'tech-fedora44-assist-5.0.1-dev.0-x86_64.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4]
        for rel in ('images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img',
                    'LiveOS/squashfs.img'):
            pth = tree / rel
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'custom-live-assistance')
        conf = tree / 'EFI/BOOT/grub.cfg'
        conf.parent.mkdir(parents=True)
        conf.write_text('linux /images/pxeboot/vmlinuz root=live:CDLABEL=TECH '
                        'rd.live.image aux.assist rd.live.overlay.overlayfs=1\n'
                        'initrd /images/pxeboot/initrd.img\n')
        # Live boot flags remain authoritative even if generic metadata has a stage2 field.
        (tree / '.treeinfo').write_text('[stage2]\nmainimage = LiveOS/squashfs.img\n')
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertTrue(rec['pxe_ready'])
        self.assertEqual(rec['boot_group'], 'tools')
        self.assertEqual(rec['boot_files']['live'], 'LiveOS/squashfs.img')
        self.assertIn('root=live:http://127.0.0.1:8080/' + nom[:-4] +
                      '/LiveOS/squashfs.img aux.assist rd.live.overlay.overlayfs=1', menu)
        self.assertNotIn('inst.rescue', menu)
        self.assertNotIn('inst.stage2=', menu)
        self.assertNotIn('CDLABEL=', menu)
        (tree / 'LiveOS/squashfs.img').unlink()
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])

    def test_aux_rescue_names_require_media_marker_before_automatic_assistance_boot(self):
        alias = eng.obt_meta('https://example.test/aux-rescue.iso')
        self.assertEqual((alias['category'], alias['family'], alias['arch']), ('assistance', 'fedora', 'x86_64'))
        name = 'aux-rescue-5.0.1-dev.5-x86_64.iso'
        (self.pth_web / name).write_bytes(self.make_iso(name))
        tree = self.pth_web / name[:-4]
        for path in ['images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img', 'LiveOS/squashfs.img']:
            target = tree / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'aux rescue fixture')
        config = tree / 'EFI/BOOT/grub.cfg'
        config.parent.mkdir(parents=True)
        config.write_text('linux /images/pxeboot/vmlinuz rd.live.image\ninitrd /images/pxeboot/initrd.img\n')
        self.run_cmd('generate', [])
        record = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(record['pxe_ready'])
        self.assertIn('set auto_timeout 0', (self.pth_web / 'menu.ipxe').read_text())
        self.assertNotIn('set auto_timeout 60000', (self.pth_web / 'menu.ipxe').read_text())
        config.write_text(config.read_text().replace('rd.live.image', 'rd.live.image aux.assist'))
        self.run_cmd('generate', [])
        record = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertTrue(record['pxe_ready'])
        self.assertEqual(record['name'], 'AUX Rescue / Remote assistance')
        self.assertIn('set auto_timeout 60000', (self.pth_web / 'menu.ipxe').read_text())

    def test_fedora_original_stage2_paths_override_live_and_fallback_paths(self):
        nom = 'Fedora-Server-netinst-x86_64-44-1.7.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4]
        for path in ['images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img',
                     'images/install.img', 'LiveOS/custom-stage2.img', 'LiveOS/squashfs.img']:
            pth = tree / path
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'original-image-data')
        (tree / '.treeinfo').write_text('[stage2]\nmainimage = LiveOS/custom-stage2.img\n')
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertEqual(rec['boot_group'], 'netboot')
        self.assertEqual(rec['boot_files']['stage2'], 'LiveOS/custom-stage2.img')
        self.assertNotIn('root=live:', (self.pth_web / 'menu.ipxe').read_text())
        (tree / 'LiveOS/custom-stage2.img').unlink()
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])
        self.assertIn('LiveOS/custom-stage2.img', rec['pxe_reason'])
        (tree / '.treeinfo').write_text('[stage2]\nmainimage = ../private-stage2.img\n')
        (self.pth_web / 'private-stage2.img').write_bytes(b'private-stage2')
        self.run_cmd('generate', [])
        rec = next(rec for rec in json.loads((self.pth_web / 'catalog.json').read_text())['resources'] if rec['filename'] == nom)
        self.assertFalse(rec['pxe_ready'])

    def test_fedora_live_uses_original_bootloader_paths_and_live_settings(self):
        tree = self.pth_web / 'units/Fedora-Workstation-Live-44-aarch64'
        for path in ['boot/aarch64/loader/linux', 'boot/aarch64/loader/initrd', 'payload/live/root.sqfs']:
            pth = tree / path
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'original-live-content')
        conf = tree / 'boot/grub2/grub.cfg'
        conf.parent.mkdir(parents=True)
        conf.write_text('linux ($root)/boot/aarch64/loader/linux root=live:CDLABEL=Fedora '
                        'rd.live.image rd.live.dir=/payload/live rd.live.squashimg=root.sqfs\n'
                        'initrd ($root)/boot/aarch64/loader/initrd\n')
        originals = {pth.relative_to(tree).as_posix(): pth.read_bytes() for pth in tree.rglob('*') if pth.is_file()}
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertEqual(rec['arch'], 'arm64')
        self.assertEqual(rec['boot_group'], 'live')
        self.assertEqual(rec['source_boot_config'], 'boot/grub2/grub.cfg')
        self.assertEqual(rec['boot_files']['live'], 'payload/live/root.sqfs')
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('/boot/aarch64/loader/linux initrd=initrd', menu)
        self.assertIn('/payload/live/root.sqfs rd.live.dir=/payload/live rd.live.squashimg=root.sqfs', menu)
        self.assertNotIn('/LiveOS/squashfs.img', menu)
        self.assertEqual(originals, {pth.relative_to(tree).as_posix(): pth.read_bytes() for pth in tree.rglob('*') if pth.is_file()})
        (tree / 'payload/live/root.sqfs').unlink()
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])
        self.assertIn('payload/live/root.sqfs', rec['pxe_reason'])

    def test_fedora_live_44_loader_layout_is_detected_from_an_iso(self):
        nom = 'Fedora-Workstation-Live-44-1.7.x86_64.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4]
        for path in ['boot/x86_64/loader/linux', 'boot/x86_64/loader/initrd', 'LiveOS/squashfs.img']:
            pth = tree / path
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'original-f44-live')
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertEqual(rec['boot_group'], 'live')
        self.assertIn('/boot/x86_64/loader/linux', (self.pth_web / 'menu.ipxe').read_text())

    def test_fedora_netinst_without_runtime_stays_out_of_the_menu(self):
        nom = 'Fedora-Server-netinst-x86_64-44-1.7.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4] / 'images/pxeboot'
        tree.mkdir(parents=True)
        (tree / 'vmlinuz').write_bytes(b'kernel')
        (tree / 'initrd.img').write_bytes(b'initrd')
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])
        self.assertIn('installer runtime missing', rec['pxe_reason'])
        self.assertNotIn('kernel ', (self.pth_web / 'menu.ipxe').read_text())

    def test_fedora_declared_kernel_paths_do_not_fall_back_to_different_files(self):
        nom = 'Fedora-Server-netinst-x86_64-44-1.7.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4]
        for path in ['images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img', 'images/install.img',
                     'original/kernel', 'original/initrd']:
            pth = tree / path
            pth.parent.mkdir(parents=True, exist_ok=True)
            pth.write_bytes(b'media-content')
        (tree / '.treeinfo').write_text('[images-x86_64]\nkernel = original/kernel\ninitrd = original/initrd\n'
                                      '[stage2]\nmainimage = images/install.img\n')
        self.run_cmd('generate', [])
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('/original/kernel initrd=initrd', menu)
        self.assertNotIn('/images/pxeboot/vmlinuz', menu)
        (tree / 'original/initrd').unlink()
        self.run_cmd('generate', [])
        rec = json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]
        self.assertFalse(rec['pxe_ready'])
        self.assertIn('declared in .treeinfo', rec['pxe_reason'])

    def test_stale_prepared_tree_is_excluded_until_redeployment(self):
        nom = 'debian-testing-amd64-netinst.iso'
        byt = self.make_iso(nom)
        (self.pth_web / nom).write_bytes(byt)
        rec = eng.obt_meta('https://example.test/' + nom)
        tree = self.pth_web / rec['tree']
        (tree / 'install.amd').mkdir(parents=True)
        (tree / 'install.amd/vmlinuz').write_bytes(b'kernel')
        (tree / 'install.amd/initrd.gz').write_bytes(b'initrd')
        cfg = SimpleNamespace(output=self.pth_web, cache=self.pth_cac)
        eng.esc_atomic(eng.obt_estado(cfg, 'tree-state', rec), json.dumps({'tree': str(tree), 'sha256': '0' * 64}))
        self.run_cmd('generate', [rec['url']], rc=1)
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertFalse(cat['resources'][0]['pxe_ready'])
        self.assertFalse(cat['resources'][0]['contents_ready'])

    def test_ram_copy_symlink_and_mount_command(self):
        nom = 'debian-testing-amd64-netinst.iso'
        byt = self.make_iso(nom)
        (self.pth_web / nom).write_bytes(byt)
        rec = eng.obt_meta('https://example.test/' + nom)
        rec.update(size=len(byt), sha256=hashlib.sha256(byt).hexdigest(), status='cached')
        cfg = SimpleNamespace(output=self.pth_web, cache=self.pth_cac, ram_dir=self.pth_tmp / 'ram',
                              mode='ram', quiet=True)
        with patch.object(dep.subprocess, 'run', return_value=SimpleNamespace(stdout='tmpfs\n')) as run:
            dep.prep_ram(rec, cfg)
        self.assertEqual((cfg.ram_dir / nom).read_bytes(), byt)
        self.assertTrue((self.pth_web / nom).is_symlink())
        self.assertEqual((self.pth_web / nom).resolve(), cfg.ram_dir / nom)
        self.assertTrue(any(call.args[0][0] == 'mount' and str(cfg.ram_dir / nom) in call.args[0] for call in run.call_args_list))

    def test_ram_archive_preflight_counts_extraction_before_copy_and_publication(self):
        nom = 'debian-netboot-amd64.tar.gz'
        arc = self.pth_cac / nom
        with tarfile.open(arc, 'w:gz') as archive:
            data = b'0' * (1024 * 1024)
            ent = tarfile.TarInfo('debian-installer/amd64/linux')
            ent.size = len(data)
            archive.addfile(ent, io.BytesIO(data))
        rec = eng.obt_meta('https://source.invalid/' + nom)
        rec.update(size=arc.stat().st_size, sha256=eng.obt_sha(arc), status='cached')
        cfg = SimpleNamespace(output=self.pth_web, cache=self.pth_cac, ram_dir=self.pth_tmp / 'ram',
                              mode='ram', quiet=True)
        # The compressed download fits, but the root tree plus download cannot fit.
        free = rec['size'] + 16 * 1024 * 1024 + 1024
        with patch.object(dep.subprocess, 'run', return_value=SimpleNamespace(stdout='tmpfs\n')), \
             patch.object(dep.shutil, 'disk_usage', return_value=SimpleNamespace(free=free)), \
             patch.object(dep.shutil, 'copy2') as copy, patch.object(dep, 'pub_rec') as publish:
            with self.assertRaisesRegex(ValueError, 'including extraction'):
                dep.prep_ram(rec, cfg)
            copy.assert_not_called()
            publish.assert_not_called()
        self.assertFalse((cfg.ram_dir / nom).exists())
        self.assertGreaterEqual(dep.tam_expandido(arc), len(data))

    def test_read_only_iso_selinux_mount_context_is_explicit_and_validated(self):
        nom = 'fedora-assist-x86_64.iso'
        byt = self.make_iso(nom)
        rec = eng.obt_meta('https://example.test/' + nom)
        rec.update(size=len(byt), sha256=hashlib.sha256(byt).hexdigest(), status='cached')
        ctx = 'system_u:object_r:httpd_sys_content_t:s0'
        cfg = SimpleNamespace(output=self.pth_web, cache=self.pth_cac, mode='mount',
                              mount_context=ctx, quiet=True)
        with patch.object(dep.subprocess, 'run') as run:
            dep.pub_rec(rec, cfg, self.pth_cac / nom)
        self.assertIn('loop,ro,nosuid,nodev,noexec,context=' + ctx, run.call_args.args[0])
        with patch('sys.argv', ['deploy.sh', 'disk', '--mode', 'mount', '--mount-context', ctx]):
            self.assertEqual(dep.obt_args('deploy', pth_repo).mount_context, ctx)
        for flags in [['disk', '--mount-context', ctx],
                      ['disk', '--mode', 'mount', '--mount-context', ctx + ',rw']]:
            with patch('sys.argv', ['deploy.sh', *flags]), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    dep.obt_args('deploy', pth_repo)

    def test_shared_config_paths_are_relative_to_the_config_file(self):
        arc_cfg = self.pth_tmp / 'config.json'
        arc_cfg.write_text(json.dumps({'output': 'html', 'cache': 'cache', 'jobs': 2}))
        with patch('sys.argv', ['deploy.sh', 'disk', '--config', str(arc_cfg)]):
            cfg = dep.obt_args('deploy', pth_repo)
        self.assertEqual(cfg.output, self.pth_web)
        self.assertEqual(cfg.cache, self.pth_cac)
        self.assertEqual(cfg.mode, 'extract')
        self.assertEqual(cfg.jobs, 2)

    @unittest.skipUnless(eng.os.geteuid() == 0 and Path('/dev/shm').is_dir(), 'RAM stage requires root and tmpfs')
    def test_separate_commands_http_ram_disk_and_generation(self):
        body = b'MZ' + b'A' * 8190
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_):
                pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            nom = 'netboot.xyz.efi'
            arc_urls = self.pth_tmp / 'urls.txt'
            arc_urls.write_text(f'http://127.0.0.1:{srv.server_port}/{nom}\n')
            args = ['--cache', str(self.pth_cac),
                    '--output', str(self.pth_web), '--base-url', 'https://mirror.example.test',
                    '--pxe-url', 'http://127.0.0.1:8080']
            def stage(cmd, extra=()):
                entrada = ['--url-file', str(arc_urls)] if cmd == 'download.sh' else []
                res = subprocess.run(['bash', str(pth_repo / cmd), *extra, *args, *entrada], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            with tempfile.TemporaryDirectory(prefix='aux-ram-test-', dir='/dev/shm') as ram:
                stage('download.sh')
                self.assertEqual(requests, ['/' + nom])
                self.assertEqual(list(self.pth_web.iterdir()), [])
                stage('deploy.sh', ['ram', '--ram-dir', ram])
                self.assertTrue((self.pth_web / nom).is_symlink())
                self.assertEqual((self.pth_web / nom).resolve(), Path(ram) / nom)
                self.assertEqual((Path(ram) / nom).read_bytes(), body)
                self.assertFalse((self.pth_web / 'index.php').exists())
                stage('generate.sh')
                cat = json.loads((self.pth_web / 'catalog.json').read_text())
                self.assertTrue(cat['resources'][0]['pxe_ready'])
                stage('deploy.sh', ['disk'])
                self.assertFalse((self.pth_web / nom).is_symlink())
                self.assertEqual((self.pth_web / nom).read_bytes(), body)
                stage('generate.sh')
                self.assertEqual(requests, ['/' + nom])
        finally:
            srv.shutdown()
            srv.server_close()

    def test_bundle_contains_three_programs_and_runs_without_url_list(self):
        with zipfile.ZipFile(pth_repo / 'dist/downloads/aux-fast-boot.zip') as arc:
            des = self.pth_tmp / 'bundle'
            arc.extractall(des)
            for nom in ['download.sh', 'deploy.sh', 'generate.sh', 'url.txt', 'light-url.txt', 'heavy-url.txt',
                        'fast-boot.json', 'src/common.py', 'TESTING.md']:
                self.assertIn(nom, arc.namelist())
            for nom in ['fast-boot.sh', 'deploy-ram.sh', 'deploy-disk.sh', 'src/engine.py']:
                self.assertNotIn(nom, arc.namelist())
            self.assertFalse(any(nom.startswith(('downloads/', 'src/fast_boot/')) for nom in arc.namelist()))
            self.assertIn('@@ROWS@@', (des / 'src/index.html').read_text())
        res = subprocess.run(['bash', str(des / 'download.sh'), '--dry-run', '--only', 'fedora'], text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn(f'download {eng.VERSION}', res.stdout)
        self.assertIn('resources=6', res.stdout)
        # The next commands inspect real files, with neither a URL list nor the downloader present.
        (des / 'url.txt').unlink()
        (des / 'download.sh').unlink()
        nom = 'netboot.xyz.efi'
        (self.pth_cac / nom).write_bytes(b'MZ' + b'A' * 1022)
        args = ['--output', str(self.pth_web), '--cache', str(self.pth_cac),
                '--base-url', 'https://mirror.example.test', '--pxe-url', 'http://127.0.0.1:8080']
        res = subprocess.run(['bash', str(des / 'deploy.sh'), 'disk', *args], text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        (des / 'deploy.sh').unlink()
        res = subprocess.run(['bash', str(des / 'generate.sh'), *args], text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertTrue(json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]['pxe_ready'])

    def test_downloader_needs_no_other_program_or_visual_assets(self):
        des = self.pth_tmp / 'download-only'
        (des / 'src').mkdir(parents=True)
        for nom in ['download.sh', 'src/common.py']:
            (des / nom).write_bytes((pth_repo / nom).read_bytes())
        nom = 'netboot.xyz.efi'
        body = b'MZ' + b'isolated downloader'
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_):
                pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            (des / 'url.txt').write_text(f'http://127.0.0.1:{srv.server_port}/{nom}\n')
            res = subprocess.run(['bash', str(des / 'download.sh'), '--cache', str(self.pth_cac),
                                  '--output', str(self.pth_web)], text=True, capture_output=True)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertEqual((self.pth_cac / nom).read_bytes(), body)
            self.assertEqual(list(self.pth_web.iterdir()), [])
            self.assertIn('PROGRESS', res.stderr)
            self.assertIn('SHA-256', res.stderr)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_deployer_needs_no_downloader_generator_or_templates(self):
        des = self.pth_tmp / 'deploy-only'
        (des / 'src').mkdir(parents=True)
        for nom in ['deploy.sh', 'src/common.py']:
            (des / nom).write_bytes((pth_repo / nom).read_bytes())
        nom = 'netboot.xyz.efi'
        body = b'MZ' + b'isolated deployer'
        (self.pth_cac / nom).write_bytes(body)
        res = subprocess.run(['bash', str(des / 'deploy.sh'), 'disk', '--cache', str(self.pth_cac),
                              '--output', str(self.pth_web)], text=True, capture_output=True)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertEqual((self.pth_web / nom).read_bytes(), body)
        self.assertFalse((self.pth_web / 'index.php').exists())

    @unittest.skipUnless(eng.os.geteuid() == 0 and Path('/dev/shm').is_dir(), 'RAM requires tmpfs')
    def test_same_tar_cache_to_ram_then_persistent_disk_after_ram_loss(self):
        nom = 'debian-netboot-amd64.tar.gz'
        payloads = {'debian-installer/amd64/linux': b'network-kernel',
                    'debian-installer/amd64/initrd.gz': b'network-initrd'}
        with tarfile.open(self.pth_cac / nom, 'w:gz') as arc:
            for name, data in payloads.items():
                ent = tarfile.TarInfo(name)
                ent.size = len(data)
                ent.mode = 0o644
                arc.addfile(ent, io.BytesIO(data))
        dig = eng.obt_sha(self.pth_cac / nom)
        with tempfile.TemporaryDirectory(prefix='aux-unit-test-', dir='/dev/shm') as ram:
            self.run_cmd('deploy-ram', [], '--ram-dir', ram)
            self.assertTrue((self.pth_web / nom).is_symlink())
            tree = self.pth_web / nom[:-7]
            self.assertTrue(tree.is_symlink())
            self.assertEqual(tree.resolve(), Path(ram) / nom[:-7])
            self.run_cmd('generate', [])
            self.assertTrue(json.loads((self.pth_web / 'catalog.json').read_text())['resources'][0]['pxe_ready'])
            eng.shutil.rmtree(Path(ram) / nom[:-7])
            (Path(ram) / nom).unlink()
            self.run_cmd('generate', [])
            self.assertEqual(json.loads((self.pth_web / 'catalog.json').read_text())['resources'], [])
            self.run_cmd('deploy-disk', [])
            self.assertFalse((self.pth_web / nom).is_symlink())
            self.assertFalse(tree.is_symlink())
            for name, data in payloads.items():
                self.assertEqual((tree / name).read_bytes(), data)
            self.assertEqual(eng.obt_sha(self.pth_cac / nom), dig)
            self.assertEqual(eng.obt_sha(self.pth_web / nom), dig)

    def test_crawler_nested_files_directory_links_cycles_and_distinct_paths(self):
        nom = 'netboot.xyz.efi'
        (self.pth_web / 'disk').mkdir()
        (self.pth_web / 'disk' / nom).write_bytes(b'MZpayload')
        external = self.pth_tmp / 'ram-units'
        external.mkdir()
        (external / nom).write_bytes(b'MZram-payload')
        (self.pth_web / 'ram').symlink_to(external, target_is_directory=True)
        (external / 'cycle').symlink_to(self.pth_web, target_is_directory=True)
        (self.pth_web / 'dead.efi').symlink_to(external / 'missing.efi')
        self.run_cmd('generate', [])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual({rec['path'] for rec in cat['resources']}, {'ram/' + nom, 'disk/' + nom})
        self.assertEqual(len({rec['id'] for rec in cat['resources']}), 2)
        self.assertTrue(all(rec['pxe_ready'] for rec in cat['resources']))
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('/ram/' + nom, menu)
        self.assertIn('/disk/' + nom, menu)
        self.assertNotIn('dead.efi', menu)
        self.assertIn('/ram/' + nom, (self.pth_web / 'cli.html').read_text())

    def test_live_trees_boot_payload_gates_and_uefi_initrd_names(self):
        fixtures = {
            'fedora-live-x86_64': {'images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img', 'LiveOS/squashfs.img'},
            'debian-live-amd64': {'live/vmlinuz', 'live/initrd.img', 'live/filesystem.squashfs'},
            'archlinux-x86_64': {'arch/boot/x86_64/vmlinuz-linux', 'arch/boot/x86_64/initramfs-linux.img', 'arch/x86_64/airootfs.erofs'},
        }
        for nom, names in fixtures.items():
            for name in names:
                arc = self.pth_web / 'units' / nom / name
                arc.parent.mkdir(parents=True, exist_ok=True)
                arc.write_bytes(b'boot-fixture')
        args = ('--live-url', 'http://192.0.2.42')
        self.run_cmd('generate', [], *args)
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual(len(cat['resources']), 3)
        self.assertTrue(all(rec['pxe_ready'] and rec['format'] == 'TREE' for rec in cat['resources']))
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('root=live:http://127.0.0.1:8080/units/fedora-live-x86_64/LiveOS/squashfs.img', menu)
        self.assertIn('fetch=http://192.0.2.42/units/debian-live-amd64/live/filesystem.squashfs', menu)
        self.assertIn('archiso_http_srv=http://127.0.0.1:8080/units/archlinux-x86_64/', menu)
        for lin in menu.splitlines():
            if lin.startswith('kernel '):
                self.assertIn('initrd=initrd', lin)
        (self.pth_web / 'units/fedora-live-x86_64/LiveOS/squashfs.img').write_bytes(b'')
        (self.pth_web / 'units/debian-live-amd64/live/initrd.img').unlink()
        self.run_cmd('generate', [], *args)
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual(sum(rec['pxe_ready'] for rec in cat['resources']), 1)

    def test_cdrom_installer_is_not_mislabelled_as_network_installer(self):
        nom = 'debian-testing-amd64-netinst.iso'
        (self.pth_web / nom).write_bytes(self.make_iso(nom))
        tree = self.pth_web / nom[:-4] / 'install.amd'
        tree.mkdir(parents=True)
        (tree / 'vmlinuz').write_bytes(b'cd-kernel')
        (tree / 'initrd.gz').write_bytes(b'cd-initrd')
        self.run_cmd('generate', [])
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertFalse(cat['resources'][0]['pxe_ready'])
        self.assertTrue(cat['resources'][0]['published'])
        self.assertNotIn('kernel ', (self.pth_web / 'menu.ipxe').read_text())

    def test_bastion_default_never_changes_pxe_and_contents_paths(self):
        nom = 'ubuntu-24.04-live-server-amd64.iso'
        (self.pth_web / 'releases').mkdir()
        (self.pth_web / 'releases' / nom).write_bytes(self.make_iso(nom))
        # A public RAM link must be browsable without writing an index into the image.
        ram = self.pth_tmp / 'ram-image'
        (ram / 'casper').mkdir(parents=True)
        original = {'casper/vmlinuz': b'kernel', 'casper/initrd': b'initrd',
                    'casper/filesystem.squashfs': b'filesystem', 'read + me.txt': b'readme',
                    '<script>.txt': b'escaped-name', '.discinfo': b'installer metadata'}
        for rel, value in original.items():
            (ram / rel).write_bytes(value)
        (ram / 'casper/loop').symlink_to(ram, target_is_directory=True)
        (self.pth_tmp / 'private-key').write_text('must not appear')
        (ram / 'outside').symlink_to(self.pth_tmp / 'private-key')
        (ram / '.private').write_text('must not appear')
        (self.pth_web / 'releases' / nom[:-4]).symlink_to(ram, target_is_directory=True)
        self.run_cmd('generate', [], '--download-url', 'https://bastion.example.test/media/')
        cat = json.loads((self.pth_web / 'catalog.json').read_text())
        self.assertEqual(cat['default_server'], 'bastion')
        self.assertEqual(cat['download_url'], 'https://bastion.example.test/media')
        self.assertEqual(len(cat['resources']), 1)
        rec = cat['resources'][0]
        self.assertEqual(rec['download_urls']['bastion'], 'https://bastion.example.test/media/releases/' + nom)
        self.assertEqual(rec['download_urls']['excalibur'], 'http://127.0.0.1:8080/releases/' + nom)
        self.assertEqual(rec['contents_files'], len(original))
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('url=http://127.0.0.1:8080/releases/' + nom, menu)
        self.assertIn('Distros / Ubuntu / Install', menu)
        self.assertNotIn('bastion.example.test', menu)
        pages = list((self.pth_web / 'contents' / rec['id']).glob('*.html'))
        self.assertEqual(len(pages), 2)
        all_links = []
        for page in pages:
            parser = PortalTests.Parser()
            parser.feed(page.read_text())
            all_links += parser.links
            for link in parser.links:
                part = urlsplit(link)
                if not part.scheme and part.path:
                    self.assertTrue((page.parent / unquote(part.path)).is_file(), link)
            rel = page.relative_to(self.pth_web).as_posix()
            self.assertIn('https://mirror.example.test/' + rel, parser.links)
            self.assertIn('http://127.0.0.1:8080/' + rel, parser.links)
            self.assertFalse({'script', 'img', 'input', 'button', 'link'} & set(parser.tags))
        for rel, value in original.items():
            self.assertIn('http://127.0.0.1:8080/releases/' + nom[:-4] + '/' + quote(rel, safe='/'), all_links)
            self.assertEqual((ram / rel).read_bytes(), value)
        self.assertFalse(any('/outside' in link or '/loop' in link or '/.private' in link for link in all_links))
        self.assertFalse((ram / 'index.html').exists())
        self.assertIn(rec['contents_path'], (self.pth_web / 'index.html').read_text())
        self.assertIn(rec['contents_path'], (self.pth_web / 'cli.html').read_text())
        for name, base in [('sitemaps.xml', 'https://mirror.example.test'), ('sitemaps-pxe.xml', 'http://127.0.0.1:8080')]:
            locs = [node.text for node in ET.parse(self.pth_web / name).getroot().iter() if node.tag.endswith('}loc')]
            self.assertTrue(all(loc.startswith(base + '/') for loc in locs))
            self.assertIn(base + '/contents/' + rec['id'] + '/index.html', locs)
        # Generated contents pages must not be rediscovered as boot trees on a second crawl.
        self.run_cmd('generate', [], '--download-url', 'https://bastion.example.test/media')
        self.assertEqual(len(json.loads((self.pth_web / 'catalog.json').read_text())['resources']), 1)

    def test_distro_and_tool_classification_is_shared_by_catalog_and_menu(self):
        records = [eng.obt_meta('https://source.test/' + name) for name in
                   ['ipxe-arch.efi', 'netboot.xyz.efi', 'gparted-live-amd64.iso', 'kali-installer-amd64.iso', 'proxmox-ve.iso']]
        for rec in records:
            rec['_boot'] = {'group': 'live' if rec['family'] == 'gparted' else 'netboot',
                            'commands': ['echo fixture'], 'firmware': None}
        self.assertEqual([rec['category'] for rec in records], ['distribution', 'tools', 'tools', 'distribution', 'distribution'])
        cfg = SimpleNamespace(pxe_url='http://pxe.example.test', base_url='https://aux.example.test')
        menu = eng.gen_ipxe(records, cfg)
        tree = eng.gen_arbol(records)
        self.assertEqual(set(eng.obt_ids(tree[2])), {records[1]['id'], records[2]['id']})
        self.assertIn('menu Tools / GParted', menu)
        self.assertIn('menu Distros / Arch Linux / Netinstall', menu)
        self.assertIn('nav_distribution_arch_netinstall', eng.gen_rows(records, cfg))
        self.assertIn('2. Tools</h2>', eng.gen_cli_page(records, cfg))

    def test_ftp_root_merge_deduplicates_payloads_and_rejects_collisions(self):
        nom = 'debian-amd64-netinst.iso'
        self.make_iso(nom)
        (self.pth_cac / 'downloads.json').write_text('{"resources": []}')
        (self.pth_cac / 'unfinished.iso.part').write_bytes(b'incomplete')
        (self.pth_web / nom).symlink_to(self.pth_cac / nom)
        (self.pth_web / 'assets').mkdir()
        (self.pth_web / 'assets/style.css').write_text('body{}')
        (self.pth_web / 'index.php').write_text('<?php echo "mirror"; ?>')
        (self.pth_web / '.secret').write_text('private')
        ram = self.pth_tmp / 'ram'
        ram.mkdir()
        (ram / 'kernel').write_bytes(b'kernel')
        (ram / '.treeinfo').write_text('[general]')
        (self.pth_web / 'distro').symlink_to(ram, target_is_directory=True)
        cfg = SimpleNamespace(cache=self.pth_cac, output=self.pth_web, ram_dir=ram,
                              only=None, checksums=None, pxe_url='http://pxe.test', quiet=True)
        plan = dep.plan_ftp(cfg)
        paths = [item['relative'] for item in plan]
        self.assertEqual(set(paths), {nom, 'assets/style.css', 'index.php', 'distro/kernel', 'distro/.treeinfo'})
        self.assertEqual(paths.count(nom), 1)
        self.assertEqual(paths[-1], 'index.php')
        self.assertTrue(all(item['path'].is_file() and not item['path'].is_symlink() for item in plan))
        before = sorted(str(path) for path in self.pth_tmp.rglob('*'))
        out = self.run_cmd('deploy-ftp', [], '--ram-dir', str(ram), '--dry-run', '--ftp-root', '/')
        self.assertIn('-> /' + nom, out.stdout)
        self.assertNotIn('-> /isos/', out.stdout)
        self.assertEqual(before, sorted(str(path) for path in self.pth_tmp.rglob('*')))
        (self.pth_web / nom).unlink()
        (self.pth_web / nom).write_bytes(b'different payload')
        with self.assertRaisesRegex(ValueError, 'collision'):
            dep.plan_ftp(cfg)
        (self.pth_web / nom).unlink()
        (self.pth_web / 'escape').symlink_to(self.pth_tmp / 'outside')
        (self.pth_tmp / 'outside').write_bytes(b'outside root')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            dep.plan_ftp(cfg)
        (self.pth_web / 'escape').unlink()
        (ram / 'cycle').symlink_to(ram, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'cycle'):
            dep.plan_ftp(cfg)

    def test_ftp_real_passive_transfer_resume_rename_and_directory_creation(self):
        remote = self.pth_tmp / 'remote'
        remote.mkdir()
        nom = 'debian-amd64-netinst.iso'
        data = bytes(self.make_iso(nom))
        (self.pth_web / 'assets').mkdir()
        (self.pth_web / 'assets/style.css').write_bytes(b'body{}')
        (self.pth_web / 'index.html').write_bytes(b'<h1>mirror</h1>')
        (remote / nom).write_bytes(b'previous public copy')
        tmp = '.aux-upload-' + hashlib.sha256(data).hexdigest() + '.part'
        (remote / tmp).write_bytes(data[:1234])
        commands = []
        interrupt = {'pending': True}
        class Handler(socketserver.StreamRequestHandler):
            def handle(self):
                cwd, rest, listener, rename = remote, 0, None, None
                def reply(line):
                    self.wfile.write((line + '\r\n').encode())
                    self.wfile.flush()
                reply('220 Local FTP fixture')
                try:
                    while True:
                        raw = self.rfile.readline()
                        if not raw:
                            break
                        cmd, _, arg = raw.decode().rstrip('\r\n').partition(' ')
                        commands.append((cmd, '[hidden]' if cmd == 'PASS' else arg))
                        path = (remote / arg.lstrip('/')) if arg.startswith('/') else cwd / arg
                        if cmd in ('USER', 'PASS', 'TYPE'):
                            reply('331 Password' if cmd == 'USER' else '230 Logged in' if cmd == 'PASS' else '200 Binary')
                        elif cmd == 'CWD':
                            if path.is_dir():
                                cwd = path
                                reply('250 Directory')
                            else:
                                reply('550 Missing directory')
                        elif cmd == 'MKD':
                            path.mkdir()
                            reply('257 Created')
                        elif cmd == 'SIZE':
                            reply('213 ' + str(path.stat().st_size) if path.is_file() else '550 Missing file')
                        elif cmd == 'PASV':
                            listener = socket.socket()
                            listener.bind(('127.0.0.1', 0))
                            listener.listen(1)
                            port = listener.getsockname()[1]
                            reply(f'227 Passive (127,0,0,1,{port // 256},{port % 256})')
                        elif cmd == 'REST':
                            rest = int(arg)
                            reply('350 Restart accepted')
                        elif cmd == 'STOR':
                            reply('150 Transfer')
                            stream, _ = listener.accept()
                            with stream, path.open('r+b' if rest else 'wb') as output:
                                output.seek(rest)
                                while True:
                                    block = stream.recv(8192)
                                    if not block:
                                        break
                                    output.write(block)
                                if interrupt['pending'] and arg == tmp:
                                    output.truncate(2000)
                            rest = 0
                            listener.close()
                            listener = None
                            if interrupt['pending'] and arg == tmp:
                                interrupt['pending'] = False
                                reply('426 Fixture transfer interrupted')
                            else:
                                reply('226 Complete')
                        elif cmd == 'RNFR':
                            rename = path
                            reply('350 Rename destination')
                        elif cmd == 'RNTO':
                            rename.replace(path)
                            reply('250 Renamed')
                        else:
                            reply('500 Unsupported')
                finally:
                    if listener:
                        listener.close()
        with socketserver.TCPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.dict('os.environ', {'AUX_FTP_PASSWORD': 'fixture-secret'}):
                    failed = self.run_cmd('deploy-ftp', [], '--ftp-host', '127.0.0.1', '--ftp-user', 'fixture',
                                          '--ftp-port', str(server.server_address[1]), '--no-ftp-tls', '--ftp-root', '/', rc=1)
                    self.assertNotIn('fixture-secret', failed.stdout + failed.stderr)
                    self.assertEqual((remote / nom).read_bytes(), b'previous public copy')
                    self.assertEqual((remote / tmp).stat().st_size, 2000)
                    out = self.run_cmd('deploy-ftp', [], '--ftp-host', '127.0.0.1', '--ftp-user', 'fixture',
                                       '--ftp-port', str(server.server_address[1]), '--no-ftp-tls', '--ftp-root', '/')
                self.assertNotIn('fixture-secret', out.stdout + out.stderr)
                self.assertEqual((remote / nom).read_bytes(), data)
                self.assertEqual((remote / 'assets/style.css').read_bytes(), b'body{}')
                self.assertEqual((remote / 'index.html').read_bytes(), b'<h1>mirror</h1>')
                self.assertIn(('REST', '1234'), commands)
                self.assertIn(('REST', '2000'), commands)
                self.assertIn(('MKD', 'assets'), commands)
                self.assertFalse((remote / tmp).exists())
                self.assertFalse((remote / 'html').exists())
                self.assertFalse((remote / 'isos').exists())
            finally:
                server.shutdown()
                thread.join()

    def test_hierarchy_media_types_and_ipxe_parent_navigation(self):
        names = ['Fedora-netinst-x86_64-44.iso', 'Fedora-DVD-x86_64-44.iso',
                 'Fedora-Workstation-Live-x86_64-44.iso', 'debian-amd64-netinst.iso',
                 'debian-amd64-DVD.iso', 'debian-live-amd64.iso',
                 'ubuntu-netboot.tar.gz', 'ubuntu-live-server-amd64.iso', 'ubuntu-desktop-amd64.iso',
                 'install-amd64-minimal.iso', 'ipxe-arch.efi', 'gparted-live-amd64.iso']
        records = [eng.obt_meta('https://source.test/' + name) for name in names]
        # Boot readiness must not turn a full installer into a netinstall.
        for rec in records:
            if rec['family'] != 'gentoo':
                rec['_boot'] = {'group': 'netboot', 'commands': ['echo fixture'], 'firmware': None}
        tree = eng.gen_arbol(records)
        nodes = {node['id']: node for node, _ in eng.recorre_arbol(tree)}
        for family in ['fedora', 'debian', 'ubuntu']:
            for ordinal, branch in enumerate(['netinstall', 'install', 'live'], 1):
                node = nodes['nav_distribution_' + family + '_' + branch]
                self.assertEqual(len(node['resources']), 1)
                self.assertTrue(node['number'].endswith('.' + str(ordinal)))
        self.assertEqual(eng.obt_ids(nodes['nav_distribution_gentoo_chroot']), [records[9]['id']])
        flattened = [rid for node, _ in eng.recorre_arbol(tree) for rid in node['resources']]
        self.assertCountEqual(flattened, [rec['id'] for rec in records])
        self.assertEqual(len(flattened), len(set(flattened)))
        cfg = SimpleNamespace(pxe_url='http://pxe.example.test', base_url='https://aux.example.test')
        menu = eng.gen_ipxe(records, cfg)
        sections = {}
        current = None
        for line in menu.splitlines():
            if line.startswith(':'):
                current = line[1:]
                sections[current] = []
            elif current:
                sections[current].append(line)
        def check_parent(node, parent):
            lines = sections[node['id']]
            self.assertIn('item ' + parent + ' Back', lines)
            self.assertIn('choose target && goto ${target} || goto ' + parent, lines)
            for child in node['children']:
                check_parent(child, node['id'])
        for node in tree:
            check_parent(node, 'start')
        for line in menu.splitlines():
            if line.startswith('item ') and not line.startswith('item --gap'):
                parts = line.split()
                target = parts[3] if parts[1] == '--key' else parts[1]
                self.assertIn(target, sections)
        gentoo = '\n'.join(sections['nav_distribution_gentoo_chroot'])
        self.assertIn('No compatible complete boot recipe', gentoo)
        self.assertNotIn(':' + records[9]['id'] + '\n', menu)
        for html_page in [eng.gen_rows(records, cfg), eng.gen_cli_page(records, cfg)]:
            for node in nodes.values():
                self.assertIn('id="' + node['id'] + '"', html_page)

    def test_tools_and_separate_host_sitemaps(self):
        (self.pth_web / 'tools').mkdir()
        (self.pth_web / 'tools/memtest64.efi').write_bytes(b'MZefi-tool')
        (self.pth_web / 'tools/memtest64.bin').write_bytes(b'bios-tool')
        self.run_cmd('generate', [])
        menu = (self.pth_web / 'menu.ipxe').read_text()
        self.assertIn('item --key 2 nav_tools 2. Tools', menu)
        self.assertIn('iseq ${platform} efi', menu)
        self.assertIn('iseq ${platform} pcbios', menu)
        self.assertIn('/tools/memtest64.bin', menu)
        self.assertIn('/tools/memtest64.efi', menu)
        ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for name, base in [('sitemaps.xml', 'https://mirror.example.test'), ('sitemaps-pxe.xml', 'http://127.0.0.1:8080')]:
            locs = [node.text for node in ET.parse(self.pth_web / name).findall('s:url/s:loc', ns)]
            self.assertTrue(all(loc.startswith(base + '/') for loc in locs))
        self.assertEqual((self.pth_web / 'index.php').read_bytes(), (self.pth_web / 'index-aux.php').read_bytes())
        self.assertEqual((self.pth_web / 'cli.html').read_bytes(), (self.pth_web / 'index-pxe.html').read_bytes())

    def test_assistance_chapter_orders_versions_and_gates_autostart(self):
        cfg = SimpleNamespace(pxe_url='http://pxe.example.test', base_url='https://aux.example.test')
        names = ['tec-fedora44-assist-5.0.1-dev.9-x86_64.iso',
                 'tec-fedora44-assist-5.0.1-dev.10-x86_64.iso',
                 'tec-fedora44-assist-5.0.1-x86_64.iso',
                 'tec-fedora44-assist-5.0.2-dev.0-x86_64.iso',
                 'Fedora-Server-netinst-x86_64-44.iso']
        records = [eng.obt_meta('https://source.test/' + name) for name in names]
        for rec in records[:3]:
            rec['assistance_boot'] = True
            rec['_boot'] = {'group': 'tools', 'commands': ['echo fixture'], 'firmware': 'efi'}
        # A newer filename without an inspected boot recipe cannot become the default.
        tree = eng.gen_arbol(records)
        self.assertEqual(tree[0]['number'], '0')
        self.assertEqual(tree[0]['resources'], [records[i]['id'] for i in [3, 2, 1, 0]])
        menu = eng.gen_ipxe(records, cfg)
        self.assertLess(menu.index('item --key 0 nav_assistance'), menu.index('item --key 1 nav_distribution'))
        self.assertNotIn('set auto_target ' + records[3]['id'], menu)
        self.assertIn('iseq ${cpu_arch} x86_64 && iseq ${platform} efi && iseq ${buildarch} x86_64 && set auto_timeout 60000', menu)
        targets = [line.split('set auto_target ')[1].split()[0] for line in menu.splitlines() if '&& set auto_target ' in line]
        self.assertEqual(targets[-1], records[2]['id'])
        self.assertIn('--retimeout 0 target || goto cancelled\nset auto_timeout 0\ngoto ${target}', menu)
        self.assertIn(':cancelled\nset auto_timeout 0\ngoto start', menu)
        self.assertIn('cpair --foreground 2 --background 0 0', menu)
        self.assertIn('cpair --foreground 4 --background 0 1', menu)
        self.assertIn('cpair --foreground 4 --background 0 2', menu)
        self.assertIn('console --keep || goto colour_missing', menu)
        self.assertNotIn('--rgb', menu)
        self.assertIn('cpair --foreground 1 --background 0 5', menu)
        for rec in records:
            rec.pop('_boot', None)
        self.assertNotIn('set auto_timeout 60000', eng.gen_ipxe(records, cfg))
        for page in [eng.gen_rows(records, cfg), eng.gen_cli_page(records, cfg)]:
            self.assertLess(page.index('0. Remote assistance'), page.index('1. Distros'))


class PortalTests(unittest.TestCase):
    def test_iso_chapter_and_manifest_are_complete_and_preserve_source_only_status(self):
        page = (pth_repo / 'dist/iso-guide.html').read_text()
        parsed = self.Parser()
        parsed.feed(page)
        self.assertNotIn('script', parsed.tags)
        self.assertIn('<html lang="es">', page)
        self.assertGreater(len(re.sub(r'<[^>]+>', ' ', page).split()), 2000)
        for anchor in ['manifesto', 'iso-parts', 'iso-design', 'iso-sources', 'iso-builder',
                       'iso-kickstart', 'iso-compile', 'iso-verify', 'iso-publish', 'iso-maintain']:
            self.assertIn('href="#' + anchor + '"', page)
            self.assertIn('id="' + anchor + '"', page)
        self.assertIn('--iso-name=aux-rescue-5.0.1-dev.5-x86_64.iso', page)
        manifest = json.loads((pth_repo / 'dist/downloads/iso/manifest.json').read_text())
        self.assertEqual(manifest['requested_count'], len(manifest['requested_packages']))
        self.assertEqual(manifest['requested_count'], 94)
        self.assertTrue(manifest['wifi'])
        for name in ['iso_sha256', 'iso_size_bytes', 'installed_rpms']:
            self.assertIsNone(manifest[name])
        for name, sha in manifest['source_sha256'].items():
            self.assertEqual(hashlib.sha256((pth_repo / 'iso' / name).read_bytes()).hexdigest(), sha)
        archive = pth_repo / 'dist/downloads/tec-fedora44-rescue-5.0.1-dev.5-sources.zip'
        with zipfile.ZipFile(archive) as source:
            self.assertEqual(set(source.namelist()), set(eng.ISO_SOURCE_FILES + ['manifest.json']))
        self.assertIn('No such file or directory', (pth_repo / 'dist/tec-502.html').read_text())
        self.assertIn('/run/php-fpm/tec.sock', (pth_repo / 'dist/tec-502.html').read_text())

    def test_ftp_and_chroot_guides_are_complete_without_javascript(self):
        for nom in ['index.html', 'cli.html', 'cli-all.html']:
            pag = (pth_repo / 'dist' / nom).read_text()
            self.assertIn('sudo bash deploy.sh ftp', pag)
            self.assertIn('--ftp-host HOST_FTP --ftp-user USUARIO_FTP', pag)
            self.assertIn('--user root --group nginx', pag)
            for fam in ['fedora', 'debian', 'ubuntu', 'gentoo', 'arch']:
                self.assertIn('id="chroot-' + fam + '"', pag)
            self.assertIn('--make-rslave', pag)
            self.assertIn('chroot "$pth_raiz" /bin/bash', pag)
        pag = (pth_repo / 'dist/chroot-all.html').read_text()
        self.assertNotIn('<script', pag)
        self.assertNotRegex(pag, r'<details(?![^>]*\bopen\b)')
        self.assertIn('--use-host-config', pag)
        self.assertIn('--force-check-sig', pag)

    class Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []
            self.downloads = []
            self.tags = []
            self.commands = []
            self.in_pre = False

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            self.tags.append(tag)
            for name in ('href', 'src'):
                if attrs.get(name):
                    self.links.append(attrs[name])
            if tag == 'a' and attrs.get('class') == 'download-link':
                self.downloads.append(attrs.get('href'))
            if tag == 'pre':
                self.in_pre = True
                self.commands.append('')

        def handle_endtag(self, tag):
            if tag == 'pre':
                self.in_pre = False

        def handle_data(self, data):
            if self.in_pre:
                self.commands[-1] += data

    def test_static_file_links_and_catalog(self):
        for path in (pth_repo / 'dist').rglob('*.html'):
            if path.relative_to(pth_repo / 'dist').as_posix().startswith('downloads/src/'):
                continue
            par = self.Parser()
            pag = path.read_text()
            par.feed(pag)
            for lnk in par.links:
                part = urlsplit(lnk)
                if not part.scheme and part.path:
                    target = path.parent / unquote(part.path)
                    self.assertTrue(target.is_file() or (target.is_dir() and (target / 'index.html').is_file()), (path.name, lnk))
            self.assertNotIn('@@', pag)
        cat = json.loads((pth_repo / 'dist/catalog.json').read_text())
        self.assertEqual(len(cat['resources']), 49)
        self.assertTrue({'ubuntu', 'bootrepair', 'centos', 'systemrescue'} <= {rec['family'] for rec in cat['resources']})
        self.assertEqual(sum(rec['arch'] == 'arm64' for rec in cat['resources']), 8)
        self.assertTrue(all(rec['status'] == 'source' for rec in cat['resources']))
        self.assertTrue(all(rec['size'] is None for rec in cat['resources']))

    def test_terminal_disclosures_and_expanded_fallback_share_all_files(self):
        class MenuParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.disclosures = []
                self.ids = []
                self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'details':
                    self.depth += 1
                    self.disclosures.append((self.depth, 'open' in attrs))
                if attrs.get('id'):
                    self.ids.append(attrs['id'])
                if tag == 'a' and 'href' in attrs:
                    self.links.append(attrs['href'])
            def handle_endtag(self, tag):
                if tag == 'details':
                    self.depth -= 1
        compact, expanded = MenuParser(), MenuParser()
        pages = [(pth_repo / 'dist' / name).read_text() for name in ['cli.html', 'cli-all.html']]
        compact.feed(pages[0])
        expanded.feed(pages[1])
        self.assertEqual(compact.links, expanded.links)
        self.assertEqual(compact.ids, expanded.ids)
        self.assertEqual(len(compact.ids), len(set(compact.ids)))
        self.assertEqual(max(depth for depth, _ in compact.disclosures), 3)
        self.assertTrue(any(not opened for _, opened in compact.disclosures))
        self.assertTrue(all(opened for _, opened in expanded.disclosures))
        self.assertEqual(compact.depth, 0)
        self.assertEqual(expanded.depth, 0)
        cat = json.loads((pth_repo / 'dist/catalog.json').read_text())
        for rec in cat['resources']:
            self.assertIn(rec['download_urls']['bastion'], compact.links)
            self.assertIn('files/' + rec['id'] + '.html', compact.links)
        for node, _ in eng.recorre_arbol(cat['hierarchy']):
            self.assertIn(node['id'], compact.ids)
        for page in pages:
            self.assertIn('background: #0f172a', page)
            self.assertIn('color: #38bdf8', page)
            self.assertNotIn('<script', page)

    def test_every_download_is_present_without_javascript(self):
        cat = json.loads((pth_repo / 'dist/catalog.json').read_text())
        by_id = {rec['id']: rec for rec in cat['resources']}
        expected = [by_id[rid]['download_urls']['bastion'] for node, _ in eng.recorre_arbol(cat['hierarchy']) for rid in node['resources']]
        for filename in ['dist/index.html', 'index.php']:
            par = self.Parser()
            par.feed((pth_repo / filename).read_text())
            self.assertEqual(par.downloads, expected)
        par = self.Parser()
        par.feed((pth_repo / 'dist/cli.html').read_text())
        self.assertFalse({'script', 'link', 'img', 'button', 'input'} & set(par.tags))
        self.assertIn('style', par.tags)
        self.assertEqual(par.links[0], cat['base_url'] + '/')
        self.assertIn('contents.html', par.links)
        self.assertIn('https://tec.1-s.es/?view=pxe', par.links)
        visual = (pth_repo / 'dist/index.html').read_text()
        self.assertIn('class="portal-switch" href="' + cat['pxe_url'] + '/"', visual)
        self.assertIn('>PXE&gt;<span class="pxe-cursor">_</span>', visual)
        self.assertIn('href="contents.html"', visual)
        self.assertTrue(set(expected).issubset(par.links))
        rows = list(csv.DictReader(io.StringIO((pth_repo / 'dist/downloads/isos.tsv').read_text()), delimiter='\t'))
        self.assertEqual([row['filename'] for row in rows], [rec['filename'] for rec in cat['resources'] if rec['format'] == 'ISO'])

    def test_local_selection_escaping_and_redirect_filenames(self):
        cfg = SimpleNamespace(base_url='https://mirror.example.test', pxe_url='http://pxe.example.test')
        rec = eng.obt_meta('https://example.test/arm64+test.iso/download?label=a&quote=%22')
        rec['name'] = '<script>alert("catalog")</script>'
        par = self.Parser()
        par.feed(eng.gen_rows([rec], cfg))
        self.assertNotIn('script', par.tags)
        self.assertEqual(par.downloads, ['https://b.1-s.es/arm64%2Btest.iso'])
        par = self.Parser()
        par.feed(eng.gen_resource_page(rec, cfg))
        for command in par.commands[:2]:
            args = shlex.split(command)
            self.assertEqual(args[-1], 'https://b.1-s.es/arm64%2Btest.iso')
            self.assertIn('arm64+test.iso', args)
        rec.update(published=True, status='ready', sha256='a' * 64, size=40960)
        self.assertEqual(eng.obt_preferred_url(rec, cfg), 'https://b.1-s.es/arm64%2Btest.iso')
        par = self.Parser()
        par.feed(eng.gen_cli_page([rec], cfg))
        self.assertIn(cfg.pxe_url + '/arm64%2Btest.iso', par.links)
        self.assertIn('sha256sum -c -', eng.gen_resource_page(rec, cfg))
        rec['status'] = 'checksum-failed'
        self.assertEqual(eng.obt_preferred_url(rec, cfg), rec['url'])

    def test_wget_and_curl_follow_links_and_resume(self):
        """Exercise actual CLI clients against a tiny redirect + Range fixture."""
        body = b'AUX ISO DOWNLOAD FIXTURE\n' * 2048
        requests = []
        page = ''
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Range')))
                if self.path == '/cli.html':
                    data = page.encode()
                    self.send_response(200)
                    self.send_header('Content-Length', str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                elif self.path in ('/test-amd64.iso/download', '/media/test-amd64.iso'):
                    self.send_response(302)
                    self.send_header('Location', '/payload')
                    self.end_headers()
                elif self.path == '/payload':
                    start = int(self.headers.get('Range', 'bytes=0-').split('=')[1].split('-')[0])
                    self.send_response(206 if start else 200)
                    self.send_header('Content-Length', str(len(body) - start))
                    self.send_header('Accept-Ranges', 'bytes')
                    if start:
                        self.send_header('Content-Range', f'bytes {start}-{len(body)-1}/{len(body)}')
                    self.end_headers()
                    self.wfile.write(body[start:])
                else:
                    self.send_error(404)
            def log_message(self, *_):
                pass
        srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        base = f'http://127.0.0.1:{srv.server_port}'
        rec = eng.obt_meta(base + '/test-amd64.iso/download')
        cfg = SimpleNamespace(base_url=base, pxe_url=base, download_url=base + '/media')
        page = eng.gen_cli_page([rec], cfg)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            response = subprocess.run(['curl', '-fsS', base + '/cli.html'], text=True, capture_output=True, check=True)
            par = self.Parser()
            par.feed(response.stdout)
            self.assertIn(rec['url'], par.links)
            detail = self.Parser()
            detail.feed(eng.gen_resource_page(rec, cfg))
            with tempfile.TemporaryDirectory(prefix='aux-cli-') as tmp:
                path = Path(tmp) / rec['filename']
                for command in detail.commands[:2]:
                    path.write_bytes(body[:8192])
                    result = subprocess.run(shlex.split(command), cwd=tmp, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(path.read_bytes(), body)
                    self.assertFalse((Path(tmp) / 'download').exists())
            self.assertEqual(sum(path == '/payload' and byte_range == 'bytes=8192-' for path, byte_range in requests), 2)
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
