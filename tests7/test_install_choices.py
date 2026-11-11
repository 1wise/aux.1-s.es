# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Exercise explicit host selection and optional assistance installation."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from auxlib import interactive, profiles, setup


class OpcionesInstalacion(unittest.TestCase):
    def test_apply_without_a_destination_cannot_select_the_host(self):
        res = subprocess.run(['python3',str(setup.DIR_APP/'aux-setup'),'--apply'],
                             capture_output=True,text=True)
        self.assertNotEqual(res.returncode,0)
        self.assertIn('Elegir explícitamente --mode',res.stderr)
        self.assertNotIn('+ apt-get',res.stdout)
        self.assertNotIn('+ dnf',res.stdout)

    def test_console_host_option_is_last_and_assist_is_selectable(self):
        cfg = SimpleNamespace(distro='debian',root=Path('/'),native=None,apply=False)
        with patch.object(interactive,'elige',return_value='tools') as elige, \
             patch.object(interactive,'marca',return_value=['aux-assist']) as marca, \
             contextlib.redirect_stdout(io.StringIO()):
            interactive.prepara(cfg)
        opciones = elige.call_args.args[1]
        self.assertEqual(opciones[0][1],'iso')
        self.assertEqual(opciones[-1][1],'existing')
        self.assertIn('SISTEMA ACTUAL',opciones[-1][0])
        self.assertIn('aux-assist',[nom for nom,_ in marca.call_args.args[1]])
        self.assertEqual(cfg.roles,'base,aux-assist')
        self.assertFalse(cfg.apply)

    def test_deselected_client_has_no_new_launchers_units_or_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            setup.instala_archivos(raiz,['base'])
            self.assertTrue((raiz/'usr/local/bin/aux-setup').is_symlink())
            for nom in ('usr/local/bin/aux-assist','etc/aux-assist/cli.json',
                        'etc/systemd/system/aux-assist.service',
                        'usr/share/applications/aux-assist.desktop',
                        'usr/lib/sysusers.d/aux-ai.conf'):
                self.assertFalse((raiz/nom).exists(),nom)

    def test_client_can_be_installed_and_existing_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            setup.instala_archivos(raiz,['base','aux-assist'])
            self.assertTrue((raiz/'usr/local/bin/aux-assist').is_symlink())
            self.assertTrue((raiz/'etc/systemd/system/aux-assist.service').is_file())
            self.assertTrue((raiz/'usr/share/applications/aux-assist.desktop').is_file())
            cfg = raiz/'etc/aux-assist/cli.json'
            cfg.write_text('{"keep":"local"}')
            setup.instala_archivos(raiz,['base'])
            self.assertEqual(cfg.read_text(),'{"keep":"local"}')
            self.assertTrue((raiz/'etc/systemd/system/aux-assist.service').is_file())

    def test_iso_hooks_preserve_the_component_choice(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dis,nom in [('fedora','installed.ks'),('debian','preseed.cfg')]:
                for roles in (['base'],['base','aux-assist']):
                    dst = Path(tmp)/dis/str(len(roles))
                    dat = profiles.genera(dis,roles,dst,build_id='c'*32)
                    self.assertIn('--roles '+','.join(roles)+' --apply',(dst/nom).read_text())
                    self.assertEqual(dat['components'],['aux-assist'] if len(roles)>1 else [])
                    if len(roles)>1:
                        self.assertIn('kbd',dat['packages'])

    def test_existing_system_plan_names_the_affected_target(self):
        res = subprocess.run(['python3',str(setup.DIR_APP/'aux-setup'),'--mode','existing',
                              '--distro','debian','--roles','base,aux-assist'],capture_output=True,text=True)
        self.assertEqual(res.returncode,0,res.stderr)
        self.assertIn('DESTINO: SISTEMA ACTUAL',res.stdout)
        self.assertIn('puede modificar sus servicios',res.stdout)
        self.assertIn('aux-assist: seleccionado',res.stdout)


if __name__ == '__main__':
    unittest.main()
