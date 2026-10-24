#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Check recipe integrity, profiles and RAM bounds without mounting client disks."""
import base64
import importlib.util
import json
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

DIR_APP = Path(__file__).resolve().parent


def modulo(nom, pth):
    spec = importlib.util.spec_from_file_location(nom, pth)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prep = modulo('tech_prep', DIR_APP / 'prepare.py')
app = modulo('tech_assist', DIR_APP / 'payload/assist.py')
ram = modulo('tech_work', DIR_APP / 'payload/work.py')
boot = modulo('tech_boot', DIR_APP / 'payload/boot_check.py')


class Fuentes(unittest.TestCase):
    def test_direct_and_web_ssh_share_port_4242(self):
        ssh_cfg = app.configura_ssh()
        agent_src = (DIR_APP / 'payload/agent.py').read_text()
        remote_src = (DIR_APP / 'payload/remote-shell.sh').read_text()
        kickstart = (DIR_APP / 'assist.ks.in').read_text()
        self.assertIn('Port 4242', ssh_cfg)
        self.assertIn('assist.PORT_SSH', agent_src)
        self.assertIn('ssh -tt -p 4242', remote_src)
        self.assertIn("'ssh_port_t', '-p', 'tcp', '4242'", kickstart)

    def test_browser_agent_command_is_documented_for_the_authorized_wss_terminal(self):
        guide = (DIR_APP / 'README.md').read_text()
        self.assertIn('runuser -u aux-ai', guide)
        self.assertIn('Pegar desde el portapapeles', guide)
        self.assertIn('puerto 443', guide)

    def test_recipe_payload_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp) / 'new'
            prep.render(pth)
            txt = (pth / 'assist.ks').read_text()
            self.assertNotIn('@PAYLOAD@', txt)
            self.assertNotIn('@ROOT_HASH@', txt)
            prep.valida_receta(txt)
            code = txt.split('%post ', 1)[1].split('\n', 1)[1].rsplit('%end', 1)[0]
            compile(code, 'Kickstart %post', 'exec')
            payload = code.split("base64.b64decode('", 1)[1].split("')", 1)[0]
            dat = json.loads(base64.b64decode(payload))
            paths = {ent['path'] for ent in dat}
            self.assertIn('/usr/share/aux-assist/assist.py', paths)
            self.assertIn('/etc/systemd/system/aux-observer@.service', paths)
            self.assertIn('/usr/share/aux-assist/profiles.json', paths)
            self.assertIn("'tcp', '4242'", code)
            self.assertFalse(any('private' in nom or 'host_ed25519' in nom for nom in paths))
            self.assertIn('--exclude-weakdeps', txt)
            self.assertIn('linux-firmware', (pth / 'packages-requested.txt').read_text())
            self.assertIn('wget2-wget', (pth / 'packages-requested.txt').read_text())
            before = (pth / 'assist.ks').read_bytes()
            with self.assertRaises(FileExistsError):
                prep.render(pth)
            self.assertEqual(before, (pth / 'assist.ks').read_bytes())

    def test_display_modes_are_rejected_before_compilation(self):
        for modo in ('text', 'cmdline', 'graphical'):
            with self.subTest(mode=modo), self.assertRaisesRegex(ValueError, 'Lorax controls display'):
                prep.valida_receta('lang en_US.UTF-8\n  ' + modo + ' # forbidden\n%packages\n')
        # Comments and script text are not installer display directives.
        prep.valida_receta('# text\nlang en_US.UTF-8\n%packages\n%end\n%post\ntext = 1\n%end\n')

    def test_virtual_storage_can_provide_required_boot_partitions(self):
        txt = (DIR_APP / 'assist.ks.in').read_text().split('%packages', 1)[0]
        cmds = [shlex.split(lin, comments=True) for lin in txt.splitlines()]
        cmds = [tok for tok in cmds if tok]
        # BIOS on GPT needs biosboot; a platform-aware request also covers EFI builds.
        boot = any(tok[0] == 'reqpart' or
                   (tok[0] in ('part', 'partition') and len(tok) > 1
                    and tok[1] == 'biosboot' and '--fstype=biosboot' in tok) for tok in cmds)
        self.assertTrue(boot, 'Virtual BIOS/GPT build lacks a required boot partition request.')
        self.assertTrue(any(tok[0] in ('part', 'partition') and tok[1] == '/'
                            and any(arg.startswith('--size=') for arg in tok) for tok in cmds))
        self.assertFalse(any(tok[0] in ('autopart', 'mount') for tok in cmds))

    def test_missing_cdboot_is_reported_before_iso_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)
            for nom in boot.ARCHIVOS_EFI:
                arc = pth / nom
                arc.parent.mkdir(parents=True, exist_ok=True)
                arc.write_bytes(b'fixture-media-input')
            self.assertEqual(len(boot.valida_efi(pth)), 4)
            gcd = pth / 'boot/efi/EFI/fedora/gcdx64.efi'
            gcd.unlink()
            with self.assertRaisesRegex(RuntimeError, 'gcdx64.efi'):
                boot.valida_efi(pth)
            gcd.write_bytes(b'')
            with self.assertRaisesRegex(RuntimeError, 'gcdx64.efi'):
                boot.valida_efi(pth)

    def test_versioned_fedora_efi_payloads_are_prepared_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)
            fuentes = {}
            for nom in boot.ARCHIVOS_EFI[:3]:
                pkg = 'grub2' if nom.endswith('/gcdx64.efi') else 'shim'
                src = pth / 'usr/lib/efi' / pkg / 'test-version/EFI/fedora' / Path(nom).name
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_bytes(b'original-' + Path(nom).name.encode())
                fuentes[nom] = src.read_bytes()
            font = pth / 'usr/share/grub/unicode.pf2'
            font.parent.mkdir(parents=True)
            font.write_bytes(b'font-fixture')
            boot.prepara_efi(pth)
            for nom, datos in fuentes.items():
                self.assertEqual((pth / nom).read_bytes(), datos)
            key = pth / 'boot/efi/EFI/fedora/shimx64.efi'
            key.write_bytes(b'existing-installed-shim')
            boot.prepara_efi(pth)
            self.assertEqual(key.read_bytes(), b'existing-installed-shim')

    def test_missing_or_ambiguous_versioned_cdboot_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'gcdx64.efi.*found 0'):
                boot.prepara_efi(pth)
            for ver in ('version-one', 'version-two'):
                src = pth / 'usr/lib/efi/grub2' / ver / 'EFI/fedora/gcdx64.efi'
                src.parent.mkdir(parents=True)
                src.write_bytes(b'efi-fixture')
            with self.assertRaisesRegex(RuntimeError, 'gcdx64.efi.*found 2'):
                boot.prepara_efi(pth)

    def test_wifi_is_included_by_default_without_duplicate_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth = Path(tmp) / 'wifi'
            prep.render(pth)
            dat = (pth / 'packages-requested.txt').read_text().splitlines()
            self.assertIn('linux-firmware', dat)
            self.assertIn('NetworkManager-wifi', dat)
            self.assertIn('wpa_supplicant', dat)
            self.assertEqual(len(dat), len(set(dat)))
            self.assertTrue(json.loads((pth / 'source-manifest.json').read_text())['wifi'])

    def test_public_key_validation_and_secret_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'test_ed25519'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
            ent = {'nombre': 'Prueba', 'contacto': 'test@example.test',
                   'clave': key.with_suffix('.pub').read_text()}
            self.assertEqual(len(app.valida_perfiles([ent])), 1)
            with self.assertRaises(ValueError):
                app.valida_perfiles([{**ent, 'private_key': key.read_text()}])
            with self.assertRaises(ValueError):
                app.valida_clave(key.read_text())
            with self.assertRaises(ValueError):
                app.valida_clave('command="bash" ' + ent['clave'])
            fake = base64.b64encode(b'\x00\x00\x00\x0bssh-ed25519').decode()
            with self.assertRaises(ValueError):
                app.valida_clave('ssh-ed25519 ' + fake)
            with self.assertRaises(ValueError):
                app.valida_perfiles([{**ent, 'nombre': '\033[2Jfake'}])

    def test_http_and_redirect_downgrade_rejected_before_fetch(self):
        for url in ('http://example.test/profile', 'https://user:secret@example.test/profile'):
            with self.assertRaises(ValueError):
                app.descarga(url)
        with self.assertRaises(ValueError):
            app.SoloHTTPS().redirect_request(None, None, 302, '', {}, 'http://example.test/')

    def test_ram_limits_and_insufficient_memory(self):
        self.assertEqual(ram.limite_ram('MemTotal: 8388608 kB\nMemAvailable: 6291456 kB\n'), 2 * 1024 ** 3)
        self.assertLessEqual(ram.limite_ram('MemTotal: 2097152 kB\nMemAvailable: 786432 kB\n'), 256 * 1024 ** 2)
        with self.assertRaises(RuntimeError):
            ram.limite_ram('MemTotal: 2097152 kB\nMemAvailable: 65536 kB\n')

    def test_cancel_before_consent_does_not_start_listener(self):
        with tempfile.TemporaryDirectory() as tmp:
            key = Path(tmp) / 'key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)], check=True)
            ent = {'nombre': 'Prueba', 'contacto': 'test@example.test',
                   'clave': key.with_suffix('.pub').read_text()}
            # Exercise both hosts without relabeling the test machine's files.
            exe_org = app.ejecuta
            exi_org = Path.exists
            def ejecuta_test(args, **kwargs):
                if args[0] == 'chcon':
                    return subprocess.CompletedProcess(args, 0)
                return exe_org(args, **kwargs)
            for activo in (False, True):
                def existe(pth):
                    return activo if str(pth) == '/sys/fs/selinux/enforce' else exi_org(pth)
                with self.subTest(selinux=activo), patch.object(app, 'DIR_RUN', Path(tmp)), \
                        patch.object(app, 'SOC_TMX', Path(tmp) / 'tmux.sock'), \
                        patch('builtins.input', return_value=''), patch.object(Path, 'exists', existe), \
                        patch.object(app, 'ejecuta', side_effect=ejecuta_test) as exe, \
                        patch.object(app.subprocess, 'Popen', wraps=subprocess.Popen) as proc:
                    app.sesion(ent)
                    # SELinux labeling is allowed; a listener or terminal must never start.
                    comandos = [Path(call.args[0][0]).name for call in exe.call_args_list]
                    comandos += [Path(call.args[0][0]).name for call in proc.call_args_list]
                    self.assertNotIn('sshd', comandos)
                    self.assertNotIn('tmux', comandos)
                    self.assertEqual('chcon' in comandos, activo)
            self.assertFalse((Path(tmp) / 'authorized_keys').exists())
            self.assertFalse((Path(tmp) / 'host_ed25519').exists())
            self.assertIn('CERRADA', (Path(tmp) / 'status.txt').read_text())


if __name__ == '__main__':
    unittest.main()
