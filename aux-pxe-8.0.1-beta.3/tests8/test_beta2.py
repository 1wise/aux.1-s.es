# Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Verify identity, observation boundaries and isolated source adaptations."""
import copy
import datetime
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from auxlib import identity,evolve,status_view,catalog_audit,profiles,webapps


class Identity(unittest.TestCase):
    def test_validation_rejects_commands_passwords_and_privileged_accounts(self):
        for dat in ({'hostname':'a;id'},{'hostname':'-node'},{'user':'root'},{'user':'a b'},{'timezone':'../../etc'},{'password':'secret'},{'locale':'en_US.UTF-8;id'}):
            with self.subTest(dat=dat),self.assertRaises(ValueError):identity.normaliza(dat)
        self.assertEqual(identity.normaliza({'hostname':'Cari.Lab'}),{'hostname':'cari.lab'})

    def test_three_native_profiles_preserve_identity_without_passwords(self):
        dat={'hostname':'cari','locale':'es_ES.UTF-8','timezone':'Europe/Andorra','user':'enki'}
        for dis,nom in (('debian','preseed.cfg'),('fedora','installed.ks'),('alpine','apply-alpine.sh')):
            with self.subTest(dis=dis),tempfile.TemporaryDirectory() as tmp:
                ret=profiles.genera(dis,[],Path(tmp),identity=dat)
                txt=(Path(tmp)/nom).read_text()
                for val in dat.values():self.assertIn(val,txt)
                self.assertEqual(ret['identity'],dat)
                self.assertIn('tzdata',ret['packages'])

    def test_plan_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity.aplica(tmp,'debian',{'hostname':'test'},False)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_target_writes_only_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            identity.aplica(tmp,'debian',{'hostname':'cari'},True)
            self.assertEqual((Path(tmp)/'etc/hostname').read_text(),'cari\n')
            self.assertEqual((Path(tmp)/'var/lib/aux-assist/identity.json').stat().st_mode&0o777,0o600)


class Adaptation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'source';self.root.mkdir();(self.root/'README.md').write_text('Original\n')
        self.proposal={'summary':'New focus','base_manifest_sha256':evolve.manifiesto(self.root)['base_manifest_sha256'],'files':[{'path':'README.md','base_sha256':evolve.sha(b'Original\n'),'content':'Adapted\n'}],'validation_notes':['Not run']}

    def test_diff_and_new_copy_preserve_source_and_exclude_private_data(self):
        (self.root/'state').mkdir();(self.root/'state/secret').write_text('private')
        (self.root/'.env').write_text('private')
        self.assertIn('+Adapted',evolve.revision(self.proposal,self.root))
        dst=evolve.aplica(self.proposal,Path(self.tmp.name)/'fork',self.root)
        self.assertEqual((self.root/'README.md').read_text(),'Original\n')
        self.assertEqual((dst/'README.md').read_text(),'Adapted\n')
        self.assertFalse((dst/'.env').exists());self.assertFalse((dst/'state').exists())
        self.assertEqual(json.loads((dst/'aux-adaptation.json').read_text())['validation_status'],'not-run')

    def test_changed_source_refuses_old_proposal(self):
        (self.root/'README.md').write_text('Changed\n')
        with self.assertRaises(ValueError):evolve.valida(self.proposal,self.root)

    def test_private_paths_and_symlink_escapes_are_rejected(self):
        for nom in ('../out','/etc/passwd','state/token','fast-boot.json','auxlib/.env'):
            with self.subTest(nom=nom),self.assertRaises(ValueError):evolve.ruta(nom,self.root)
        (self.root/'auxlib').symlink_to(Path(self.tmp.name),target_is_directory=True)
        with self.assertRaises(ValueError):evolve.ruta('auxlib/escape.py',self.root)

    def test_source_alias_cannot_be_destination(self):
        alias=Path(self.tmp.name)/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):evolve.aplica(self.proposal,alias/'fork',self.root)


class Observations(unittest.TestCase):
    def test_bit_map_is_twenty_four_ordered_unique_bits(self):
        self.assertEqual([e['bit'] for e in status_view.BITS],list(range(23,-1,-1)))
        self.assertEqual(sum(e['readonly'] for e in status_view.BITS),8)

    def test_stale_http_cannot_set_origin_or_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=8)).isoformat()
            ent={'id':'x','original_url':'https://example.test/file.iso','policy':'004'}
            (root/'catalog.audit.json').write_text(json.dumps({'entries':[{'id':'x','original_url':ent['original_url'],'checked_at':old,'verified':True,'status':'reachable'}]}))
            dat=status_view.datos([ent],root/'catalog.json')['entries']['x']
            self.assertFalse(int(dat['word24'],16)&(1<<18));self.assertFalse(int(dat['word24'],16)&(1<<15))

    def test_http_reachability_never_becomes_boot_or_integrity_proof(self):
        class Response(io.BytesIO):
            status=200;url='https://example.test/file.iso';headers={'Content-Length':'12','Content-Type':'application/octet-stream'}
        class Client:
            def open(self,*args,**kwargs):return Response(b'')
        with patch.object(catalog_audit,'publica',side_effect=lambda u:u):
            row=catalog_audit.comprueba({'id':'x','original_url':Response.url,'size_bytes':12},cliente=Client())
            self.assertTrue(row['verified']);self.assertEqual(row['boot_test'],'not-tested');self.assertEqual(row['integrity'],'not-checked')
            row=catalog_audit.comprueba({'id':'x','original_url':Response.url,'size_bytes':13},cliente=Client())
            self.assertFalse(row['verified']);self.assertEqual(row['status'],'metadata-mismatch')

    def test_web_keeps_canonical_identity_and_own_recipe_metadata(self):
        dat=webapps.modelo();ent=next(e for e in dat['entries'] if e['id']=='aux-debian-netboot-amd64')
        self.assertEqual(len(ent['identity']),64);self.assertEqual(ent['recipe_owner'],'AUX')
        self.assertEqual(len(dat['status']['bits']),24)


if __name__=='__main__':unittest.main()
