# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Regress invalid confirmations, contextual help, and atomic checkbox entry."""
import contextlib
import curses
import io
import unittest
from unittest.mock import patch

from auxlib import console_ui as ui, interactive
from auxlib.helptext import valida
from test_catalog_console import Pantalla


class CamposPersistentes(unittest.TestCase):
    def test_invalid_confirmation_and_help_keep_the_plan_until_valid(self):
        scr = Pantalla(['\n', curses.KEY_F1, '\n', '\x15', *'GENERAR', '\n'])
        val = ui.campo_pantalla(scr, 'Escribir GENERAR para crear', 'error', ['PLAN CONSERVADO'])
        self.assertEqual(val, 'GENERAR')
        self.assertTrue(any('error' in txt for txt in scr.textos))
        self.assertTrue(any('PLAN CONSERVADO' in txt for txt in scr.textos))
        self.assertTrue(any('AYUDA' in txt for txt in scr.textos))

    def test_plain_confirmation_does_not_return_an_invalid_value(self):
        with patch.object(ui.sys.stdin, 'isatty', return_value=False), \
             patch('builtins.input', side_effect=['ejecuta', '?ayuda', 'EJECUTAR']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ui.campo('Escribir EJECUTAR para aplicar'), 'EJECUTAR')

    def test_numbered_menu_retries_invalid_input_without_losing_default(self):
        with patch.object(interactive.sys.stdin, 'isatty', return_value=False), \
             patch('builtins.input', side_effect=['x', '99', '']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(interactive.elige('Destino', [('A', 1), ('B', 2)], 2), 2)

    def test_checkbox_line_is_atomic_when_one_number_is_invalid(self):
        with patch.object(interactive.sys.stdin, 'isatty', return_value=False), \
             patch('builtins.input', side_effect=['1,99', '']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(interactive.marca('Selección', [('a', 'A'), ('b', 'B')], ['b']), ['b'])

    def test_help_preserves_menu_selection(self):
        scr = Pantalla([curses.KEY_F1, '\n', '\n'])
        self.assertEqual(ui.pantalla(scr, 'Destino', [('a', 'A'), ('b', 'B')], ['b']), 'b')

    def test_nonfinite_and_out_of_range_budgets_stay_invalid(self):
        for val in ('nan', 'inf', '-1', 'text'):
            with self.subTest(value=val), self.assertRaises(ValueError):
                valida('Presupuesto RAM (GiB)', val)
        with self.assertRaises(ValueError):
            valida('Reserva RAM (%)', '100')

    def test_configured_port_validation_runs_before_the_menu_returns(self):
        scr = Pantalla(['\n', '\x15', *'9443', '\n'])
        self.assertEqual(ui.campo_pantalla(scr, 'ftp_port', '70000'), '9443')


if __name__ == '__main__':
    unittest.main()
