# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
# Author & Credits: https://www.alawise.es/1-s
"""Exercise the workbench through native presets, CLI plans, ISO profiles and installation."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from auxlib import profiles,software,setup,interactive,kernel_modeler as kernel


class KernelModeler(unittest.TestCase):
    def run_cli(self,*args):
        return subprocess.run(['python3',str(setup.DIR_APP/'aux'),'kernel-modeler',*args],capture_output=True,text=True)
    def test_missing_target_never_selects_the_current_host(self):
        result=self.run_cli('--distro','debian')
        self.assertNotEqual(result.returncode,0);self.assertIn('--target-mode',result.stderr)
        self.assertNotIn('apt-get',result.stdout)
    def test_new_root_plan_contains_only_explicit_console_workbench_roles(self):
        result=self.run_cli('--target-mode','root','--distro','debian','--root','/mnt/kernel-lab')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('build-essential',result.stdout);self.assertIn('libncurses-dev',result.stdout)
        self.assertIn('qemu-system-x86',result.stdout);self.assertNotIn('task-xfce-desktop',result.stdout)
        self.assertIn('aux-assist: sin seleccionar',result.stdout)
    def test_new_root_cannot_accidentally_use_slash(self):
        result=self.run_cli('--target-mode','root','--distro','debian')
        self.assertNotEqual(result.returncode,0);self.assertIn('distinto de /',result.stderr)
    def test_host_plan_names_the_effective_target(self):
        result=self.run_cli('--target-mode','existing','--distro','fedora')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('DESTINO: SISTEMA ACTUAL',result.stdout);self.assertIn('ncurses-devel',result.stdout)
    def test_iso_plan_preserves_verified_input_and_requires_native_package_check_to_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);iso=root/'official.iso';iso.write_bytes(b'fixture ISO bytes')
            from auxlib.common import suma
            out=root/'modeler.iso';result=self.run_cli('--target-mode','iso','--distro','alpine','--iso',str(iso),'--iso-sha256',suma(iso),'--output',str(out))
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn('--check-packages',result.stdout);self.assertFalse(out.exists())
    def test_three_native_profiles_include_tools_review_model_and_no_fake_build_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            for dis in ('fedora','debian','alpine'):
                with self.subTest(distribution=dis):
                    dest=Path(tmp)/dis;dat=profiles.genera(dis,['base','kernel-modeler'],dest,native=software.minimo(dis),build_id='a'*32)
                    self.assertTrue(set(kernel.PACKAGES[dis].split())<=set(dat['packages']))
                    model=json.loads((dest/'kernel-modeler/model.json').read_text())
                    self.assertEqual(model['kernel_build'],'not-run');self.assertEqual(model['boot_test'],'not-tested')
                    self.assertIsNone(model['kernel_source']['sha256']);self.assertTrue((dest/'kernel-modeler/README.md').is_file())
                    if dis=='fedora':self.assertIn('--distro fedora',(dest/'installed.ks').read_text())
    def test_installation_adds_workbench_templates_and_private_work_but_no_boot_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);setup.instala_archivos(root,['base','kernel-modeler'],'alpine')
            model=root/'usr/local/share/aux/kernel-modeler/model.json'
            self.assertEqual(json.loads(model.read_text())['distribution'],'alpine')
            self.assertEqual((root/'work/kernel-modeler').stat().st_mode&0o777,0o700)
            self.assertFalse((root/'boot').exists());self.assertFalse((root/'usr/local/bin/aux-assist').exists())
            model.write_text('{"keep":"manual"}')
            kernel.instala(root,'alpine');self.assertEqual(json.loads(model.read_text()),{'keep':'manual'})
    def test_web_selection_requires_explicit_target_and_adds_the_workbench_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'selection.json';data={'schema':'aux-install-v1','distribution':'debian','mode':'kernel-modeler','roles':['base'],'root':'/mnt/build'}
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'target_mode'):interactive.lee_seleccion(path)
            data['target_mode']='root';path.write_text(json.dumps(data));cfg=interactive.lee_seleccion(path)
            self.assertEqual(cfg['mode'],'kernel-modeler');self.assertEqual(cfg['target_mode'],'root');self.assertIn('kernel-modeler',cfg['roles'].split(','))
    def test_modeler_is_opt_in_and_has_minimal_native_defaults(self):
        self.assertNotIn('kernel-modeler',profiles.DEFAULT_ROLES)
        self.assertEqual(software.minimo('debian')['tasks'],['standard'])
        self.assertEqual(software.minimo('fedora')['groups'],['core']);self.assertEqual(software.minimo('fedora')['environment'],'')
    def test_console_keeps_workbench_selected_and_host_destination_explicit(self):
        cfg=SimpleNamespace(mode='kernel-modeler',target_mode='root',distro='debian',root=Path('/'),native=None,apply=False)
        with patch.object(interactive,'elige',return_value='debian'),patch.object(interactive,'software_nativo',return_value=software.minimo('debian')),patch.object(interactive,'marca',return_value=[]),patch.object(interactive,'campo',return_value='/mnt/modeler'),patch('auxlib.identity.pregunta',side_effect=lambda c:c),contextlib.redirect_stdout(io.StringIO()):interactive.prepara(cfg)
        self.assertEqual(cfg.mode,'root');self.assertEqual(cfg.workbench,'kernel-modeler');self.assertEqual(cfg.roles,'base,kernel-modeler')
