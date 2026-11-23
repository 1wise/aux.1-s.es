# Timestamp: 2026-11-23 | Version: 8.0.1-beta.2
# Author & Credits: https://www.alawise.es/1-s
"""Verify four sibling payloads and reject broken bundles before deployment."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from auxlib import release_bundle
spec=importlib.util.spec_from_file_location('deploy_layout',ROOT/'packaging/deploy-matrioshka.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)


class ReleaseLayout(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.base=self.root/'envelope';self.base.mkdir()
        self.dat={'schema':'aux-matrioshka-v2','version':'fixture','budget':{'suite_source_bytes':6},
                  'minimal_image':{'boot_test':'not-tested'},'repository':{'source_prefix':'aux-fixture/'},'layers':{}}
        for nom,contenido in [('web',{'index.html':'Portal'}),('sources',{'aux-fixture/README.md':'Source'}),
                              ('aux-pxe',{'README.md':'AUX'}),('tec-cli',{'README.md':'TEC'})]:
            pth=self.base/(nom+'.zip')
            with zipfile.ZipFile(pth,'w') as arc:
                for archivo,txt in contenido.items():arc.writestr(archivo,txt)
            self.capa(nom,pth)
        pth=self.base/'usb.img';pth.write_bytes(b'USB fixture');self.capa('image',pth);self.guarda()
    def capa(self,nom,pth):
        self.dat['layers'][nom]={'path':pth.name,'size_bytes':pth.stat().st_size,
            'sha256':hashlib.sha256(pth.read_bytes()).hexdigest(),'download_name':None if nom=='web' else pth.name}
    def guarda(self):(self.base/'MANIFEST.json').write_text(json.dumps(self.dat))
    def test_web_and_working_tree_receive_the_same_four_sibling_payloads(self):
        web=self.root/'web';src=self.root/'repo'
        plan=deploy.prepara(self.base,web,src);self.assertEqual(len(plan['deliverables']),4);self.assertFalse(src.exists())
        deploy.prepara(self.base,web,src,True)
        self.assertEqual((src/'suite/README.md').read_text(),'Source')
        for nom in plan['deliverables']:
            self.assertEqual((src/nom).read_bytes(),(self.base/nom).read_bytes())
            self.assertEqual((web/'downloads'/nom).read_bytes(),(src/nom).read_bytes())
            self.assertTrue((src/(nom+'.sha256')).is_file())
        self.assertFalse((src/'.git').exists())
    def test_corrupted_module_prevents_all_destination_writes(self):
        (self.base/'tec-cli.zip').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'SHA-256'):deploy.prepara(self.base,self.root/'web',self.root/'repo',True)
        self.assertFalse((self.root/'web').exists());self.assertFalse((self.root/'repo').exists())
    def test_download_name_cannot_escape_the_public_or_repository_directory(self):
        self.dat['layers']['image']['download_name']='../escape.img';self.guarda()
        with self.assertRaisesRegex(ValueError,'Nombre de descarga'):deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertFalse((self.root/'web').exists());self.assertFalse((self.root/'escape.img').exists())
    def test_wrong_source_prefix_is_rejected_before_publication(self):
        self.dat['repository']['source_prefix']='other/';self.guarda()
        with self.assertRaisesRegex(ValueError,'prefijo'):deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertFalse((self.root/'web').exists())
    def test_all_four_payloads_are_required(self):
        del self.dat['layers']['aux-pxe'];self.guarda()
        with self.assertRaisesRegex(ValueError,'Faltan capas'):deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertFalse((self.root/'web').exists())
    def test_web_restores_shared_assets_from_a_complete_module(self):
        self.dat['web_restore']=[{'path':'assets/shared.txt','layer':'aux-pxe','member':'README.md',
            'sha256':hashlib.sha256(b'AUX').hexdigest(),'size_bytes':3}];self.guarda()
        deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertEqual((self.root/'web/assets/shared.txt').read_bytes(),b'AUX')
        self.assertTrue((self.root/'web/downloads/aux-pxe.zip').is_file())
    def test_corrupt_shared_asset_reference_fails_before_any_write(self):
        self.dat['web_restore']=[{'path':'assets/shared.txt','layer':'aux-pxe','member':'README.md',
            'sha256':'0'*64,'size_bytes':3}];self.guarda()
        with self.assertRaisesRegex(ValueError,'restauración web'):deploy.prepara(self.base,self.root/'web',apply=True)
        self.assertFalse((self.root/'web').exists())
    def test_release_outputs_cannot_be_recursively_packaged_as_sources(self):
        with patch.object(release_bundle,'DIR_APP',self.root):
            with self.assertRaisesRegex(ValueError,'fuera del árbol'):release_bundle.prepara(self.root/'nested')


if __name__=='__main__':unittest.main()
