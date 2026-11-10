# Timestamp: 2026-11-10 | Version: 7.0.0-dev.4
# Author & Credits: https://www.alawise.es/1-s
"""Keep remote coverage independent from bounded, explicitly selected local images."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from auxlib import catalog, catalog_sources, setup, webapps
from test_core import entrada


class FuentesYAlmacenamiento(unittest.TestCase):
    def test_fedora_tracks_latest_released_version_without_mistaking_beta(self):
        fuente = {'id':'fedora','url':'https://fedoraproject.org/releases.json',
                  'allowed_hosts':['download.fedoraproject.org'],'pattern':r'.*\.iso'}
        dat = [{'version':v,'arch':'x86_64','link':'https://download.fedoraproject.org/'+v.replace(' ','-')+'.iso',
                'sha256':'a'*64,'size':'100','subvariant':'Everything'} for v in ('44','45','46 Beta')]
        ent = catalog_sources.fedora(fuente,json.dumps(dat).encode())
        self.assertEqual([val['release'] for val in ent],['45'])
        self.assertEqual(ent[0]['channel'],'released')

    def test_netboot_inventory_preserves_versions_and_only_publishes_source_links(self):
        txt = b'releases:\n  debian:\n    name: Debian\n    versions:\n      stable:\n      - code_name: trixie\n        name: 13\n      testing:\n      - code_name: forky\n        name: Testing\n'
        indice = json.dumps([{'name':'debian.ipxe.j2'},{'name':'live-ubuntu.ipxe.j2'},
                             {'name':'../unsafe.ipxe.j2'}]).encode()
        ents = catalog_sources.netboot({'id':'netboot','url':'https://raw.githubusercontent.com/config'},txt,indice)
        self.assertEqual(len(ents),3)
        self.assertTrue(all(ent['remote_only'] for ent in ents))
        self.assertEqual({ent['channel'] for ent in ents},{'stable','testing','upstream'})
        self.assertTrue(all(not ent.get('boot') for ent in ents))

    def test_complete_snapshot_and_plain_html_are_available_without_javascript(self):
        dat = webapps.modelo()
        rem = [ent for ent in dat['entries'] if ent.get('remote_only')]
        self.assertEqual(len(rem),186)
        self.assertTrue(any(ent['family']=='fedora' and ent['release']=='45' for ent in dat['entries']))
        html = webapps.pagina('catalogue',dat)
        self.assertIn('https://boot.netboot.xyz/live-ubuntu.ipxe',html)
        self.assertNotIn('@@CATALOG_ROWS@@',html)

    def test_download_requires_a_real_local_selection_and_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pol in (None,{'enabled':False},
                        {'enabled':True,'ids':['missing'],'max_images':1,'max_total_bytes':100}):
                with self.subTest(pol=pol), self.assertRaises(ValueError):
                    catalog.publica([entrada()],Path(tmp),descargar=True,politica=pol)

    def test_metadata_only_refresh_never_downloads_remote_menus(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(catalog,'descarga') as descarga:
            pth = catalog.publica([entrada(remote_only=True,sha256=None)],Path(tmp))
            descarga.assert_not_called()
            self.assertFalse((pth/'downloads').exists())
            self.assertNotIn('https://cdimage.debian.org/sample.iso',(pth/'light-url.txt').read_text())

    def test_selected_image_is_reused_and_catalog_stays_broad(self):
        byt = b'verified-image'
        sha = hashlib.sha256(byt).hexdigest()
        pol = {'enabled':True,'ids':['debian-one'],'max_images':1,'max_total_bytes':len(byt)}
        def guarda(ent,dst):
            dst.write_bytes(byt)
            ent['verification']['download_hash'] = 'passed'
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            ents = [entrada(sha256=sha),entrada(id='remote',remote_only=True,sha256=None)]
            with patch.object(catalog,'descarga',side_effect=guarda) as desc:
                ant = catalog.publica(ents,raiz,descargar=True,politica=pol)
                self.assertEqual(desc.call_count,1)
            with patch.object(catalog,'descarga') as desc:
                nue = catalog.publica(ents,raiz)
                desc.assert_not_called()
            self.assertEqual(len(json.loads((nue/'catalog.json').read_text())['entries']),2)
            arc_ant = next((ant/'downloads').iterdir())
            arc_nue = next((nue/'downloads').iterdir())
            self.assertEqual(arc_ant.stat().st_ino,arc_nue.stat().st_ino)
            self.assertEqual(catalog.espacio_usado(raiz),(1,len(byt)))
            with self.assertRaises(ValueError):
                catalog.publica([entrada(sha256='b'*64)],raiz,descargar=True,politica=pol)
            self.assertEqual((raiz/'current').resolve(),nue)

    def test_remote_menu_cannot_enter_the_image_cache(self):
        with self.assertRaises(ValueError):
            catalog.politica_local([entrada(remote_only=True)],
                {'enabled':True,'ids':['debian-one'],'max_images':1,'max_total_bytes':100})

    def test_fedora_45_root_uses_release_repositories(self):
        cmd = setup.comandos_base('fedora',Path('/tmp/aux-fedora45'),True,['base'],'45')[0]
        self.assertIn('--releasever=45',cmd)
        self.assertIn('--enablerepo=fedora',cmd)
        self.assertIn('--enablerepo=updates',cmd)
        self.assertNotIn('--enablerepo=rawhide',cmd)

    def test_source_only_resources_do_not_invent_mirrors(self):
        from build import motor
        eng = motor()
        ent = {'format':'ISO','status':'source','url':'https://example.org/image.iso',
               'filename':'image.iso','published':False}
        cfg = SimpleNamespace(pxe_url='https://aux.1-s.es',base_url='https://aux.1-s.es')
        self.assertEqual(eng.obt_downloads(ent,cfg),{'source':ent['url']})
        self.assertEqual(eng.obt_preferred_url(ent,cfg),ent['url'])


if __name__ == '__main__':
    unittest.main()
