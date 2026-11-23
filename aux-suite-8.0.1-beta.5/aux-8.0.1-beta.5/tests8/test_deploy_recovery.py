# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Recover incomplete deployment plans while retaining pins and batch progress."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from auxlib import catalog_v8 as catalog, deploy_prepare as prep, v8


class DeployRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=b'verified deployment source\n'
        self.ent=catalog.valida({'id':'fixture','family':'test','release':'1','architecture':'x86_64',
            'kind':'image','policy':'E12','priority':'5','priority_sectors':['debian'],
            'original_url':'https://example.org/1/file.img','filename':'file.img',
            'artifact_type':'component','sha256':hashlib.sha256(self.data).hexdigest()})
        self.cfg={'cache':str(self.root/'cache'),'output':str(self.root/'public'),
                  'status_file':str(self.root/'state/status.json')}
    def cached(self,ent=None,legacy=False):
        ent=ent or self.ent;path=Path(self.cfg['cache'])
        if not legacy:path/=catalog.raiz_artefacto(ent)
        path/=ent['filename'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.data)
        return path
    def prepare(self,ent=None):
        ent=ent or self.ent
        return prep.prepara_despliegues({'entries':[ent]},self.cfg,{ent['id']})
    def cli(self,rows,flags=()):
        pth=self.root/'catalog.json';catalog.guarda(pth,{'schema':catalog.SCHEMA,'entries':rows})
        cfg=self.root/'config.json';cfg.write_text(json.dumps({**self.cfg,'catalog_file':str(pth)}))
        out=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(io.StringIO()):
            code=v8.main(['deploy','--config',str(cfg),*flags])
        return code,out.getvalue(),pth
    def test_verified_cache_recovers_size_without_network_or_c_permission(self):
        ent={**self.ent,'policy':'012'};self.cached(ent)
        with patch.object(prep,'refresca') as resolve:
            new,errors=self.prepare(ent)
        resolve.assert_not_called();self.assertEqual(errors,{})
        self.assertEqual(new['entries'][0]['size_bytes'],len(self.data));self.assertNotIn('size_bytes',ent)
        self.assertEqual(new['entries'][0]['artifact_identity'],ent['artifact_identity'])
        self.assertEqual(new['entries'][0]['size_observation']['source'],'verified-cache')
    def test_legacy_flat_cache_is_verified_and_measured(self):
        self.cached(legacy=True);new,errors=self.prepare()
        self.assertFalse(errors);self.assertEqual(new['entries'][0]['size_bytes'],len(self.data))
    def test_corrupt_cache_cannot_supply_capacity(self):
        self.cached().write_bytes(b'corrupt')
        with patch.object(prep,'refresca') as resolve:new,errors=self.prepare()
        resolve.assert_not_called();self.assertIn('Checksum',errors['fixture']);self.assertNotIn('size_bytes',new['entries'][0])
    def test_local_file_without_official_hash_is_not_authenticated(self):
        ent={**self.ent,'sha256':None,'policy':'012'};self.cached(ent)
        new,errors=self.prepare(ent)
        self.assertIn('C no permite resolver',errors['fixture']);self.assertIsNone(new['entries'][0]['sha256'])
    def test_official_resolution_preserves_manual_priority_and_policy(self):
        ent={**self.ent,'sha256':None,'resolved':False}
        resolved={**self.ent,'size_bytes':len(self.data),'resolved':True,'policy':'004','priority':'0'}
        with patch.object(prep,'refresca',return_value={'entries':[resolved]}) as resolve:new,errors=self.prepare(ent)
        self.assertFalse(errors);resolve.assert_called_once()
        for key in ('policy','priority','priority_sectors'):self.assertEqual(new['entries'][0][key],ent[key])
    def test_deploy_does_not_advance_authenticated_pin(self):
        resolved={**self.ent,'size_bytes':12,'sha256':'a'*64}
        with patch.object(prep,'refresca',return_value={'entries':[resolved]}):new,errors=self.prepare()
        self.assertIn('otra versión',errors['fixture']);self.assertEqual(new['entries'][0]['sha256'],self.ent['sha256'])
    def test_completed_metadata_stays_offline(self):
        ent={**self.ent,'size_bytes':len(self.data)}
        with patch.object(prep,'refresca') as resolve:new,errors=self.prepare(ent)
        resolve.assert_not_called();self.assertEqual(new['entries'][0],ent);self.assertFalse(errors)
    def test_nixos_and_agama_resolvers_clear_the_stale_unresolved_flag(self):
        root=Path(__file__).resolve().parents[1]
        rows=json.loads((root/'catalog.json').read_text())['entries']
        for rid in ('other-tool-x86_64-nixos-minimal-26','other-tool-x86_64-agama-installer'):
            known=next(e for e in rows if e['id']==rid)
            old={**known,'resolved':False,'size_bytes':None,'sha256':None}
            cfg={**self.cfg,'metadata_cache':str(self.root/'metadata'),'catalog_sources_file':str(root/'config/catalog.sources.json')}
            with self.subTest(id=rid),patch('auxlib.catalog_downloads.candidatos',return_value=[known]),patch('auxlib.catalog_downloads.comprueba_enlace',return_value={}):
                new,errors=prep.prepara_despliegues({'entries':[old]},cfg,{rid})
            self.assertFalse(errors);self.assertTrue(new['entries'][0]['resolved'])
            self.assertEqual(new['entries'][0]['size_bytes'],known['size_bytes'])
            self.assertEqual(new['entries'][0]['sha256'],known['sha256'])
    def test_cli_measures_saves_and_really_copies_existing_source(self):
        self.cached()
        with patch.object(prep,'refresca') as resolve,patch('auxlib.precautions.protege'):
            code,out,pth=self.cli([self.ent],['--apply'])
        self.assertEqual(code,0);resolve.assert_not_called()
        saved=catalog.carga(pth)['entries'][0];self.assertEqual(saved['size_bytes'],len(self.data))
        self.assertEqual((Path(self.cfg['output'])/catalog.ruta_publicada(saved,'ssd')).read_bytes(),self.data)
        self.assertTrue(Path(str(pth)+'.sha256').is_file());self.assertIn('0 errores',out)
    def test_resolution_and_transfer_errors_do_not_block_remaining_destinations(self):
        bad={**self.ent,'id':'bad-metadata','sha256':None}
        failed={**self.ent,'id':'bad-deploy','size_bytes':len(self.data)}
        good={**self.ent,'id':'last-good','policy':'E1A','size_bytes':len(self.data)}
        def deploy(ent,cfg,dest,args):
            if ent['id']=='bad-deploy' or dest=='ssd':raise ValueError('destination failed')
        with patch.object(prep,'refresca',side_effect=ValueError('metadata 404')),patch.object(v8,'despliega',side_effect=deploy) as run:
            code,out,_=self.cli([bad,failed,good],['--apply'])
        self.assertEqual(code,1);self.assertEqual(run.call_count,3)
        report=json.loads((self.root/'state/deploy-report.json').read_text())
        self.assertEqual((report['ok'],report['failed']),(1,3))
        self.assertEqual(report['entries'][-1]['destination'],'bastion');self.assertIn('metadata 404',out)
    def test_dry_run_does_not_resolve_save_or_deploy(self):
        with patch.object(prep,'prepara_despliegues') as prepare,patch.object(v8,'despliega') as run:
            code,_,pth=self.cli([self.ent],['--dry-run','--apply'])
        self.assertEqual(code,0);prepare.assert_not_called();run.assert_not_called()
        self.assertNotIn('size_bytes',catalog.carga(pth)['entries'][0]);self.assertFalse((self.root/'state').exists())
    def test_deploy_ssd_ignores_unknown_ram_only_entry(self):
        excluded={**self.ent,'id':'ram-only','policy':'E11'}
        good={**self.ent,'size_bytes':len(self.data)}
        with patch.object(prep,'refresca') as resolve,patch.object(v8,'despliega') as run:
            code,_,_=self.cli([excluded,good],['ssd','--apply'])
        self.assertEqual(code,0);resolve.assert_not_called();run.assert_called_once()
        self.assertEqual(run.call_args.args[0]['id'],'fixture')
    def test_unknown_size_never_becomes_zero_to_bypass_budget(self):
        ent={**self.ent,'policy':'012'}
        with patch.object(v8,'despliega') as run:code,_,_=self.cli([ent],['--apply'])
        self.assertEqual(code,1);run.assert_not_called()
        report=json.loads((self.root/'state/deploy-report.json').read_text());self.assertEqual(report['failed'],1)


if __name__=='__main__':unittest.main()
