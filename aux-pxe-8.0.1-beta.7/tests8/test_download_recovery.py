# Timestamp: 2026-11-27 | Version: 8.0.1-beta.7
# Author & Credits: https://www.alawise.es/1-s
"""Exercise metadata preparation, actual curl resumes and pinned signature results."""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from auxlib import v8,catalog_v8 as catalog,download_prepare as prep,arch_netboot as arch
from auxlib.catalog import descubre


class Downloads(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.payload=b'AUX actual payload\n'*256;self.events=[];data=self.payload;events=self.events
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                req_path='/'+self.path.rsplit('/',1)[-1]
                events.append(dict(self.headers));body=data if req_path!='/corrupt' else b'X'*len(data)
                if req_path=='/range-416' and self.headers.get('Range'):self.send_response(416);self.send_header('Content-Length','0');self.end_headers();return
                if req_path=='/missing':self.send_response(404);self.send_header('Content-Length','0');self.end_headers();return
                start=int(self.headers['Range'].split('=')[1].split('-')[0]) if self.headers.get('Range') and req_path!='/ignore-range' else 0
                self.send_response(206 if start else 200);self.send_header('Content-Length',str(len(body)-start));self.send_header('ETag','"current"')
                if start:self.send_header('Content-Range',f'bytes {start}-{len(body)-1}/{len(body)}')
                self.end_headers()
                try:self.wfile.write(body[start:])
                except (BrokenPipeError,ConnectionResetError):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=self.server.serve_forever,daemon=True).start();self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.ent=catalog.valida({'id':'fixture','family':'test','release':'1','architecture':'x86_64','kind':'image','policy':'E15','filename':'file.iso','artifact_type':'iso','original_url':f'http://127.0.0.1:{self.server.server_port}/weekly-builds/file','size_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        self.cfg={'cache':str(self.root/'cache')};self.args=SimpleNamespace(resource=None,only=None,refresh=False)
    def target(self,ent=None):
        ent=ent or self.ent;return Path(self.cfg['cache'])/catalog.raiz_artefacto(ent)/ent['filename']
    def partial(self,path='/file'):
        self.ent['original_url']=self.ent['original_url'].rsplit('/',1)[0]+path
        p=self.target();p.parent.mkdir(parents=True);p.with_name(p.name+'.part').write_bytes(self.payload[:20]);p.with_name(p.name+'.part.headers').write_text('HTTP/1.1 301 Redirect\nETag: "proxy"\n\nHTTP/1.1 200 OK\nETag: "current"\n\n');return p
    def test_real_curl_download_is_promoted_only_after_matching_hash(self):
        p=v8.descarga(self.ent,self.cfg);self.assertEqual(p.read_bytes(),self.payload);self.assertFalse(p.with_name(p.name+'.part').exists())
    def test_real_resume_uses_final_response_validator(self):
        p=self.partial();v8.descarga(self.ent,self.cfg);self.assertEqual(p.read_bytes(),self.payload);self.assertEqual(self.events[0]['Range'],'bytes=20-');self.assertEqual(self.events[0]['If-Range'],'"current"')
    def test_ignored_range_restarts_once_from_zero(self):
        p=self.partial('/ignore-range');v8.descarga(self.ent,self.cfg);self.assertEqual(p.read_bytes(),self.payload);self.assertEqual(len(self.events),2);self.assertIn('Range',self.events[0]);self.assertNotIn('Range',self.events[1])
    def test_http_416_restarts_once_from_zero(self):
        p=self.partial('/range-416');v8.descarga(self.ent,self.cfg);self.assertEqual(p.read_bytes(),self.payload);self.assertEqual(len(self.events),2);self.assertNotIn('Range',self.events[1])

    def test_complete_partial_is_recovered_without_network(self):
        p=self.target();p.parent.mkdir(parents=True);p.with_name(p.name+'.part').write_bytes(self.payload);v8.descarga(self.ent,self.cfg);self.assertEqual(self.events,[]);self.assertEqual(p.read_bytes(),self.payload)
    def test_wrong_hash_is_never_published(self):
        self.ent['original_url']=self.ent['original_url'].rsplit('/',1)[0]+'/corrupt'
        with self.assertRaisesRegex(ValueError,'Checksum distinto'):v8.descarga(self.ent,self.cfg)
        self.assertFalse(self.target().exists());self.assertFalse(self.target().with_name('file.iso.part').exists())
    def test_actual_http_failure_reports_curl_and_status(self):
        self.ent['original_url']=self.ent['original_url'].rsplit('/',1)[0]+'/missing'
        with self.assertRaisesRegex(ValueError,'curl 22 / HTTP 404'):v8.descarga(self.ent,self.cfg)
    def test_prepare_refreshes_only_selected_policy_permitted_resource(self):
        old=copy.deepcopy(self.ent);old['sha256']='1'*64;other=copy.deepcopy(old);other['id']='other';cat={'entries':[old,other]};self.args.resource=['fixture']
        with patch.object(prep,'refresca',return_value={'entries':[self.ent]}) as resolve:
            new,errors=prep.prepara_descargas(cat,self.cfg,self.args)
        self.assertEqual(errors,{});self.assertEqual(resolve.call_count,1);self.assertEqual(new['entries'][0]['sha256'],self.ent['sha256']);self.assertEqual(new['entries'][1],other)
    def test_prepare_preserves_pinned_policy_and_verified_cache_without_network(self):
        ent={**self.ent,'policy':'015'}
        with patch.object(prep,'refresca') as resolve:prep.prepara_descargas({'entries':[ent]},self.cfg,self.args);resolve.assert_not_called()
        p=self.target();p.parent.mkdir(parents=True);p.write_bytes(self.payload)
        with patch.object(prep,'refresca') as resolve:prep.prepara_descargas({'entries':[self.ent]},self.cfg,self.args);resolve.assert_not_called()
    def test_immutable_pinned_image_is_not_advanced_implicitly(self):
        ent={**self.ent,'original_url':'https://example.test/releases/1/pinned.iso'}
        with patch.object(prep,'refresca') as resolve:prep.prepara_descargas({'entries':[ent]},self.cfg,self.args);resolve.assert_not_called()

    def test_cli_saves_refreshed_metadata_and_downloads_with_new_hash(self):
        old={**self.ent,'sha256':'1'*64};catfile=self.root/'catalog.json';catalog.guarda(catfile,{'schema':catalog.SCHEMA,'entries':[old]});cfg=self.root/'fast-boot.json';cfg.write_text(json.dumps({**self.cfg,'catalog_file':str(catfile)}))
        with patch.object(prep,'refresca',return_value={'entries':[self.ent]}):self.assertEqual(v8.main(['download','--config',str(cfg),'--resource','fixture','--apply']),0)
        self.assertEqual(catalog.carga(catfile)['entries'][0]['sha256'],self.ent['sha256']);self.assertEqual(self.target().read_bytes(),self.payload)
    def test_dry_run_has_no_metadata_queries_or_download_requests(self):
        catfile=self.root/'catalog.json';catalog.guarda(catfile,{'schema':catalog.SCHEMA,'entries':[self.ent]});cfg=self.root/'fast-boot.json';cfg.write_text(json.dumps({**self.cfg,'catalog_file':str(catfile)}))
        with patch.object(prep,'prepara_descargas') as prepare:self.assertEqual(v8.main(['download','--config',str(cfg),'--dry-run']),0);prepare.assert_not_called()
        self.assertEqual(self.events,[])


class OriginMetadata(unittest.TestCase):
    def test_gentoo_root_manifest_keeps_dated_directory(self):
        source={'id':'gentoo','url':'https://distfiles.gentoo.org/releases/amd64/autobuilds/latest-install-amd64-minimal.txt','format':'gentoo-latest','allowed_hosts':['distfiles.gentoo.org'],'pattern':r'install-amd64-minimal-(?P<release>\d{8}T\d{6}Z)\.iso','defaults':{}}
        nom='install-amd64-minimal-20261122T164601Z.iso';calls=[]
        def fetch(url,*args):calls.append(url);return ('20261122T164601Z/'+nom+' 123\n').encode() if url==source['url'] else ('a'*64+'  '+nom+'\n').encode()
        row=descubre(source,Path('/unused'),fetch)[0];self.assertIn('/autobuilds/20261122T164601Z/',row['original_url']);self.assertEqual(row['sha256'],'a'*64);self.assertTrue(calls[-1].endswith(nom+'.sha256'))
    def test_gentoo_legacy_current_directory_resolves_dated_path(self):
        source={'id':'gentoo','url':'https://distfiles.gentoo.org/releases/amd64/autobuilds/current-install-amd64-minimal/latest-install-amd64-minimal.txt','format':'gentoo-latest','allowed_hosts':['distfiles.gentoo.org'],'pattern':r'install-amd64-minimal-(?P<release>\d{8}T\d{6}Z)\.iso','defaults':{}}
        nom='install-amd64-minimal-20261122T164601Z.iso'
        def fetch(url,*args):return (nom+' 123\n').encode() if url==source['url'] else ('a'*64+'  '+nom+'\n').encode()
        row=descubre(source,Path('/unused'),fetch)[0];self.assertIn('/autobuilds/20261122T164601Z/',row['original_url'])

    def test_daily_image_cannot_be_resolved_from_weekly_rule(self):
        ent={'id':'daily','original_url':'https://cdimage.debian.org/cdimage/daily-builds/daily/current/amd64/iso-cd/debian-testing-amd64-netinst.iso','filename':'debian-testing-amd64-netinst.iso','family':'debian','release':'daily','architecture':'amd64','kind':'installer','policy':'E15'}
        with tempfile.TemporaryDirectory() as tmp,patch('auxlib.catalog.consulta') as fetch:
            with self.assertRaisesRegex(ValueError,'otra rama'):catalog.refresca({'entries':[ent]},{'catalog_sources_file':str(ROOT/'config/catalog.sources.json'),'metadata_cache':tmp})
            fetch.assert_not_called()

    def test_signature_requires_successful_gpg_and_pinned_primary_key(self):
        valid='[GNUPG:] VALIDSIG '+'A'*40+' 2023-08-28 1 0 4 0 22 10 00 '+arch.FINGERPRINT+'\n'
        cases=[(0,valid,True),(0,valid.replace(arch.FINGERPRINT,'B'*40),False),(1,valid,False),(0,valid+'[GNUPG:] REVKEYSIG bad\n',False)]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sig';p.write_bytes(b'signature')
            for code,status,ok in cases:
                results=[SimpleNamespace(returncode=0),SimpleNamespace(returncode=code,stdout=status)]
                with self.subTest(code=code,status=status),patch.object(arch.shutil,'which',return_value='/usr/bin/gpg'),patch.object(arch.subprocess,'run',side_effect=results):
                    if ok:self.assertEqual(arch.verifica(p,p)['fingerprint'],arch.FINGERPRINT)
                    else:
                        with self.assertRaises(ValueError):arch.verifica(p,p)


if __name__=='__main__':unittest.main()
