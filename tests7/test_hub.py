# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Check dispatch boundaries, return navigation and a real curses child application."""
import contextlib
import fcntl
import io
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest
from unittest.mock import patch

from auxlib import hub, localtools
from auxlib.console_ui import CONTEXTO

RAIZ = Path(__file__).resolve().parents[1]


class ConsolaUnificada(unittest.TestCase):
    def test_registry_uses_existing_python_and_bash_commands_without_execution_flags(self):
        for nom, (_, archivo, args) in hub.APLICACIONES.items():
            with self.subTest(application=nom):
                cmd = hub.comando(nom)
                self.assertEqual(cmd[0], 'bash' if archivo.endswith('.sh') else sys.executable)
                self.assertEqual(Path(cmd[1]), RAIZ / archivo)
                self.assertEqual(cmd[2:], list(args))
                self.assertNotIn('--apply', cmd)
                self.assertNotIn('--build', cmd)
                self.assertNotIn('sudo', cmd)

    def test_unknown_application_cannot_become_a_shell_command(self):
        with patch.object(hub.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                hub.abre('download; touch /tmp/aux-unexpected')
            run.assert_not_called()

    def test_completed_and_cancelled_children_return_to_the_same_main_selection(self):
        temas = []
        def elige(*args):
            temas.append(CONTEXTO.get())
            return next(elegidos)
        elegidos = iter(('images', 'catalogue', 'exit'))
        with patch.object(hub, 'elige', side_effect=elige) as selector, \
             patch.object(hub, 'abre', side_effect=(0, 130)) as abre, \
             patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()) as sal:
            self.assertEqual(hub.navega(), 0)
        self.assertEqual([c.args[0] for c in abre.call_args_list], ['images', 'catalogue'])
        self.assertEqual([c.args[2] for c in selector.call_args_list], [1, 1, 2])
        self.assertIn('Cancelado', sal.getvalue())
        self.assertTrue(all(nom.startswith('AUX ') and tipo == 'configuracion' for nom, tipo in temas))
        self.assertEqual(CONTEXTO.get(), ('AUX', 'configuracion'))

    def test_server_failure_keeps_submenu_open_and_back_restores_main_position(self):
        with patch.object(hub, 'elige', side_effect=('server', 'download', 'generate', 'back', 'exit')) as sel, \
             patch.object(hub, 'abre', side_effect=(OSError('fixture failure'), 0)), \
             patch('builtins.input', return_value=''), contextlib.redirect_stdout(io.StringIO()) as sal:
            self.assertEqual(hub.navega(), 0)
        self.assertIn('fixture failure', sal.getvalue())
        self.assertEqual([c.args[0] for c in sel.call_args_list],
                         ['Menú principal', 'Servidor AUX / PXE', 'Servidor AUX / PXE',
                          'Servidor AUX / PXE', 'Menú principal'])
        self.assertEqual(sel.call_args.args[2], 3)

    def test_escape_from_submenu_returns_and_escape_from_main_exits(self):
        with patch.object(hub, 'elige', side_effect=('server', KeyboardInterrupt, KeyboardInterrupt)), \
             patch.object(hub, 'abre') as abre:
            self.assertEqual(hub.navega(), 0)
        abre.assert_not_called()

    def test_noninteractive_default_only_prints_help_and_explicit_mode_requires_tty(self):
        with patch.object(hub.sys.stdin, 'isatty', return_value=False), \
             patch.object(hub, 'navega') as navega, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(hub.main([]), 0)
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as err:
                hub.main(['--interactive'])
            self.assertEqual(err.exception.code, 2)
            navega.assert_not_called()

    def test_aux_tools_delegates_but_explicit_tool_does_not_recurse(self):
        with patch.object(hub, 'main', return_value=0) as main:
            self.assertEqual(localtools.main(['--interactive']), 0)
            main.assert_called_once_with(['--interactive'])
        with patch.object(hub, 'main') as main, patch.object(localtools, 'abre', return_value=0) as abre:
            self.assertEqual(localtools.main(['--tool', 'cockpit']), 0)
            main.assert_not_called()
            abre.assert_called_once_with('cockpit')

    def test_actual_curses_parent_opens_images_and_returns_after_child_cancellation(self):
        fd, esclavo = pty.openpty()
        fcntl.ioctl(esclavo, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 120, 0, 0))
        proc = subprocess.Popen([sys.executable, str(RAIZ / 'aux')], stdin=esclavo, stdout=esclavo,
                                stderr=esclavo, env=os.environ | {'TERM': 'xterm-256color'},
                                start_new_session=True)
        os.close(esclavo)
        def espera(txt):
            datos = b''
            fin = time.monotonic() + 8
            while txt.encode() not in datos and time.monotonic() < fin:
                if select.select([fd], [], [], .1)[0]:
                    try:
                        datos += os.read(fd, 65536)
                    except OSError:
                        break
            self.assertIn(txt.encode(), datos, datos.decode(errors='replace')[-2000:])
        try:
            espera('Menú principal')
            os.write(fd, b'\r')
            espera('AUX IMAGES')
            os.write(fd, b'\x1b')
            espera('Enter para volver al menú AUX')
            os.write(fd, b'\r')
            espera('Menú principal')
            os.write(fd, b'q')
            self.assertEqual(proc.wait(timeout=5), 0)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            os.close(fd)
