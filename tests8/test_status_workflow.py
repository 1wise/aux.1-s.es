# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Exercise identity, real files, remote failures and the publication boundary."""
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from auxlib import catalog_v8 as catalog
from auxlib import checkstatus, policy24, v8
from auxlib.common import guarda_json


class Bits(unittest.TestCase):
    def test_all_policies_round_trip_without_reserved_bits(self):
        for num in range(4096):
            val=f'{num:03X}';out=policy24.separa(policy24.combina(val,11,7))
            self.assertEqual(out,{'policy':val,'availability':11,'state':7,'reserved':0})

    def test_reserved_and_malformed_words_are_rejected(self):
        for word in ('F00000','100000','FFFF','0x1234','-00001'):
            with self.assertRaises(ValueError):policy24.separa(word)
        for word in ('0000','ZZZ',True,0):
            with self.assertRaises(ValueError):policy24.politica(word)

    def test_archive_preserves_and_download_without_deploy_is_valid(self):
        self.assertTrue(policy24.acciones('080')['preserve'])
        act=policy24.acciones('010')
        self.assertTrue(act['download']);self.assertEqual(act['locations'],[])
        self.assertFalse(policy24.acciones('002')['download'])


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for nom in ('public','cache','ram'): (self.root/nom).mkdir()
        byt=bytearray(34822);byt[32769:32774]=b'CD001';self.payload=bytes(byt)
        self.ent={'id':'debian-test-amd64','family':'debian','release':'1.0','architecture':'x86_64',
                  'kind':'installer','policy':'112','filename':'debian-test.iso','artifact_type':'iso',
                  'original_url':'https://example.test/debian-test.iso',
                  'sha256':hashlib.sha256(self.payload).hexdigest(),'size_bytes':len(self.payload)}
        self.catpath=self.root/'catalog.json';catalog.guarda(self.catpath,{'schema':catalog.SCHEMA,'entries':[self.ent]})
        self.cfg={'catalog_file':str(self.catpath),'cache':str(self.root/'cache'),'output':str(self.root/'public'),
                  'ram_dir':str(self.root/'ram'),'base_url':'https://aux.example.test','pxe_url':'http://pxe.example.test',
                  'download_url':'https://b.example.test','status_file':str(self.root/'status.json'),
                  'evidence_file':str(self.root/'evidence.json'),'ssd_budget_gib':2,'ram_budget_gib':1,
                  'generate':{'tec':'off'},'checkstatus':{'max_age_seconds':3600,'bastion':{'enabled':False}}}
        self.config=self.root/'fast-boot.json';guarda_json(self.config,self.cfg)
        self.cat=catalog.carga(config=self.config);self.ent=self.cat['entries'][0]

    def check(self,**kwargs):return checkstatus.comprueba(self.cat,self.cfg,self.config,**kwargs)

    def run_aux(self,*args):
        return subprocess.run([sys.executable,str(ROOT/'aux'),*args,'--config',str(self.config)],capture_output=True,text=True)

    def test_empty_locations_never_claim_boot_or_deployment(self):
        row=self.check()['entries'][0]
        self.assertEqual(row['state'],0);self.assertEqual(row['availability'],0)
        self.assertEqual(row['policy'],'112');self.assertEqual(row['word24'],'000112')
        self.assertEqual(row['locations']['bastion']['status'],'unknown')

    def test_cache_presence_is_not_deployment(self):
        (self.root/'cache'/self.ent['filename']).write_bytes(self.payload)
        row=self.check()['entries'][0]
        self.assertEqual(row['state'],1);self.assertEqual(row['availability'],0)

    def test_real_ssd_presence_does_not_become_a_login_test(self):
        (self.root/'public'/self.ent['filename']).write_bytes(self.payload)
        row=self.check(hash_archivos=True)['entries'][0]
        self.assertEqual(row['state'],3);self.assertEqual(row['availability'],2)
        self.assertEqual(row['locations']['ssd']['integrity'],'matched')
        self.assertEqual(row['boot_test']['status'],'not-tested')

    def test_bad_bytes_and_escaping_symlink_are_not_available(self):
        arc=self.root/'public'/self.ent['filename'];arc.write_bytes(b'x'*len(self.payload))
        self.assertEqual(self.check(hash_archivos=True)['entries'][0]['state'],0)
        arc.unlink();private=self.root/'private.iso';private.write_bytes(self.payload);arc.symlink_to(private)
        row=self.check()['entries'][0]
        self.assertEqual(row['locations']['ssd']['status'],'error');self.assertEqual(row['availability'],0)

    def test_recipe_and_logged_login_have_separate_evidence(self):
        self.ent['recipe']={'entry_id':self.ent['id'],'label':'Debian exact','type':'linux','architecture':'x86_64',
                            'firmware':'uefi','kernel_url':'https://example.test/vmlinuz',
                            'initrd_url':'https://example.test/initrd','kernel_args':['ip=dhcp'],'menu_url':'','approved':False}
        catalog.guarda(self.catpath,self.cat);self.cat=catalog.carga(config=self.config);self.ent=self.cat['entries'][0]
        self.assertEqual(self.check()['entries'][0]['state'],4)
        log=self.root/'boot.log';log.write_text('Firmware: UEFI\nInstaller booted\nlogin:\n')
        checkstatus.registra(self.cat,self.cfg,self.ent['id'],log,'QEMU fixture; operator attestation','uefi',self.config)
        row=self.check()['entries'][0];self.assertEqual(row['state'],12)
        log.write_text('changed')
        self.assertEqual(self.check()['entries'][0]['state'],4)

    def test_a_different_artifact_invalidates_login_evidence(self):
        log=self.root/'boot.log';log.write_text('login:')
        checkstatus.registra(self.cat,self.cfg,self.ent['id'],log,'fixture','bios',self.config)
        self.ent['release']='2.0';self.ent['identity']=catalog.identidad(self.ent)
        self.assertEqual(self.check()['entries'][0]['boot_test']['status'],'not-tested')

    def test_incomplete_remote_inventory_preserves_last_success_as_history(self):
        good={'status':'observed','files':[{'relative':self.ent['filename'],'size':len(self.payload),
              'public_url':'https://b.example.test/'+self.ent['filename']}],'errors':[]}
        with patch.object(checkstatus,'remoto',return_value=good):old=self.check()
        guarda_json(self.root/'status.json',old)
        bad={'status':'error','files':[],'errors':[{'error':'timeout'}]}
        with patch.object(checkstatus,'remoto',return_value=bad):row=self.check()['entries'][0]
        self.assertEqual(row['availability'],0)
        self.assertEqual(row['locations']['bastion']['status'],'unknown')
        self.assertEqual(row['locations']['bastion']['last_success']['status'],'present')

    def test_duplicate_remote_paths_are_ambiguous(self):
        remote={'status':'observed','files':[{'relative':self.ent['filename'],'size':len(self.payload)}]*2,'errors':[]}
        with patch.object(checkstatus,'remoto',return_value=remote):row=self.check()['entries'][0]
        self.assertEqual(row['locations']['bastion']['status'],'ambiguous');self.assertFalse(row['availability']&8)

    def test_snapshot_expires_and_detects_policy_changes(self):
        snap=self.check();self.assertTrue(checkstatus.vigente(snap,self.cat,self.cfg))
        changed=copy.deepcopy(self.cat);changed['entries'][0]['policy']='004'
        self.assertFalse(checkstatus.vigente(snap,changed,self.cfg))
        snap['checked_at']='2001-01-01T00:00:00+00:00';self.assertFalse(checkstatus.vigente(snap,self.cat,self.cfg))

    def test_cli_plans_do_not_modify_catalogue_or_download(self):
        before=self.catpath.read_bytes()
        rsp=self.run_aux('download','--dry-run');self.assertEqual(rsp.returncode,0,rsp.stderr)
        self.assertEqual(self.catpath.read_bytes(),before);self.assertFalse(list((self.root/'cache').iterdir()))
        rsp=self.run_aux('catalog','set-policy','--resource',self.ent['id'],'--policy','004')
        self.assertEqual(rsp.returncode,0,rsp.stderr);self.assertEqual(self.catpath.read_bytes(),before)

    def test_generate_requires_a_fresh_snapshot(self):
        rsp=self.run_aux('generate','--apply')
        self.assertNotEqual(rsp.returncode,0);self.assertIn('checkstatus',rsp.stderr)

    def test_generation_uses_remote_inventory_without_scanning_bastion(self):
        remote={'status':'observed','files':[{'relative':self.ent['filename'],'size':len(self.payload),
                'public_url':'https://b.example.test/subdir/'+self.ent['filename']}],'errors':[]}
        with patch.object(checkstatus,'remoto',return_value=remote):snapshot=self.check()
        guarda_json(self.root/'status.json',snapshot)
        rsp=self.run_aux('generate','--apply')
        self.assertEqual(rsp.returncode,0,rsp.stdout+'\n'+rsp.stderr)
        dat=json.loads((self.root/'public/catalog.json').read_text())
        record=next(e for e in dat['resources'] if e.get('catalog_id')==self.ent['id'])
        self.assertEqual(record['download_urls']['bastion'],remote['files'][0]['public_url'])
        self.assertNotIn('log_path',(self.root/'public/catalog/catalog.json').read_text())
        menu=(self.root/'public/menu.ipxe').read_text()
        self.assertIn('item aux_components Components / pinned origins',menu)
        self.assertTrue((self.root/'public/documentation.html').is_file())
        self.assertTrue((self.root/'public/docs/NAVIGATION-8.md').is_file())

    def test_bastion_and_ssd_budgets_are_equal(self):
        args=argparse_fixture('deploy');pl=v8.plan(self.cat,self.cfg,args)
        self.assertEqual(pl['budget_bytes']['ssd'],pl['budget_bytes']['bastion'])

    def test_ram_and_ssd_can_hold_distinct_copies_of_one_component(self):
        from types import SimpleNamespace
        self.ent['artifact_type']='rootfs';self.ent['policy']='113'
        catalog.guarda(self.catpath,self.cat);self.cat=catalog.carga(config=self.config);self.ent=self.cat['entries'][0]
        pth=self.root/'cache'/catalog.raiz_artefacto(self.ent)/self.ent['filename']
        pth.parent.mkdir(parents=True);pth.write_bytes(self.payload)
        args=SimpleNamespace(config=self.config,mode=None)
        for dest in ('ram','ssd'):v8.despliega(self.ent,self.cfg,dest,args)
        row=self.check(hash_archivos=True)['entries'][0]
        self.assertEqual(row['availability'],3)
        self.assertNotEqual(catalog.ruta_publicada(self.ent,'ram'),catalog.ruta_publicada(self.ent,'ssd'))
        from auxlib.publication_v8 import une
        recs=[{'filename':self.ent['filename'],'path':catalog.ruta_publicada(self.ent,dest)} for dest in ('ram','ssd')]
        joined=une(recs,SimpleNamespace(catalog_file=self.catpath,status_file=self.root/'status.json'),lambda url:{})
        self.assertEqual(len(joined),1)
        guarda_json(self.root/'status.json',self.check(hash_archivos=True))
        rsp=self.run_aux('generate','--apply')
        self.assertEqual(rsp.returncode,0,rsp.stdout+'\n'+rsp.stderr)
        dat=json.loads((self.root/'public/catalog.json').read_text())
        filas=[e for e in dat['resources'] if e.get('catalog_id')==self.ent['id']]
        self.assertEqual(len(filas),1)
        self.assertEqual(set(filas[0]['download_urls']),{'source','ram','ssd'})

    def test_chroot_is_shared_by_all_three_presets(self):
        ent={**self.ent,'family':'gentoo','deploy_method':'chroot','procedure_url':'https://wiki.gentoo.org/'}
        self.assertEqual(set(catalog.presets(ent)),{'alpine','fedora','debian'})

    def test_public_catalogue_refuses_credentials(self):
        with self.assertRaises(ValueError):catalog.valida({**self.ent,'api_key':'private-fixture'})
        with self.assertRaises(ValueError):catalog.valida({**self.ent,'original_url':'https://user:password@example.test/file.iso'})

    def test_recipe_edits_do_not_move_cached_artifact_identity(self):
        before=catalog.raiz_artefacto(self.ent)
        changed={**self.ent,'recipe':{'label':'changed'}}
        self.assertEqual(catalog.raiz_artefacto(changed),before)
        self.assertNotEqual(catalog.identidad(changed),catalog.identidad(self.ent))

    def test_parallel_downloads_propagate_worker_failures(self):
        self.ent['policy']='110';catalog.guarda(self.catpath,self.cat)
        with patch.object(v8,'descarga',side_effect=ValueError('fixture checksum mismatch')) as fn:
            with self.assertRaisesRegex(ValueError,'fixture checksum mismatch'):
                v8.main(['download','--config',str(self.config),'--apply','--jobs','2'])
        fn.assert_called_once()
        with self.assertRaisesRegex(ValueError,'jobs'):
            v8.main(['download','--config',str(self.config),'--jobs','0'])

    def test_catalog_commit_leaves_unrelated_staged_files_untouched(self):
        def git(*args):
            return subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True,text=True).stdout.strip()
        git('init');git('config','user.name','Fixture');git('config','user.email','fixture@example.test')
        git('add','catalog.json','catalog.json.sha256');git('commit','-m','Initial fixture')
        (self.root/'unrelated.txt').write_text('Preserve the existing staged change.\n')
        git('add','unrelated.txt')
        self.cfg['catalog_git_repository']=str(self.root);guarda_json(self.config,self.cfg)
        nuevo=copy.deepcopy(self.cat);nuevo['updated_at']='2026-11-22T12:00:00+00:00'
        with patch.object(v8,'refresca',return_value=nuevo):
            self.assertEqual(v8.main(['catalog','refresh','--config',str(self.config),'--apply','--commit']),0)
        self.assertEqual(set(git('show','--pretty=','--name-only','HEAD').splitlines()),{'catalog.json','catalog.json.sha256'})
        self.assertEqual(git('diff','--cached','--name-only'),'unrelated.txt')


def argparse_fixture(command):
    from types import SimpleNamespace
    return SimpleNamespace(command=command,resource=None,only=None,apply=False,dry_run=True)


class RemoteInventory(unittest.TestCase):
    def test_ftps_walk_is_metadata_only_and_bounded(self):
        from unittest.mock import MagicMock
        conn=MagicMock()
        conn.mlsd.side_effect=lambda path,facts:iter([('image.iso',{'type':'file','size':'123'}),
               ('sub',{'type':'dir'})] if path=='/' else [('kernel',{'type':'file','size':'45'})])
        cfg={'ftp_host':'b.example.test','ftp_user':'test','ftp_tls':True}
        lim={'timeout_seconds':1,'max_files':10,'max_depth':4}
        with patch.object(checkstatus.ftplib,'FTP_TLS',return_value=conn):
            rows=checkstatus.inventario_ftp(cfg,'/',lim,{'ftp_password':'private-test'})
        self.assertEqual([r['relative'] for r in rows],['image.iso','sub/kernel'])
        conn.retrbinary.assert_not_called();conn.storbinary.assert_not_called()
        conn.close.assert_called_once()
        conn.prot_p.assert_called_once()


if __name__=='__main__':unittest.main()
