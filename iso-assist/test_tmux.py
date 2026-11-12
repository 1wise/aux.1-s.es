#!/usr/bin/env python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Exercise missing Live configuration recovery without launching a terminal server."""
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('aux_tmux_assist',Path(__file__).parent/'payload/assist.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)


class ConfiguracionTmux(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.raiz=Path(self.tmp.name);self.cfg=self.raiz/'live/tmux.conf'
        self.src=self.raiz/'release.conf';self.src.write_text('set -g mouse on\nset -gw pane-scrollbars on\n')
        self.ctx=ExitStack();self.addCleanup(self.ctx.close)
        self.ctx.enter_context(patch.object(app,'DIR_CFG',self.cfg.parent))
        self.ctx.enter_context(patch.object(app,'INSTALADO',False))
        self.ctx.enter_context(patch.object(app,'FUENTES_TMX',(self.src,)))

    def test_missing_default_is_restored_with_readable_mode_under_private_umask(self):
        prv=os.umask(0o077)
        try:self.assertEqual(app.prepara_tmux(),self.cfg)
        finally:os.umask(prv)
        self.assertEqual(self.cfg.read_bytes(),self.src.read_bytes())
        self.assertEqual(self.cfg.stat().st_mode&0o777,0o644)
        self.assertFalse(list(self.cfg.parent.glob('.tmux-*')))

    def test_existing_configuration_is_preserved(self):
        self.cfg.parent.mkdir();self.cfg.write_text('set -g history-limit 1234\n')
        self.assertEqual(app.prepara_tmux(),self.cfg)
        self.assertEqual(self.cfg.read_text(),'set -g history-limit 1234\n')

    def test_missing_trusted_source_prevents_terminal_creation(self):
        with patch.object(app,'FUENTES_TMX',()),patch.object(app,'ejecuta') as run:
            with self.assertRaisesRegex(RuntimeError,'Missing public tmux configuration'):
                app.inicia_terminales()
        run.assert_not_called();self.assertFalse(self.cfg.exists())

    def test_explicit_missing_configuration_is_not_replaced_by_a_default(self):
        with self.assertRaisesRegex(RuntimeError,'Missing tmux configuration'):
            app.prepara_tmux(self.raiz/'custom.conf')
        self.assertFalse(self.cfg.exists())

    def test_installed_configuration_requires_explicit_repair(self):
        with patch.object(app,'INSTALADO',True):
            with self.assertRaisesRegex(RuntimeError,'Missing tmux configuration'):app.prepara_tmux()
        self.assertFalse(self.cfg.exists())

    def test_both_sessions_receive_the_restored_configuration(self):
        with patch.object(app,'ejecuta') as run:app.inicia_terminales()
        self.assertEqual(run.call_count,2)
        for call in run.call_args_list:
            cmd=call.args[0]
            self.assertEqual(cmd[cmd.index('-f')+1],str(self.cfg))
        self.assertEqual({call.args[0][call.args[0].index('-s')+1] for call in run.call_args_list}, {'assist','assist-2'})

    def test_failed_publication_leaves_no_partial_configuration(self):
        with patch.object(app.os,'link',side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError):app.prepara_tmux()
        self.assertFalse(self.cfg.exists());self.assertFalse(list(self.cfg.parent.glob('.tmux-*')))

    def test_configuration_created_concurrently_is_preserved(self):
        def publica(src,dst):
            Path(dst).write_text('set -g history-limit 5678\n');raise FileExistsError()
        with patch.object(app.os,'link',side_effect=publica):app.prepara_tmux()
        self.assertEqual(self.cfg.read_text(),'set -g history-limit 5678\n')
        self.assertFalse(list(self.cfg.parent.glob('.tmux-*')))


if __name__=='__main__':unittest.main()
