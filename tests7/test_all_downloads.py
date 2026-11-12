# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Cover all selected payloads, source adapters and failed-update preservation."""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch
from urllib.parse import urlsplit,urlunsplit

from auxlib import catalog, catalog_downloads as desc, catalog_workflow as flujo
from auxlib.common import DIR_APP


class TodasDescargas(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((DIR_APP/'config/catalog.sources.json').read_text())
        self.urls=[lin for lin in (DIR_APP/'url.txt').read_text().splitlines() if lin.startswith('https://')]

    def opciones(self,fuente,*args):
        sal=[]
        for url in self.urls:
            slot=next((s for s in self.config['download_slots'] if desc.coincide(url,s)),None)
            if slot is None:continue
            if slot['source_id']!=fuente['id']:continue
            mat=re.fullmatch(slot['filename_pattern'],desc.nombre_archivo(url))
            rel=mat.groupdict().get('release') or 'rolling'
            nue=re.sub(r'[0-9]+(?!.*[0-9])',lambda m:str(int(m[0])+1).zfill(len(m[0])),rel)
            if re.fullmatch(slot['filename_pattern'],desc.nombre_archivo(url).replace(rel,nue)):
                url=url.replace(rel,nue);rel=nue
            host=next(h for h in fuente['allowed_hosts'] if not h.startswith('*.'))
            part=urlsplit(url);url=urlunsplit(('https',host,part.path,part.query,''))
            sal.append({'original_url':url,'release':rel,'size_bytes':1024,'sha256':'a'*64})
        return sal

    def ejecuta(self,raiz,fallo=None):
        cfg=dict(self.config,download_lists={'all':'url.txt'})
        (raiz/'url.txt').write_text('\n'.join(self.urls)+'\n')
        def fuente(f,*args):
            if f['id']==fallo:raise OSError('upstream unavailable')
            return self.opciones(f)
        with patch.object(desc,'candidatos',side_effect=fuente),contextlib.redirect_stdout(io.StringIO()):
            return desc.rastrea_descargas(cfg,raiz/'sources.json',raiz,lambda *args:b'',
                comprobar=lambda *args:{'http':'passed','size_bytes':1024})

    def test_all_49_urls_have_exactly_one_edition_and_channel_rule(self):
        self.assertEqual(len(self.urls),49)
        for url in self.urls:
            self.assertEqual(sum(desc.coincide(url,s) for s in self.config['download_slots']),1,url)
        self.assertEqual(len(self.config['sync_rules']),49)
        self.assertEqual({s['id'] for s in self.config['download_slots']},
                         {r['source_id'] for r in self.config['sync_rules']})

    def test_full_resolution_and_sync_keep_all_49_members_and_storage_classes(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);ents,inf=self.ejecuta(raiz)
            self.assertTrue(inf['complete']);self.assertEqual(inf['resolved'],49)
            self.assertEqual(inf['http_passed'],49);self.assertEqual(len(ents),49)
            cat=raiz/'catalog.json';cat.write_text(json.dumps({'entries':ents}))
            cfg=raiz/'config.json';cfg.write_text(json.dumps(self.config))
            for nom in ('light-url.txt','heavy-url.txt'):(raiz/nom).write_text((DIR_APP/nom).read_text())
            plan=flujo.plan_listas(cfg,cat,raiz)
            self.assertGreater(len(plan),0)
            for pth,ant,nue in plan:
                self.assertEqual(len([l for l in ant.splitlines() if l.startswith('https://')]),
                                 len([l for l in nue.splitlines() if l.startswith('https://')]))
            flujo.aplica_listas(plan)
            self.assertTrue(any('Fedora-Server-netinst' in e['original_url'] for e in ents))
            self.assertTrue(any('Workstation-Live' in e['original_url'] for e in ents))
            self.assertTrue(any('Cloud-Base-Generic' in e['original_url'] for e in ents))

    def test_one_failed_source_does_not_prevent_checking_the_other_downloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            ents,inf=self.ejecuta(Path(tmp),'alpine-aarch64')
        self.assertEqual(inf['total'],49);self.assertEqual(inf['resolved'],48)
        self.assertEqual(len(inf['resources']),49);self.assertFalse(inf['complete'])
        self.assertIn('upstream unavailable',next(r['error'] for r in inf['resources'] if r['status']=='failed'))

    def test_unmapped_user_added_url_is_explicit_in_the_report(self):
        self.urls.append('https://example.org/unconfigured.iso')
        with tempfile.TemporaryDirectory() as tmp:
            ents,inf=self.ejecuta(Path(tmp))
        self.assertEqual(inf['total'],50);self.assertEqual(inf['resolved'],49)
        self.assertEqual(inf['resources'][-1]['status'],'unmapped')

    def test_incomplete_resolution_preserves_current_and_writes_a_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);out=raiz/'out';out.mkdir();(out/'current').mkdir()
            (out/'current/marker').write_text('previous publication')
            cfgfile=raiz/'sources.json';cfgfile.write_text(json.dumps(self.config))
            cfg=SimpleNamespace(config=cfgfile,output=out,cache=raiz/'cache',select=None,evidence=None,download=False)
            inf={'complete':False,'resolved':48,'total':49,'resources':[]}
            with patch.object(desc,'rastrea_descargas',return_value=([],inf)),self.assertRaises(ValueError):
                catalog.actualiza(cfg)
            self.assertEqual((out/'current/marker').read_text(),'previous publication')
            self.assertEqual(json.loads((out/'crawl-report.json').read_text())['resolved'],48)

    def test_checksum_sections_do_not_confuse_blake3_with_sha256(self):
        txt='### SHA256SUMS:\n'+'a'*64+'  image.iso\n### B3SUMS:\n'+'b'*64+'  image.iso\n'
        self.assertEqual(desc.lee_sumas(txt),{'image.iso':'a'*64})
        self.assertEqual(desc.lee_sumas('SHA256 (image.iso) = '+'c'*64),{'image.iso':'c'*64})

    def test_fedora_resolver_rejects_cross_edition_or_architecture_substitution(self):
        slot=next(s for s in self.config['download_slots'] if 'Server-netinst-x86_64' in s['label'])
        with self.assertRaises(ValueError):desc.resuelve_slot(slot,[{'original_url':'https://download.fedoraproject.org/Fedora-Workstation-Live-45-1.4.x86_64.iso'}])
        with self.assertRaises(ValueError):desc.resuelve_slot(slot,[{'original_url':'https://download.fedoraproject.org/Fedora-Server-netinst-aarch64-45-1.4.iso'}])

    def test_github_asset_metadata_and_alpine_yaml_are_read_without_images(self):
        github={'format':'github-assets','url':'https://api.github.com/repo/latest','allowed_hosts':['api.github.com']}
        data={'tag_name':'3.0','assets':[{'browser_download_url':'https://github.com/boot.efi','size':100,'digest':'sha256:'+'a'*64}]}
        ent=desc.candidatos(github,Path('/unused'),lambda *args:json.dumps(data).encode())[0]
        self.assertEqual((ent['size_bytes'],ent['sha256']),(100,'a'*64))
        alpine={'format':'alpine-releases','url':'https://example.org/latest-releases.yaml','allowed_hosts':['example.org']}
        ent=desc.candidatos(alpine,Path('/unused'),lambda *args:b'- file: alpine-netboot-3.24.4-x86.tar.gz\n  version: 3.24.4\n  size: 12\n')[0]
        self.assertEqual(ent['original_url'],'https://example.org/alpine-netboot-3.24.4-x86.tar.gz')

    def test_html_rss_and_checksum_sources_find_real_files_only(self):
        fuente={'format':'artifact-html','url':'https://example.org/','allowed_hosts':['example.org']}
        ent=desc.candidatos(fuente,Path('/unused'),lambda *args:b'<a href="image-2.iso">image</a><a href="image-2.iso.sha256">sum</a>')
        self.assertEqual([e['original_url'] for e in ent],['https://example.org/image-2.iso'])
        fuente['format']='artifact-rss'
        ent=desc.candidatos(fuente,Path('/unused'),lambda *args:b'<rss><channel><item><link>https://example.org/image-3.iso/download</link></item></channel></rss>')
        self.assertEqual(desc.nombre_archivo(ent[0]['original_url']),'image-3.iso')

    def test_configured_mirror_wildcards_do_not_match_lookalike_domains(self):
        catalog.url_segura('https://mirror.dl.sourceforge.net/a.iso',['*.dl.sourceforge.net'])
        for host in ('dl.sourceforge.net.evil.invalid','mirror.dl.sourceforge.net.evil.invalid'):
            with self.assertRaises(ValueError):catalog.url_segura('https://'+host+'/a.iso',['*.dl.sourceforge.net'])

    def test_removed_announced_beta_falls_back_within_the_same_channel_and_reports_it(self):
        slot=dict(self.config['download_slots'][0],id='test-beta',source_id='beta',
                  filename_pattern=r'tool-(?P<release>[0-9]+)-beta\.iso',latest_available=True)
        conf={'download_slots':[slot],'download_sources':[{'id':'beta','format':'artifact-html',
              'url':'https://example.org/','allowed_hosts':['example.org']}],'download_lists':{'all':'url.txt'}}
        opciones=[{'original_url':'https://example.org/tool-'+v+'-beta.iso'} for v in ('2','3')]
        def comprobar(url,*args):
            if 'tool-3-' in url:raise urllib.error.HTTPError(url,404,'Not Found',None,None)
            return {'http':'passed','size_bytes':100}
        with tempfile.TemporaryDirectory() as tmp,patch.object(desc,'candidatos',return_value=opciones),contextlib.redirect_stdout(io.StringIO()):
            raiz=Path(tmp);(raiz/'url.txt').write_text('https://example.org/tool-1-beta.iso\n')
            ents,inf=desc.rastrea_descargas(conf,raiz/'sources.json',raiz,lambda *args:b'',comprobar)
        self.assertTrue(inf['complete']);self.assertEqual(ents[0]['release'],'2')
        self.assertEqual(inf['resources'][0]['unavailable_newer_versions'][0]['release'],'3')

    def test_head_fallback_never_reads_a_payload_and_does_not_store_mirror_tickets(self):
        class Respuesta:
            headers={'Content-Length':'100'}
            url='https://example.org/image.iso?temporary-secret=123'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):raise AssertionError('An image body must not be read by the crawler.')
        from unittest.mock import Mock
        abridor=Mock();abridor.open.side_effect=[urllib.error.HTTPError('https://example.org/image.iso',405,'HEAD unavailable',None,None),Respuesta()]
        with patch.object(desc.urllib.request,'build_opener',return_value=abridor):
            dat=desc.comprueba_enlace('https://example.org/image.iso',['example.org'],100)
        self.assertEqual(dat['final_url'],'https://example.org/image.iso')
        self.assertEqual(abridor.open.call_args.args[0].get_header('Range'),'bytes=0-0')

    def test_interactive_crawl_honors_the_selected_download_list(self):
        from auxlib import console_ui
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);cfg=raiz/'sources.json';cfg.write_text(json.dumps(self.config))
            urls=raiz/'chosen-url.txt';urls.write_text(self.urls[0]+'\n')
            with patch.object(console_ui,'campo',side_effect=[str(cfg),str(raiz/'out'),str(raiz/'http'),str(urls),'RASTREAR','']), \
                 patch.object(catalog,'actualiza',return_value=raiz/'out/releases/test') as update, \
                 contextlib.redirect_stdout(io.StringIO()):
                resultado=flujo.rastreo_interactivo(url_file=urls)
            self.assertTrue(resultado.succeeded)
            self.assertEqual(update.call_args.args[0].url_file,urls)

    def test_cli_passes_the_custom_download_list_to_the_interactive_app(self):
        from auxlib import localtools
        with patch.object(localtools,'catalogo') as abrir:
            catalog.main(['-i','--url-file','custom-url.txt'])
        self.assertEqual(abrir.call_args.args[-1],Path('custom-url.txt'))


if __name__=='__main__':unittest.main()
