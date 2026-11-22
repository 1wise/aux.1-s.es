# Timestamp: 2026-11-22 | Version: 8.0.0-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Exercise full preservation, zero-copy input and actual remote verification code."""
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from auxlib import settings as cfg, release as rel
from auxlib import mirror_inventory as inv, mirror_transport as net
from auxlib.common import DIR_APP


class MirrorRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root/'public'; self.src.mkdir()
        self.cache = self.root/'cache'; self.cache.mkdir()
        self.ram = self.root/'ram'; self.ram.mkdir()
        self.remote = self.root/'remote'; self.remote.mkdir()
        self.config = self.root/'config.json'
        self.sec = self.root/'private/credentials.json'
        self.dat = json.loads((DIR_APP/'fast-boot.json').read_text())
        self.dat.update(output=str(self.src),cache=str(self.cache),ram_dir=str(self.ram),catalog_file=str(DIR_APP/'catalog.json'))
        self.dat['mirror'].update(state_root=str(self.root/'work'),release_id='test',minimum_isos=0,
            ssh_host='host.example',ssh_user='user',remote_root=str(self.remote))
        self.config.write_text(json.dumps(self.dat))

    def ctx(self): return rel.contexto(self.config)

    def iso(self,nom='Fedora-Server-netinst-x86_64-45-1.4.iso'):
        arc = self.cache/nom
        arc.write_bytes(b'\0'*32769+b'CD001'+b'\0'*2048)
        return arc

    def verify_actual(self,dat,items,sec):
        req = {'root':str(self.remote),'files':items}
        result = subprocess.run([sys.executable,'-c',net.VERIFICA],input=json.dumps(req),
                                text=True,capture_output=True,check=True)
        return json.loads(result.stdout)

    def send_local(self,dat,items,vista,sec):
        inv.valida_vista(items,vista)
        for ent in items:
            dst = self.remote/ent['relative']; dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(Path(vista)/ent['relative'],dst)

    def test_inventory_covers_old_unlisted_cache_iso_and_nested_tree_once(self):
        iso = self.iso(); (self.src/iso.name).symlink_to(iso)
        older = self.iso('old-unlisted.iso')
        tree = self.ram/'boot/live'; tree.mkdir(parents=True)
        (tree/'filesystem.squashfs').write_bytes(b'contents')
        (self.src/'boot').symlink_to(tree.parent,target_is_directory=True)
        data = inv.inventario(self.src,self.cache,self.ram)
        self.assertEqual(data['iso_count'],2)
        self.assertEqual({e['relative'] for e in data['files']},{iso.name,older.name,'boot/live/filesystem.squashfs'})

    def test_93_cache_images_are_not_trimmed_to_preset_or_budget(self):
        for idx in range(93): self.iso(f'resource-{idx}.iso')
        self.assertEqual(inv.inventario(self.src,self.cache,self.ram)['iso_count'],93)

    def test_view_uses_no_payload_copies_and_cannot_escape_manifest(self):
        iso = self.iso()
        items = inv.inventario(self.src,self.cache,self.ram)['files']
        view = self.root/'view'; inv.vista(items,view)
        self.assertTrue((view/iso.name).is_symlink())
        self.assertEqual((view/iso.name).resolve(),iso)
        inv.valida_vista(items,view)
        (view/'rogue.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError,'Vista modificada'): inv.valida_vista(items,view)

    def test_collision_or_escaping_or_broken_link_blocks_before_upload(self):
        self.iso('same.iso'); (self.src/'same.iso').write_bytes(b'different')
        with self.assertRaisesRegex(ValueError,'Colisión'): inv.inventario(self.src,self.cache,self.ram)
        (self.src/'same.iso').unlink(); (self.src/'escape').symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError,'fuera'): inv.inventario(self.src,self.cache,self.ram)
        (self.src/'escape').unlink(); (self.src/'broken.iso').symlink_to(self.root/'missing')
        with self.assertRaises(OSError): inv.inventario(self.src,self.cache,self.ram)

    def test_existing_catalog_requires_previously_published_images(self):
        (self.src/'catalog.json').write_text(json.dumps({'resources':[{'filename':'missing.iso','published':True}]}))
        with self.assertRaisesRegex(ValueError,'ausente'): inv.inventario(self.src,self.cache,self.ram)

    def test_configured_checksum_is_distinct_from_local_sha(self):
        arc = self.iso(); sums = self.root/'SHA256SUMS'
        sums.write_text('0'*64+'  '+arc.name+'\n')
        with self.assertRaisesRegex(ValueError,'Checksum'): inv.inventario(self.src,self.cache,self.ram,sums)

    def test_secrets_never_enter_inventory_and_source_defaults_remain_downloadable(self):
        (self.src/'credentials.json').write_text('private')
        (self.src/'fast-boot.json').write_text('private-config')
        (self.src/'tec').mkdir(); (self.src/'tec/tecnicos.json').write_text('private')
        (self.src/'downloads').mkdir(); (self.src/'downloads/fast-boot.json').write_text('{}')
        dat = inv.inventario(self.src,self.cache,self.ram)
        self.assertEqual([e['relative'] for e in dat['files']],['downloads/fast-boot.json'])
        self.assertEqual(len(dat['excluded_private']),3)

    def test_inventory_and_plan_do_not_write_input_or_cache(self):
        self.iso(); before = set(self.root.rglob('*'))
        self.assertEqual(rel.plan(self.ctx())['payload_copies'],0)
        self.assertEqual(before,set(self.root.rglob('*')))
        dat = rel.captura(self.ctx())
        self.assertEqual(dat['inventory']['iso_count'],1)
        self.assertFalse(dat['deployed'])
        self.assertEqual(stat.S_IMODE((self.ctx()['root']/'state.json').stat().st_mode),0o600)

    def test_custom_recipe_without_original_profile_blocks_before_transfer(self):
        (self.src/'origins').mkdir()
        (self.src/'origins/custom_test.ipxe').write_text('#!ipxe\n')
        with self.assertRaisesRegex(ValueError,'perfil original'): rel.captura(self.ctx())
        self.assertFalse((self.ctx()['root']/'state.json').exists())

    def test_expected_iso_minimum_blocks_a_truncated_server_inventory(self):
        self.iso()
        self.dat['mirror']['minimum_isos']=93
        self.config.write_text(json.dumps(self.dat))
        with self.assertRaisesRegex(ValueError,'mínimo esperado 93'):rel.captura(self.ctx())

    def test_deploy_does_not_replace_live_entry_points_before_verify(self):
        self.iso(); (self.src/'index.html').write_text('source page')
        (self.remote/'index.html').write_text('existing page')
        ctx=self.ctx();rel.captura(ctx)
        with patch.object(net,'envia',side_effect=self.send_local):rel.despliega(ctx,self.sec)
        self.assertEqual((self.remote/'index.html').read_text(),'existing page')

    def test_prepared_tree_with_older_image_digest_is_rejected(self):
        arc=self.iso();tree=self.src/arc.stem;tree.mkdir()
        est=self.cache/'tree-state';est.mkdir()
        (est/'test.json').write_text(json.dumps({'tree':str(tree),'source':str(arc),'sha256':'0'*64}))
        with self.assertRaisesRegex(ValueError,'otra imagen'):inv.inventario(self.src,self.cache,self.ram)

    def test_generate_and_publish_require_previous_verified_phases(self):
        self.iso(); ctx = self.ctx(); rel.captura(ctx)
        with self.assertRaisesRegex(ValueError,'Verificar'): rel.genera(ctx)
        with self.assertRaisesRegex(ValueError,'Falta web'): rel.publica(ctx,self.sec)
        with self.assertRaisesRegex(ValueError,'deploy'): rel.verifica(ctx,self.sec)

    def test_remote_program_checks_hash_when_size_matches_and_rejects_symlink(self):
        arc = self.iso(); ent = inv.elemento(arc,arc.name)
        shutil.copyfile(arc,self.remote/arc.name)
        self.assertEqual(self.verify_actual(None,[ent],{})['checked'],1)
        (self.remote/arc.name).write_bytes(b'x'*ent['size'])
        self.assertEqual(self.verify_actual(None,[ent],{})['failures'][0]['error'],'sha256')
        (self.remote/arc.name).unlink(); (self.remote/arc.name).symlink_to(arc)
        self.assertTrue(self.verify_actual(None,[ent],{})['failures'])

    def test_verification_failure_is_persisted_and_blocks_generate(self):
        self.iso(); ctx = self.ctx(); rel.captura(ctx)
        with patch.object(net,'envia',side_effect=self.send_local): rel.despliega(ctx,self.sec)
        (self.remote/next(iter(self.cache.iterdir())).name).unlink()
        with patch.object(net,'verifica',side_effect=self.verify_actual):
            with self.assertRaisesRegex(ValueError,'no coincide'): rel.verifica(ctx,self.sec)
        self.assertFalse(rel.estado(ctx)['media_verified'])
        with self.assertRaises(ValueError): rel.genera(ctx)

    def test_changed_input_invalidates_transfer_and_generation(self):
        arc = self.iso(); ctx = self.ctx(); rel.captura(ctx)
        arc.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'INPUT cambió'): rel.despliega(ctx,self.sec)

    def test_catalog_guard_keeps_all_previous_local_and_origin_resources(self):
        old = {'resources':[{'filename':'one.iso','published':True}],
               'origin_resources':[{'url':'https://origin.example/two.iso'}]}
        with self.assertRaisesRegex(ValueError,'perdería'): inv.compara_catalogos(old,{'resources':[]})
        inv.compara_catalogos(old,dict(old,extra='additive'))

    def test_rsync_is_resumable_physical_and_does_not_delete_or_disable_ssh_checks(self):
        cmd = net.comando_rsync(self.dat,self.root/'view')
        self.assertIn('-rtpL',cmd); self.assertIn('--checksum',cmd)
        self.assertIn('--partial',cmd)
        self.assertFalse(any(c.startswith(('--delete','--remove-source','--inplace')) for c in cmd))
        self.assertIn('StrictHostKeyChecking=yes',' '.join(cmd))
        self.assertIn('BatchMode=yes',' '.join(cmd))

    def test_ftps_resumes_partial_and_verifies_same_size_corruption(self):
        arc=self.iso();ent=inv.elemento(arc,arc.name);view=self.root/'view';inv.vista([ent],view)
        dat=dict(self.dat,mirror={'transport':'ftps'},ftp_root='/site')
        tmp='.aux-upload-'+ent['sha256']+'.part'
        store={tmp:arc.read_bytes()[:120]}
        class Conn:
            def cwd(self,*args):pass
            def voidcmd(self,*args):pass
            def close(self):pass
            def size(self,name):return len(store[name]) if name in store else None
            def storbinary(self,cmd,src,blocksize,rest):
                self.offset=rest
                store[cmd[5:]]=store.get(cmd[5:],b'')[:rest or 0]+src.read()
            def rename(self,src,dst):store[dst]=store.pop(src)
            def retrbinary(self,cmd,callback,blocksize):callback(store[cmd[5:]])
        conn=Conn()
        with patch.object(net,'conecta_ftp',return_value=conn):
            net.envia(dat,[ent],view,{'ftp_password':'test'})
            self.assertEqual(conn.offset,120)
            self.assertEqual(net.verifica(dat,[ent],{})['checked'],1)
            store[arc.name]=b'x'*ent['size']
            self.assertEqual(net.verifica(dat,[ent],{})['failures'][0]['error'],'sha256')

    def test_full_workflow_actual_generation_keeps_master_media_and_all_entries(self):
        arc = self.iso(); (self.src/arc.name).symlink_to(arc)
        # Synthetic payloads need their own pinned catalogue, not a real distribution's size/hash.
        from auxlib.catalog_v8 import carga,guarda
        cat=carga(self.dat['catalog_file'])
        for ent in cat['entries']:
            if ent['filename']==arc.name:
                ent.update(size_bytes=arc.stat().st_size,sha256=inv.suma(arc))
        pth_cat=self.root/'catalog.json';guarda(pth_cat,cat)
        self.dat['catalog_file']=str(pth_cat);self.config.write_text(json.dumps(self.dat))
        tree = self.src/arc.stem/'images/pxeboot'; tree.mkdir(parents=True)
        (tree/'vmlinuz').write_bytes(b'kernel'); (tree/'initrd.img').write_bytes(b'initrd')
        before = {p:inv.sello(p) for p in [arc,tree/'vmlinuz',tree/'initrd.img']}
        ctx = self.ctx(); data = rel.captura(ctx)
        with patch.object(net,'envia',side_effect=self.send_local),patch.object(net,'verifica',side_effect=self.verify_actual):
            rel.despliega(ctx,self.sec); rel.verifica(ctx,self.sec)
            vigente=rel.estado(ctx);vencido=dict(vigente,media_verified_at='2001-01-01T00:00:00+00:00')
            rel.guarda(ctx,vencido)
            with self.assertRaisesRegex(ValueError,'caducada'):rel.genera(ctx)
            rel.guarda(ctx,vigente)
            data = rel.genera(ctx)
            snapshot=json.loads((ctx['root']/'status.json').read_text())
            self.assertEqual(snapshot['remote_inventory']['via'],'verified-release')
            self.assertEqual(before,{p:inv.sello(p) for p in before})
            self.assertFalse(list((ctx['root']/'web').glob('*.iso')))
            self.assertTrue((ctx['root']/'input-view'/arc.name).is_symlink())
            cat = json.loads((ctx['root']/'web/catalog.json').read_text())
            self.assertIn(arc.name,[e['filename'] for e in cat['resources']])
            rec=next(e for e in cat['resources'] if e['filename']==arc.name)
            tsv=(ctx['root']/'web/contents'/rec['id']/'files.tsv').read_text()
            self.assertIn('vmlinuz',tsv)
            self.assertIn('initrd.img',tsv)
            self.assertTrue(cat['origin_resources'])
            self.assertEqual(cat['default_server'],'bastion')
            self.assertIn('Bastion · France</a>',(ctx['root']/'web/catalogue.html').read_text())
            self.assertIn('https://tec.1-s.es/',(ctx['root']/'web/index.html').read_text())
            self.assertNotIn('t.1-s.es',(ctx['root']/'web/.htaccess').read_text())
            self.assertFalse((ctx['root']/'web/index.php').exists())
            rel.publica(ctx,self.sec); data = rel.verifica(ctx,self.sec)
        self.assertTrue(data['final_verified'])
        self.assertEqual(data['verification']['checked'],len(rel.finales(data)))
        self.assertFalse((self.remote/arc.name).is_symlink())


class Settings(unittest.TestCase):
    def test_default_edits_keep_signed_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'XDG_CONFIG_HOME':tmp}):
            antes=(DIR_APP/'fast-boot.json').read_bytes()
            cfg.establece('mirror.ssh_host','mirror.example')
            self.assertEqual((DIR_APP/'fast-boot.json').read_bytes(),antes)
            self.assertEqual(cfg.ruta_config(),Path(tmp)/'aux/config.json')
            self.assertTrue(Path(cfg.lee_config()['catalog_file']).is_absolute())

    def test_field_validation_cannot_turn_host_into_a_command_or_root_into_slash(self):
        for nom,txt in [('mirror.ssh_host','-oProxyCommand=bad'),('mirror.ssh_user','x;bad'),
                        ('mirror.remote_root','/'),('ftp_root','/../'),('ai.openai.model','x y')]:
            with self.subTest(nom=nom),self.assertRaises(ValueError): cfg.convierte(nom,txt)

    def test_private_credentials_owner_permissions_and_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); config = root/'settings.json'; sec = root/'private/credentials.json'
            dat = json.loads((DIR_APP/'fast-boot.json').read_text()); dat['output']=str(root/'public')
            config.write_text(json.dumps(dat))
            cfg.guarda_secreto('openai_api_key','test-key',sec,config)
            self.assertEqual(stat.S_IMODE(sec.stat().st_mode),0o600)
            self.assertEqual(stat.S_IMODE(sec.parent.stat().st_mode),0o700)
            self.assertNotIn('test-key',json.dumps(cfg.diagnostico(config,sec)))
            sec.chmod(0o644)
            with self.assertRaises(ValueError): cfg.lee_secretos(sec,config)
            with self.assertRaises(ValueError): cfg.guarda_secreto('ftp_password','test',root/'public/credentials.json',config)


if __name__ == '__main__': unittest.main()
