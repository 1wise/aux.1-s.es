# Timestamp: 2026-11-23 | Version: 8.0.1-beta.6
# Author & Credits: https://www.alawise.es/1-s
"""Test Rescue selection without starting services or modifying the host."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class RescueDialog(unittest.TestCase):
    def setUp(self):
        path=ROOT/'iso-assist/payload/assist.py'
        spec=importlib.util.spec_from_file_location('aux8_rescue_fixture',path)
        self.mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.mod)

    def test_menu_returns_action_without_starting_services(self):
        with patch.object(self.mod.shutil,'which',return_value='/usr/bin/dialog'), \
             patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stdout,'isatty',return_value=True), \
             patch.object(self.mod,'ia_disponible',return_value=False), \
             patch.object(self.mod.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='b\n')) as run:
            self.assertEqual(self.mod.opcion_rescue([]),'b')
        self.assertIn('--menu',run.call_args.args[0]);self.assertIn('--help-button',run.call_args.args[0])
        self.assertNotIn('systemctl',run.call_args.args[0])

    def test_help_returns_to_the_same_selector(self):
        replies=[SimpleNamespace(returncode=2,stdout='HELP'),SimpleNamespace(returncode=0,stdout=''),
                 SimpleNamespace(returncode=0,stdout='s\n')]
        with patch.object(self.mod.shutil,'which',return_value='dialog'), \
             patch.object(sys.stdin,'isatty',return_value=True),patch.object(sys.stdout,'isatty',return_value=True), \
             patch.object(self.mod,'ia_disponible',return_value=False), \
             patch.object(self.mod.subprocess,'run',side_effect=replies) as run:
            self.assertEqual(self.mod.opcion_rescue([]),'s')
        self.assertEqual(run.call_count,3);self.assertIn('--msgbox',run.call_args_list[1].args[0])


if __name__=='__main__':unittest.main()
