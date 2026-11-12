#!/usr/bin/env python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Register the real browser alternative in private directories, without manpages."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

DIR_APP=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('aux_image_check',DIR_APP/'payload/image_check.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


class NavegadorLive(unittest.TestCase):
    def test_existing_browser_is_preserved(self):
        with patch.object(mod.shutil,'which',return_value='/usr/bin/links'),patch.object(mod.subprocess,'run') as run:
            mod.prepara_links()
        run.assert_not_called()

    @unittest.skipUnless(shutil.which('update-alternatives'),'Requires alternatives tool for isolated integration')
    def test_registration_without_manpages_creates_a_working_browser_link(self):
        ejecuta=subprocess.run;busca=shutil.which;exe=busca('update-alternatives')
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);bin_dir=raiz/'bin';alt_dir=raiz/'etc/alternatives';adm_dir=raiz/'var/lib/alternatives'
            for pth in (bin_dir,alt_dir,adm_dir):pth.mkdir(parents=True)
            src=bin_dir/'links2';dst=bin_dir/'links'
            src.write_text('#!/bin/sh\n# Timestamp: 2026-11-11 | Version: fixture\n'
                '# Author & Credits: https://www.alawise.es/1-s\nprintf "links2 fixture works\\n"\n')
            src.chmod(0o755)
            def which(nom):
                if nom=='links':return str(dst) if dst.exists() else None
                if nom=='/usr/bin/links2':return '/usr/bin/links2'
                return exe if nom=='update-alternatives' else None
            def registra(cmd,**kwargs):
                self.assertEqual(cmd,[exe,'--install','/usr/bin/links','links','/usr/bin/links2','80'])
                return ejecuta([exe,'--altdir',str(alt_dir),'--admindir',str(adm_dir),
                    '--install',str(dst),'links',str(src),'80'],capture_output=True,**kwargs)
            with patch.object(mod.shutil,'which',side_effect=which),patch.object(mod.subprocess,'run',side_effect=registra):
                mod.prepara_links()
            self.assertTrue(dst.is_symlink())
            self.assertEqual(dst.resolve(),src)
            self.assertEqual(ejecuta([str(dst)],check=True,capture_output=True,text=True).stdout,'links2 fixture works\n')
            self.assertFalse((raiz/'usr/share/man').exists())

    def test_missing_real_browser_fails_without_creating_an_alias(self):
        with patch.object(mod.shutil,'which',return_value=None),patch.object(mod.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'Missing executable /usr/bin/links2'):mod.prepara_links()
        run.assert_not_called()

    def test_missing_alternatives_tool_is_reported(self):
        with patch.object(mod.shutil,'which',side_effect=lambda nom:'/usr/bin/links2' if nom=='/usr/bin/links2' else None):
            with self.assertRaisesRegex(RuntimeError,'Missing update-alternatives'):mod.prepara_links()

    def test_unsuccessful_registration_does_not_hide_the_missing_command(self):
        with patch.object(mod.shutil,'which',side_effect=lambda nom:None if nom=='links' else nom if nom.startswith('/') else '/usr/bin/'+nom), \
             patch.object(mod.subprocess,'run'):
            with self.assertRaisesRegex(RuntimeError,'still unavailable'):mod.prepara_links()


class TerminalesLive(unittest.TestCase):
    def test_live_config_is_required_before_finishing_the_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError,'Missing regular Live tmux configuration'):
                mod.verifica_tmux(Path(tmp))

    def test_live_config_must_match_the_embedded_release_and_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);cfg=raiz/'usr/share/aux-assist/tmux.conf';src=raiz/'usr/local/lib/aux/config/tmux.conf'
            for pth in (cfg,src):pth.parent.mkdir(parents=True)
            src.write_text('set -g mouse on\n');cfg.write_text('changed\n');cfg.chmod(0o644)
            with self.assertRaisesRegex(RuntimeError,'differs from the verified AUX sources'):mod.verifica_tmux(raiz)
            cfg.write_bytes(src.read_bytes());cfg.chmod(0o600)
            with self.assertRaisesRegex(RuntimeError,'mode 0644'):mod.verifica_tmux(raiz)
            cfg.chmod(0o644);mod.verifica_tmux(raiz)

    def test_symbolic_live_config_is_not_accepted_as_a_built_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);cfg=raiz/'usr/share/aux-assist/tmux.conf';cfg.parent.mkdir(parents=True)
            cfg.symlink_to('/dev/null')
            with self.assertRaisesRegex(RuntimeError,'Missing regular Live tmux configuration'):mod.verifica_tmux(raiz)

    def test_missing_utilities_fail_before_terminfo_queries(self):
        with patch.object(mod.shutil,'which',return_value=None),patch.object(mod.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'Missing ncurses utilities: clear, tput, reset, infocmp'):
                mod.prepara_terminales()
        run.assert_not_called()

    def test_missing_tmux_terminfo_fails_with_the_entry_name(self):
        def ejecuta(cmd,**kwargs):
            return SimpleNamespace(returncode=int(cmd[-1]=='tmux-256color'),stderr='not found')
        with patch.object(mod.shutil,'which',side_effect=lambda nom:'/usr/bin/'+nom), \
             patch.object(mod.subprocess,'run',side_effect=ejecuta):
            with self.assertRaisesRegex(RuntimeError,'Missing terminfo entry tmux-256color'):
                mod.prepara_terminales()

    @unittest.skipUnless(all(shutil.which(nom) for nom in ('clear','tput','reset','infocmp')),
                         'Requires real ncurses tools for terminal definition integration')
    def test_real_ncurses_definitions_and_clear_escape_output(self):
        mod.prepara_terminales()
        dat=subprocess.run(['tput','-T','xterm-256color','clear'],capture_output=True,check=True)
        self.assertIn(b'\x1b[',dat.stdout)


if __name__=='__main__':unittest.main()
