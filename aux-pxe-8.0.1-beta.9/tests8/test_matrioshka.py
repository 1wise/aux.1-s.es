# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Exercise offline layer validation and private self-assambler workspaces."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from auxlib import evolve,catalog_v8,webapps
spec=importlib.util.spec_from_file_location('deploy_matrioshka',ROOT/'packaging/deploy-matrioshka.py');deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)


class Matrioshka(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.base=self.root/'package';self.base.mkdir();(self.base/'layers').mkdir()
        for name,files in [('web',{'index.html':'Test'}),('sources',{'aux/README.md':'Source'})]:
            with zipfile.ZipFile(self.base/'layers'/(name+'.zip'),'w') as arc:
                for nom,txt in files.items():arc.writestr(nom,txt)
        (self.base/'layers/image.gz').write_bytes(b'image fixture')
        self.dat={'schema':'aux-matrioshka-v1','version':'fixture','budget':{'suite_source_bytes':6},'minimal_image':{'boot_test':'not-tested'},'layers':{}}
        for nom,path in [('web','web.zip'),('sources','sources.zip'),('image','image.gz')]:
            p=self.base/'layers'/path;self.dat['layers'][nom]={'path':'layers/'+path,'size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'download_name':path}
        self.save()
    def save(self):(self.base/'MANIFEST.json').write_text(json.dumps(self.dat))
    def test_plan_then_verified_deployment_and_optional_sources(self):
        web=self.root/'web';src=self.root/'src';deploy.prepara(self.base,web,src);self.assertFalse(web.exists())
        deploy.prepara(self.base,web,src,True);self.assertEqual((web/'index.html').read_text(),'Test');self.assertEqual((src/'aux/README.md').read_text(),'Source');self.assertTrue((web/'downloads/image.gz').is_file())
        with self.assertRaises(ValueError):deploy.prepara(self.base,web,apply=True)
    def test_corrupt_layer_fails_before_creating_destination(self):
        (self.base/'layers/image.gz').write_bytes(b'changed');web=self.root/'web'
        with self.assertRaises(ValueError):deploy.prepara(self.base,web,apply=True)
        self.assertFalse(web.exists())
    def test_paths_outside_zip_are_rejected_before_writes(self):
        p=self.base/'layers/web.zip'
        with zipfile.ZipFile(p,'w') as arc:arc.writestr('../outside','bad')
        self.dat['layers']['web'].update(size_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest());self.save()
        with self.assertRaises(ValueError):deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertFalse((self.root/'web').exists())
    def test_imported_catalogue_preserves_all_profiles_without_masks(self):
        cat=catalog_v8.carga();rows=[e for e in cat['entries'] if e['id'].startswith(('ei-', 'ap-ei-'))]
        self.assertEqual(len(rows), 142)
        current = [r for r in rows if r['provenance']['contributor'] == 'AP y Ei']
        self.assertEqual(len({r['provenance']['entry_id'] for r in current}), 139)
        self.assertEqual(len(cat['entries']), 367)
        self.assertEqual({r['id'] for r in rows if r not in current},
                         {'ei-proxmox-ve-9.2','ei-opnsense-26.1','ei-clonezilla-live-3.3.3-37'})
        for row in current:
            self.assertFalse(row['sha256'])
            self.assertFalse(row['provenance']['mask_imported'])
            self.assertEqual(row['priority'], '0')
            self.assertEqual(row['verification']['bios_boot'], 'not-tested')
        for ent in rows:
            self.assertNotIn('capability_mask',ent);self.assertEqual(ent['policy'],'004');self.assertFalse(ent.get('recipe'));self.assertFalse(ent['resolved'])
        dat=webapps.modelo();ent=next(e for e in dat['entries'] if e['id']=='ei-alpine-3.24')
        self.assertIn('source_artifacts',ent);self.assertEqual(ent['provenance']['initial_source']['contributor'],'Ei')

    def test_self_assambler_copy_excludes_workbench(self):
        source=self.root/'suite';source.mkdir();(source/'README.md').write_text('Original')
        (source/'self-assamble/proposals').mkdir(parents=True);(source/'self-assamble/proposals/private.json').write_text('private')
        proposal={'summary':'Adapt','base_manifest_sha256':evolve.manifiesto(source)['base_manifest_sha256'],'files':[{'path':'README.md','base_sha256':evolve.sha(b'Original'),'content':'Adapted'}],'validation_notes':['pending']}
        dst=evolve.aplica(proposal,source/'self-assamble/builds/test',source)
        self.assertEqual((dst/'README.md').read_text(),'Adapted');self.assertFalse((dst/'self-assamble').exists());self.assertEqual((source/'README.md').read_text(),'Original')


if __name__=='__main__':unittest.main()
