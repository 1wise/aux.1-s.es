# Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Exercise mixed failures, capacity accounting and relocated replica publication."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from auxlib import capacity,catalog_v8 as cat,v8,checkstatus
from auxlib.release_sources import nixos,metalink
import test_download_recovery as recovery


class Batch(unittest.TestCase):
    setUp=recovery.Downloads.setUp
    target=recovery.Downloads.target
    def test_failures_do_not_stop_later_downloads_and_report_is_saved(self):
        good={**self.ent,'id':'last-good','policy':'015'}
        bad={**self.ent,'id':'bad-transfer','policy':'015','original_url':self.ent['original_url'].rsplit('/',1)[0]+'/missing'}
        meta={**self.ent,'id':'bad-metadata','sha256':None}
        catalog=self.root/'catalog.json';cat.guarda(catalog,{'schema':cat.SCHEMA,'entries':[meta,bad,good]})
        cfg=self.root/'config.json';cfg.write_text(json.dumps({**self.cfg,'catalog_file':str(catalog),'status_file':str(self.root/'status.json')}))
        stdout=io.StringIO();stderr=io.StringIO()
        with patch('auxlib.download_prepare.refresca',side_effect=ValueError('metadata 404')),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=v8.main(['download','--config',str(cfg),'--apply','--jobs','1'])
        self.assertEqual(code,1);self.assertEqual(self.target(good).read_bytes(),self.payload)
        report=json.loads((self.root/'download-report.json').read_text());self.assertEqual((report['ok'],report['failed']),(1,2))
        self.assertEqual({r['stage'] for r in report['entries'] if r['status']=='error'},{'resolve','download'})
        for tag in ('SKIP','DOWNLOAD','VERIFY','DONE','ERROR'):self.assertIn(tag,stderr.getvalue())
        self.assertIn('2 errores',stdout.getvalue())


class Capacity(unittest.TestCase):
    def entry(self,policy='01F',size=1024**3):
        return {'id':'fixture','family':'gentoo','policy':policy,'size_bytes':size,'artifact_type':'iso','deploy_method':'chroot','procedure_url':'https://example.org/'}
    def test_cache_images_and_extracted_tree_are_distinct(self):
        plan=capacity.prevision([self.entry()],{})
        self.assertEqual(plan['images_bytes'],{'ram':1024**3,'ssd':2*1024**3,'bastion':1024**3})
        self.assertEqual(plan['deploy_bytes']['ssd'],1024**3)
        self.assertEqual(plan['selected_bytes']['ssd'],3*1024**3)
    def test_three_presets_share_one_artifact_and_one_capacity_pool(self):
        e=self.entry();plan=capacity.prevision([e,e],{},['alpine','debian','fedora'])
        self.assertEqual(plan['budget_bytes'],{'ram':30*1024**3,'ssd':225*1024**3,'bastion':225*1024**3})
        self.assertEqual(plan['shared_savings_bytes']['ssd'],6*1024**3)
        self.assertEqual(plan['selected_bytes']['ssd'],3*1024**3)
    def test_one_preset_and_hardware_caps_remain_adjustable(self):
        plan=capacity.prevision([self.entry()],{'ram_budget_gib':8,'ssd_budget_gib':50},['alpine'])
        self.assertEqual(plan['budget_bytes']['ram'],8*1024**3);self.assertEqual(plan['budget_bytes']['ssd'],50*1024**3)
        plan=capacity.prevision([self.entry()],{},['alpine'])
        self.assertEqual(plan['budget_bytes']['ram'],10*1024**3);self.assertEqual(plan['budget_bytes']['ssd'],75*1024**3)
    def test_mount_does_not_budget_a_second_ssd_image_or_tree(self):
        plan=capacity.prevision([self.entry()],{},mode='mount')
        self.assertEqual(plan['selected_bytes']['ssd'],1024**3);self.assertEqual(plan['deploy_bytes']['ssd'],0)
    def test_unknown_sizes_are_visible_and_explicit_tree_size_is_used(self):
        known={**self.entry(),'deployment_size_bytes':123}
        unknown={**self.entry(),'id':'unresolved','size_bytes':None}
        plan=capacity.prevision([known,unknown],{})
        self.assertEqual(plan['unknown_sizes'],['unresolved']);self.assertEqual(plan['deploy_bytes']['ssd'],123);self.assertEqual(plan['estimated_deployments'],[])
    def test_presets_defer_excess_and_reuse_shared_capacity_without_overwriting_manual_choices(self):
        common={**self.entry('016',1024**3),'artifact_type':'rootfs'}
        large={**self.entry('016',100*1024**3),'id':'huge','family':'fedora','deploy_method':None,'procedure_url':None,'download_class':'heavy'}
        rows,deferred=capacity.propuesta([common,large],{},['fedora'])
        self.assertEqual(deferred,['huge']);self.assertEqual(next(e for e in rows if e['id']=='huge')['policy'],'004')
        self.assertFalse(capacity.prevision(rows,{},['fedora'])['over_budget'])
        manual={**large,'policy':'016'}
        rows,deferred=capacity.propuesta([common,large],{},['fedora'],[manual])
        self.assertEqual(next(e for e in rows if e['id']=='huge')['policy'],'016')

    def test_web_plan_import_preserves_presets_without_raising_physical_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            e={**self.entry(),'original_url':'https://example.org/x.iso','release':'1','architecture':'x86_64','kind':'installer'}
            path=Path(tmp)/'web.json';path.write_text(json.dumps({'entries':[e],'planning':{'presets':['alpine'],'ram_budget_gib':200,'ssd_budget_gib':400,'ssd_mode':'mount'}}))
            imported=cat.importa(path,{'entries':[]});self.assertEqual(imported['planning']['presets'],['alpine'])
            args=SimpleNamespace(command='download',resource=None,only=None,mode=None,apply=False,dry_run=True)
            plan=v8.plan(imported,{'ram_budget_gib':7,'ssd_budget_gib':40},args)
            self.assertEqual(plan['budget_bytes']['ram'],7*1024**3);self.assertEqual(plan['selected_bytes']['ssd'],1024**3)


class Sources(unittest.TestCase):
    def test_nixos_reads_exact_revision_size_and_hash_from_channel_table(self):
        name='nixos-minimal-26.05.123.abcdef-x86_64-linux.iso'
        body=f"<table><tr><td><a href='/nixos/26.05/nixos-26.05.123.abcdef/{name}'>{name}</a></td><td>123</td><td><tt>{'a'*64}</tt></td></tr></table>".encode()
        source={'url':'https://channels.nixos.org/nixos-26.05','allowed_hosts':['channels.nixos.org','releases.nixos.org'],'filename_pattern':r'nixos-minimal-(?P<release>26\.05\.[0-9]+\.[a-f0-9]+)-x86_64-linux\.iso'}
        row=nixos(source,None,lambda *args:body)[0]
        self.assertEqual(row['size_bytes'],123);self.assertEqual(row['sha256'],'a'*64);self.assertIn('https://releases.nixos.org/nixos/26.05/nixos-26.05.123.abcdef/',row['original_url'])
        with self.assertRaises(ValueError):nixos(source,None,lambda *args:body.replace(b'nixos-26.05.123.abcdef/',b'../../'))
    def test_metalink_and_official_sidecar_must_agree(self):
        source={'url':'https://download.opensuse.org/x.iso?metalink','artifact_url':'https://download.opensuse.org/x.iso','allowed_hosts':['download.opensuse.org'],'release':'16.0'}
        body=('<metalink><file name="x.iso"><size>123</size><hash type="sha256">'+'a'*64+'</hash></file></metalink>').encode()
        def fetch(url,*args):return body if '?' in url else ('a'*64+'  x.iso\n').encode()
        self.assertEqual(metalink(source,None,fetch)[0]['size_bytes'],123)
        def bad(url,*args):return body if '?' in url else ('b'*64+'  x.iso\n').encode()
        with self.assertRaisesRegex(ValueError,'no coinciden'):metalink(source,None,bad)


class Replica(unittest.TestCase):
    def test_nested_legacy_bastion_copy_is_recognized_and_exported_to_web(self):
        from auxlib.publication_v8 import une
        from auxlib.webapps import modelo
        from auxlib.common import guarda_json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e=cat.valida({'id':'test','family':'test','policy':'018','original_url':'https://example.org/a.iso','filename':'a.iso','release':'1','architecture':'x86_64','kind':'installer','size_bytes':123})
            catalog={'schema':cat.SCHEMA,'entries':[e]};cp=root/'catalog.json';cat.guarda(cp,catalog)
            cfg={'catalog_file':str(cp),'status_file':str(root/'custom-status.json'),'cache':str(root/'cache'),'output':str(root/'public'),'ram_dir':str(root/'ram'),'base_url':'https://aux.example.org'}
            url='https://b.example.org/isos/test/a.iso';remote={'status':'observed','files':[{'relative':'isos/test/a.iso','size':123,'public_url':url}],'errors':[]}
            snap=checkstatus.comprueba(catalog,cfg,inventario_remoto=remote);guarda_json(cfg['status_file'],snap)
            self.assertEqual(snap['entries'][0]['locations']['bastion']['status'],'present')
            joined=une([],SimpleNamespace(**cfg),lambda url:{'filename':'a.iso','format':'ISO'})
            self.assertEqual(joined[0]['observed_downloads']['bastion'],url)
            model=modelo(joined,catalog_file=cp,config=cfg);entry=next(e for e in model['entries'] if e['id']=='test')
            self.assertEqual(entry['download_urls']['bastion'],url);self.assertTrue(int(model['status']['entries']['test']['word24'],16)&(8<<16))
            remote['files'].append({**remote['files'][0],'relative':'other/a.iso'})
            snap=checkstatus.comprueba(catalog,cfg,inventario_remoto=remote)
            self.assertEqual(snap['entries'][0]['locations']['bastion']['status'],'ambiguous')


class Priority(unittest.TestCase):
    def test_priority_is_independent_of_actions_and_boot_identity(self):
        from auxlib.policy24 import combina,separa,acciones
        e={'id':'x','family':'fedora','release':'1','architecture':'amd64','kind':'image','policy':'004','original_url':'https://example.org/x.iso'}
        before=cat.valida(e);after=cat.valida({**e,'priority':'F','priority_sectors':['fedora']})
        self.assertEqual(before['identity'],after['identity']);self.assertFalse(acciones(after['policy'])['download'])
        self.assertEqual(combina('004',8,7,'F'),'F87004');self.assertEqual(separa('F87004')['priority'],'F')
    def test_malformed_priority_or_sector_is_rejected(self):
        e={'id':'x','family':'fedora','release':'1','architecture':'amd64','kind':'image','policy':'004','original_url':'https://example.org/x.iso'}
        for p in ('10','-1','G',True,1):
            with self.subTest(priority=p),self.assertRaises(ValueError):cat.valida({**e,'priority':p})
        with self.assertRaises(ValueError):cat.valida({**e,'priority_sectors':['unknown']})
    def test_user_precedes_default_and_mandatory_is_not_silently_deferred(self):
        e={'id':'a-default','family':'fedora','policy':'016','size_bytes':20*1024**3,'artifact_type':'component','architecture':'x86_64','download_class':'heavy'}
        user={**e,'id':'z-user','priority':'1'}
        rows,deferred=capacity.propuesta([e,user],{},['fedora'])
        self.assertEqual(deferred,['a-default']);self.assertTrue(int(rows[0]['policy'],16)&16)
        required={**e,'id':'mandatory','priority':'4','size_bytes':50*1024**3}
        rows,deferred=capacity.propuesta([required],{},['fedora'])
        self.assertEqual(deferred,[]);self.assertEqual(rows[0]['policy'],'016');self.assertIn('ssd',capacity.prevision(rows,{},['fedora'])['over_budget'])
    def test_cli_priority_edit_keeps_the_existing_cde_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'catalog.json';cfg=Path(tmp)/'config.json'
            e={'id':'x','family':'fedora','release':'1','architecture':'amd64','kind':'image','policy':'004','original_url':'https://example.org/x.iso'}
            cat.guarda(path,{'schema':cat.SCHEMA,'entries':[e]});cfg.write_text(json.dumps({'catalog_file':str(path)}))
            self.assertEqual(v8.main(['catalog','set-priority','--config',str(cfg),'--resource','x','--priority','A','--sector','fedora','--apply']),0)
            row=cat.carga(path)['entries'][0];self.assertEqual((row['priority'],row['policy']),('A','004'));self.assertEqual(row['priority_sectors'],['fedora'])

    def test_refreshing_an_own_recipe_preserves_manual_priority_and_sector(self):
        e={'id':'aux-debian-netboot-amd64','family':'debian','release':'old','architecture':'amd64','kind':'image','policy':'E15','original_url':'https://example.org/x.iso','recipe_owner':'AUX','priority':'D','priority_sectors':['fedora']}
        new={**e,'release':'new','priority':'0','priority_sectors':[]}
        with tempfile.TemporaryDirectory() as tmp,patch.dict('auxlib.seed_recipes.RESOLVERS',{e['id']:lambda:new}):
            row=cat.refresca({'entries':[e]},{'metadata_cache':tmp,'catalog_sources_file':str(Path(__file__).resolve().parents[1]/'config/catalog.sources.json')})['entries'][0]
        self.assertEqual((row['policy'],row['priority'],row['priority_sectors']),('E15','D',['fedora']));self.assertEqual(row['release'],'new')
