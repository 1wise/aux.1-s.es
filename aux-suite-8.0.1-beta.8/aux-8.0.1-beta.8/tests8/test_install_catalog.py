# Timestamp: 2026-11-27 | Version: 8.0.1-beta.8
# Author & Credits: https://www.alawise.es/1-s
"""Exercise the inputs and publication actually used by the native installer."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from auxlib import install_catalog as instal, checkstatus, catalog_v8

spec = importlib.util.spec_from_file_location('web_install', ROOT/'install-web.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class CatalogoInstalado(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base/'server'
        self.cfg = self.base/'xdg/aux/config.json'
        self.cfg.parent.mkdir(parents=True)
        entorno = patch.dict(os.environ, {'XDG_CONFIG_HOME':str(self.cfg.parents[1]), 'AUX_CONFIG_FILE':''})
        entorno.start()
        self.addCleanup(entorno.stop)
        self.dat = web.configura(json.loads((ROOT/'fast-boot.json').read_text()), self.root)
        self.cat = self.cfg.parent/'catalog.json'
        self.ent = json.loads((ROOT/'catalog.json').read_text())['entries'][0]
        catalog_v8.guarda(self.cat, {'entries':[self.ent]})

    def test_plan_reads_personal_catalogue_and_creates_nothing(self):
        self.cfg.write_text(json.dumps(self.dat))
        for mods in (['aux-pxe'], ['aux-pxe','tec-cli']):
            ret = subprocess.run([sys.executable, str(ROOT/'install-web.py'), '--root', str(self.root),
                                  '--modules', *mods], capture_output=True, text=True, cwd=self.base)
            self.assertEqual(ret.returncode, 0, ret.stderr+ret.stdout)
            self.assertIn(str(self.cat), ret.stdout)
            self.assertFalse(self.root.exists())

    def test_explicit_config_wins_and_missing_custom_input_fails_before_writes(self):
        self.cfg.write_text('{}')
        cfg = self.base/'settings.json'
        cfg.write_text(json.dumps({'catalog_file':'other.json'}))
        with self.assertRaisesRegex(ValueError, 'other.json'):
            instal.seleccion(ROOT,self.root,self.dat,cfg)
        self.assertFalse(self.root.exists())

    def test_first_install_reuses_existing_personal_file_or_imports_legacy_once(self):
        plan = instal.seleccion(ROOT,self.root,self.dat)
        self.assertEqual(plan[1],self.cat)
        self.assertIsNone(plan[3])
        self.root.mkdir()
        self.cat.rename(self.root/'catalog.json')
        plan = instal.seleccion(ROOT,self.root,self.dat)
        self.assertEqual(plan[3],self.root/'catalog.json')
        instal.genera_instalacion(self.root,plan,lambda *args: None)
        self.assertEqual(self.cat.read_bytes(),(self.root/'catalog.json').read_bytes())
        self.assertEqual(self.cat.stat().st_mode & 0o777,0o600)

    def test_tec_only_plan_does_not_read_catalogue(self):
        ret = subprocess.run([sys.executable,str(ROOT/'install-web.py'),'--modules','tec-cli',
                              '--config',str(self.base/'absent.json')],capture_output=True,text=True)
        self.assertEqual(ret.returncode,0,ret.stdout+ret.stderr)

    def test_real_generation_reuses_inventory_from_selected_config(self):
        self.cfg.write_text(json.dumps(self.dat))
        cat = catalog_v8.carga(self.cat,self.cfg)
        ref = cat['entries'][0]
        remoto = {'status':'observed','files':[{'relative':ref['filename'],
                  'size':ref.get('size_bytes') or 1024,'public_url':'https://mirror.example/'+ref['filename']}],
                  'errors':[]}
        estado = self.cfg.parent/'state/status.json'
        estado.parent.mkdir()
        estado.write_text(json.dumps(checkstatus.comprueba(cat,self.dat,self.cfg,inventario_remoto=remoto)))
        antes = estado.read_bytes()
        (self.root/'html/downloads').mkdir(parents=True)
        (self.root/'aux').symlink_to(ROOT/'aux')
        from auxlib.release_bundle import nombres
        for archivo in nombres().values():
            (self.root/'html/downloads'/archivo).write_bytes(b'fixture')
        plan = instal.seleccion(ROOT,self.root,self.dat)
        def ejecuta(*cmd):
            ret = subprocess.run(cmd,capture_output=True,text=True,cwd=self.base)
            self.assertEqual(ret.returncode,0,ret.stdout+ret.stderr)
        instal.genera_instalacion(self.root,plan,ejecuta,tec='link')
        self.assertEqual(antes,estado.read_bytes())
        cat_pub=json.loads((self.root/'html/catalog/catalog.json').read_text())['entries']
        self.assertEqual([e['id'] for e in cat_pub],[ref['id']])
        self.assertIn('https://mirror.example/',json.dumps(cat_pub[0]['download_urls']))
        pagina=(self.root/'html/release-8.html').read_text()
        for archivo in nombres().values():self.assertIn('href="downloads/'+archivo+'"',pagina)
        for nom in ('release-7.html','readme-7.html','index.html'):
            self.assertIn('href="release-8.html"',(self.root/'html'/nom).read_text())
        self.assertFalse((self.root/'catalog.json').exists())
