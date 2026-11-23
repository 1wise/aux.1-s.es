# Timestamp: 2026-11-23 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Keep bundled resolver inputs independent of personal configuration directories."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from auxlib import catalog_v8 as catalog,settings,v8


class SourcePaths(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.xdg=self.root/'personal';self.cfg=self.xdg/'aux/config.json';self.cfg.parent.mkdir(parents=True)
        self.env=patch.dict(os.environ,{'XDG_CONFIG_HOME':str(self.xdg)},clear=False);self.env.start();self.addCleanup(self.env.stop)
        self.bundled=(ROOT/'config/catalog.sources.json').resolve()
        self.cfg.write_text('{}')

    def resolve(self,dat):return catalog.ruta_cfg(dat,'catalog_sources_file','config/catalog.sources.json',self.cfg)

    def test_old_user_configuration_without_new_field_uses_bundled_rules(self):
        self.assertEqual(self.resolve({}),self.bundled)

    def test_relative_default_in_personal_configuration_uses_bundled_rules(self):
        self.assertEqual(self.resolve({'catalog_sources_file':'config/catalog.sources.json'}),self.bundled)
        self.assertFalse((self.cfg.parent/'config').exists())

    def test_old_absolute_default_is_repaired_without_editing_configuration(self):
        old=self.cfg.parent/'config/catalog.sources.json';dat={'catalog_sources_file':str(old)};before=self.cfg.read_bytes()
        self.assertEqual(self.resolve(dat),self.bundled);self.assertEqual(self.cfg.read_bytes(),before)

    def test_existing_adjacent_default_overrides_the_bundled_rules(self):
        p=self.cfg.parent/'config/catalog.sources.json';p.parent.mkdir();p.write_text('{}')
        self.assertEqual(self.resolve({'catalog_sources_file':'config/catalog.sources.json'}),p)

    def test_missing_custom_relative_and_absolute_paths_are_not_replaced(self):
        for p in ('custom-rules.json',str(self.root/'explicit-rules.json')):
            self.assertEqual(self.resolve({'catalog_sources_file':p}),(self.cfg.parent/Path(p)).resolve())

    def test_missing_custom_rules_fail_with_actionable_error(self):
        p=self.root/'missing-custom.json'
        with self.assertRaisesRegex(ValueError,'catalog_sources_file'):
            catalog.refresca({'entries':[]},{'catalog_sources_file':str(p)})
        self.assertFalse(p.exists())

    def test_relative_catalogue_and_runtime_outputs_keep_configuration_base(self):
        dat=v8.campos_absolutos({'catalog_file':'catalog.json','output':'web','cache':'cache'},self.cfg)
        self.assertEqual(dat['catalog_sources_file'],str(self.bundled))
        self.assertEqual(dat['catalog_file'],str(self.cfg.parent/'catalog.json'));self.assertEqual(dat['output'],str(self.cfg.parent/'web'))

    def test_real_cli_refresh_from_personal_config_requires_no_missing_directory(self):
        ent={'id':'fixture','family':'test','release':'1','architecture':'x86_64','kind':'reference','policy':'004','original_url':'https://example.test/file.iso','filename':'file.iso'}
        p=self.root/'catalog.json';catalog.guarda(p,{'schema':catalog.SCHEMA,'entries':[ent]})
        self.cfg.write_text(json.dumps({'catalog_file':str(p),'catalog_sources_file':'config/catalog.sources.json','metadata_cache':str(self.root/'metadata')}))
        before=self.cfg.read_bytes();ret=subprocess.run([sys.executable,str(ROOT/'aux'),'catalog','refresh','--resource','fixture','--apply'],capture_output=True,text=True)
        self.assertEqual(ret.returncode,0,ret.stdout+ret.stderr);self.assertEqual(self.cfg.read_bytes(),before)
        self.assertFalse((self.cfg.parent/'config').exists());self.assertEqual(catalog.carga(p)['entries'][0]['id'],'fixture')


if __name__=='__main__':unittest.main()
