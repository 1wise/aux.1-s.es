# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Verify the public origin catalogue and reviewed recipe workshop end to end."""
import copy
import json
import subprocess
import shutil
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from build import motor
from auxlib import origin_catalog, remote_menu, recipe_workshop as taller
from auxlib import catalog_assist as api, catalog_assist_ui as ui, catalog_profile as perfiles
from auxlib import webapps
from test_catalog_assist import entrada, receta, propuesta, LIM, CAL


class Respuesta:
    status=200
    def __init__(self,peso):self.headers={'Content-Length':str(peso)}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,*args):raise AssertionError('Recipe validation must not read payload bodies')


def fixture(raiz):
    pub=raiz/'public';ram=raiz/'ram';cache=raiz/'cache'
    for pth in (pub,ram,cache):pth.mkdir()
    media=ram/'one';(media/'live').mkdir(parents=True)
    for nom in ('vmlinuz','initrd.img','filesystem.squashfs'):(media/'live'/nom).write_bytes(b'asset')
    (pub/'one').symlink_to(media)
    (raiz/'fast-boot.json').write_text(json.dumps({'output':str(pub),'ram_dir':str(ram),
        'cache':str(cache),'pxe_url':'http://pxe.example.org','ram_budget_gib':28,'ssd_budget_gib':100,
        'ai':{'not_for_context':'synthetic-secret'}}))
    selection=raiz/'selection.json';selection.write_text(json.dumps({'entries':[entrada(modo='light')]}))
    data={'resources':[{'id':'deployed','url':'https://example.org/one.iso','published':True,
        'tree':'one','format':'ISO','pxe_ready':False,'pxe_reason':'Recipe missing'}]}
    (pub/'catalog.json').write_text(json.dumps(data))
    return pub,selection


class CatalogoOrigen(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'Node is optional for portal development tests')
    def test_javascript_keeps_origin_links_visible_after_filtering(self):
        subprocess.run(['node',str(Path(__file__).with_name('test_origin_portal.cjs'))],check=True,capture_output=True,text=True)

    def test_origin_adapter_deduplicates_local_urls_without_claiming_local_bytes(self):
        ent=dict(entrada('tiny'),family='tinyos')
        menu=dict(entrada('provider'),original_url='https://boot.netboot.xyz/debian.ipxe',remote_only=True)
        sal=origin_catalog.recursos_origen([ent,ent,menu,entrada('local')],[{'url':'https://example.org/local.iso'}])
        self.assertEqual(len(sal),2)
        for rec in sal:
            self.assertFalse(rec['published']);self.assertFalse(rec['pxe_ready'])
            self.assertIsNone(rec['size']);self.assertIsNone(rec['sha256'])
            self.assertEqual(rec['download_urls'],{'source':rec['url']})
        self.assertTrue(sal[1]['origin_launcher']);self.assertIsNone(sal[0]['origin_launcher'])

    def test_launchers_never_chain_an_arbitrary_image_or_an_untrusted_script(self):
        for url in ('https://example.org/rescue.iso','https://elsewhere.example/script.ipxe',
                    'https://boot.netboot.xyz/debian.ipxe?cmd=other'):
            self.assertIsNone(remote_menu.lanzador_origen(dict(entrada(),original_url=url,remote_only=True)))
        text=remote_menu.lanzador_origen(dict(entrada(),original_url='https://boot.netboot.xyz/debian.ipxe',remote_only=True))
        self.assertLess(text.index('/boot.cfg'),text.index('set menu debian'))
        self.assertIn('chain --autofree https://boot.netboot.xyz/debian.ipxe',text)

    def test_origin_rows_and_commands_are_in_static_visual_and_text_pages(self):
        eng=motor();eng.carga_recursos()
        ents=[dict(entrada('tiny'),family='tinyos'),
              dict(entrada('provider'),family='debian',original_url='https://boot.netboot.xyz/debian.ipxe',remote_only=True)]
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);cfg=SimpleNamespace(output=raiz/'pub',cache=raiz/'cache',
                base_url='https://aux.example.org',pxe_url='http://pxe.example.org',download_url='https://b.example.org',
                tec={},tec_enabled=False)
            cfg.output.mkdir();cfg.cache.mkdir()
            original=webapps.modelo
            def modelo(*args,**kwargs):
                dat=original(*args,**kwargs);dat['entries']=ents;return dat
            with patch('auxlib.webapps.modelo',side_effect=modelo):dat=eng.gen_pages([],cfg,'source')
            self.assertEqual(len(dat['resources']),0);self.assertEqual(len(dat['origin_resources']),2)
            for filename in ('index.html','index.php','cli.html','cli-all.html','index-pxe.html'):
                text=(cfg.output/filename).read_text()
                for ent in ents:self.assertIn(ent['original_url'],text,filename)
                self.assertIn('Tinyos',text)
            for rec in dat['origin_resources']:
                self.assertTrue((cfg.output/'files'/(rec['id']+'.html')).is_file())
            self.assertEqual(len(list((cfg.output/'origins').glob('*.ipxe'))),1)


class TallerRecetas(unittest.TestCase):
    def test_approved_recipe_is_published_with_a_registry_and_individual_launcher(self):
        eng=motor();eng.carga_recursos()
        rec={'recipe':receta(),'approved':True,'http':'passed','hardware_boot':'not-tested'}
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Replica',LIM,recetas=[rec])
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);pth=raiz/'profile.json';pth.write_text(json.dumps(perfil))
            cfg=SimpleNamespace(output=raiz/'pub',cache=raiz/'cache',catalog_profile=pth,
                base_url='https://aux.example.org',pxe_url='http://pxe.example.org',
                download_url='https://b.example.org',tec={},tec_enabled=False)
            cfg.output.mkdir();cfg.cache.mkdir()
            dat=eng.gen_pages([],cfg,'source')
            registro=json.loads((cfg.output/'recipes.json').read_text())
            self.assertEqual(len(registro['entries']),1)
            launcher=registro['entries'][0]['launcher']
            self.assertIn('kernel https://example.org/vmlinuz',(cfg.output/launcher).read_text())
            origen=next(r for r in dat['origin_resources'] if r['url']=='https://example.org/one.iso')
            self.assertEqual(origen['origin_launcher'],launcher);self.assertTrue(origen['reviewed_recipe'])
            self.assertIn(registro['entries'][0]['id'],(cfg.output/'recipes.html').read_text())

    def test_recipe_registry_has_revision_ids_and_excludes_unapproved_candidates(self):
        recs=[{'recipe':receta(nom),'approved':nom=='one','http':'passed','hardware_boot':'not-tested'} for nom in ('one','two')]
        perfil=perfiles.perfil_desde_seleccion([entrada('one'),entrada('two')],'Replica',LIM,recetas=recs)
        reg=perfiles.registro_recetas(perfil)
        self.assertEqual(len(reg['entries']),1)
        ent=reg['entries'][0]
        self.assertEqual(len(ent['id']),64)
        self.assertEqual(ent['review']['hardware_boot'],'not-tested')
        self.assertIn('kernel https://example.org/vmlinuz',perfiles.lanzador_receta(perfil,'one'))
        self.assertIsNone(perfiles.lanzador_receta(perfil,'two'))
        nuevo=copy.deepcopy(perfil);nuevo['recipes'][0]['recipe']['kernel_args'].append('quiet')
        self.assertNotEqual(ent['id'],perfiles.registro_recetas(nuevo)['entries'][0]['id'])

    def test_inventory_contains_public_paths_and_keeps_storage_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp);pub,selection=fixture(raiz)
            external=raiz/'private';external.write_text('private')
            (raiz/'ram/one/live/kernel-link').symlink_to(external)
            with patch.object(taller,'DIR_APP',raiz),patch.object(perfiles,'carga_perfil',return_value=None):
                plan=taller.carga_taller(pub/'catalog.json',selection)
            self.assertEqual(plan['entries'][0]['selection_mode'],'light')
            text=json.dumps(plan['context'])
            self.assertNotIn(str(raiz),text);self.assertNotIn('synthetic-secret',text)
            self.assertNotIn('kernel-link',text)
            self.assertIn('http://pxe.example.org/one/live/vmlinuz',plan['assets'])

    def test_local_head_uses_only_the_matching_entry_and_never_reads_a_body(self):
        plan={'bases':['http://pxe.example.org'],'assets':{'http://pxe.example.org/one/linux':{'entry_id':'one','size':5}},'directories':{}}
        rec=dict(receta(),kernel_url='http://pxe.example.org/one/linux')
        opener=Mock();opener.open.return_value=Respuesta(5)
        self.assertTrue(taller.comprueba_local(plan,rec,rec['kernel_url'],opener))
        self.assertEqual(opener.open.call_args.args[0].get_method(),'HEAD')
        for url in ('http://pxe.example.org/secret','http://pxe.example.org/one/linux?other=1'):
            with self.assertRaises(ValueError):taller.comprueba_local(plan,rec,url,opener)
        with self.assertRaises(ValueError):taller.comprueba_local(plan,dict(rec,entry_id='other'),rec['kernel_url'],opener)
        self.assertFalse(taller.comprueba_local(plan,rec,'http://elsewhere.example/one/linux',opener))
        opener.open.return_value=Respuesta(9)
        with self.assertRaises(ValueError):taller.comprueba_local(plan,rec,rec['kernel_url'],opener)

    def test_generated_live_ipv4_is_bounded_and_private_metadata_is_not_trusted(self):
        for ip,admitida in [('144.217.182.189',True),('127.0.7.1',False),('224.0.0.1',False)]:
            with self.subTest(ip=ip),tempfile.TemporaryDirectory() as tmp:
                raiz=Path(tmp);pub,selection=fixture(raiz)
                pth=pub/'catalog.json';dat=json.loads(pth.read_text());dat['live_url']='http://'+ip
                pth.write_text(json.dumps(dat))
                with patch.object(taller,'DIR_APP',raiz),patch.object(perfiles,'carga_perfil',return_value=None):
                    plan=taller.carga_taller(pth,selection)
                self.assertEqual('http://'+ip in plan['bases'],admitida)
                self.assertEqual(plan['context']['live_url'],'http://'+ip if admitida else None)

    def test_generic_assistance_cannot_approve_uninventoried_http(self):
        sol=propuesta();sol['recipes']=[dict(receta(),kernel_url='http://127.0.0.1/linux')]
        with tempfile.TemporaryDirectory() as tmp:
            _,_,recs,_=api.verifica_propuesta(sol,[entrada()],CAL,Path(tmp))
        self.assertEqual(recs[0]['http'],'failed');self.assertFalse(recs[0]['approved'])

    def test_recipe_only_mode_rejects_storage_changes_and_new_sources(self):
        sol=propuesta();sol['recipes']=[receta()]
        self.assertEqual(taller.valida_solo_recetas(sol,[entrada()])['recipes'],[receta()])
        sol['selection'][0]['mode']='light'
        with self.assertRaises(ValueError):taller.valida_solo_recetas(sol,[entrada()])
        sol=propuesta();sol['sources']=[{'unexpected':'source'}]
        with self.assertRaises(ValueError):taller.valida_solo_recetas(sol,[entrada()])

    def test_recipe_architecture_must_match_the_selected_media(self):
        sol=propuesta();sol['recipes']=[dict(receta(),architecture='arm64')]
        with self.assertRaisesRegex(ValueError,'arquitectura'):api.valida_propuesta(sol,[entrada()])

    def test_kernel_argument_dependencies_are_checked_too(self):
        sol=propuesta();sol['recipes']=[dict(receta(),kernel_args=['fetch=https://example.org/root.squashfs'])]
        urls=[]
        with tempfile.TemporaryDirectory() as tmp:
            _,_,recs,_=api.verifica_propuesta(sol,[entrada()],CAL,Path(tmp),
                comprobar=lambda url,*args:urls.append(url),valida_red=lambda *args:None)
        self.assertEqual(len(urls),3);self.assertIn('https://example.org/root.squashfs',urls)
        self.assertFalse(recs[0]['approved'])

    def test_merging_recipe_proposals_keeps_other_reviewed_entries(self):
        old={'recipe':receta(),'approved':True,'http':'passed','hardware_boot':'not-tested'}
        new={'recipe':receta('two'),'approved':False,'http':'failed','hardware_boot':'not-tested'}
        merged=taller.combina_recetas([old],[new])
        self.assertEqual(len(merged),2);self.assertTrue(merged[0]['approved'])
        self.assertEqual(old['recipe']['entry_id'],'one')

    def test_saving_approves_only_explicitly_checked_recipes(self):
        recs=[{'recipe':receta(nom),'approved':False,'http':'passed','hardware_boot':'not-tested'} for nom in ('one','two')]
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ui,'campo',side_effect=['Replica','EXPORTAR',str(Path(tmp)/'profile'),'']), \
                 patch.object(ui,'elige',side_effect=[False,'export']),patch.object(ui,'marca',return_value=['one']):
                result=ui.guarda_plan([entrada('one'),entrada('two')],LIM,recs,[])
            perfil=result['profile']
            self.assertEqual([r['approved'] for r in perfil['recipes']],[True,False])
            menu='\n'.join(perfiles.menu_recetas(perfil))
            self.assertIn(':custom_one',menu);self.assertNotIn(':custom_two',menu)


if __name__=='__main__':unittest.main()
