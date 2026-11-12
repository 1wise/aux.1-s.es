# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Exercise provider schemas, portable profiles and reviewed iPXE recipes without paid calls."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from auxlib import catalog_assist as api,catalog_profile as perfiles,catalog_selection as seleccion
from auxlib import catalog, catalog_downloads, catalog_assist_ui,console_ui,webapps
from auxlib.common import DIR_APP


def entrada(nom='one',modo='heavy',peso=1024):
    return {'id':nom,'name':nom,'family':'debian','release':'1.0','architecture':'x86_64','kind':'image',
            'original_url':'https://example.org/'+nom+'.iso','download_class':'heavy',
            'selection_mode':modo,'size_bytes':peso,'remote_only':False}


def receta(nom='one'):
    return {'entry_id':nom,'label':'Custom Linux','type':'linux','architecture':'x86_64','firmware':'uefi',
            'kernel_url':'https://example.org/vmlinuz','initrd_url':'https://example.org/initrd',
            'kernel_args':['ip=dhcp','console=tty0'],'menu_url':''}


def fuente():
    return {'id':'rescue','label':'Rescue','family':'rescue','architecture':'x86_64','kind':'live',
            'source_url':'https://example.org/releases/','filename_glob':'rescue-*-x86_64.iso',
            'artifact_url':'','checksum_url':'','reference_url':'https://example.org/docs/',
            'reason':'Requested rescue tool','format':'artifact-html','mode':'heavy','channel':'stable'}


def propuesta():
    return {'summary':'Catalogue proposal','selection':[{'entry_id':'one','mode':'heavy','reason':'Requested'}],
            'sources':[],'recipes':[]}


LIM={'ram_gib':28,'ssd_gib':100,'reserve_percent':10}
CAL={'ram':int(25.2*1024**3),'ssd':100*1024**3}


class CatalogoAsistido(unittest.TestCase):
    def test_openai_uses_responses_strict_json_without_server_side_storage(self):
        url,dat=api.peticion('openai','test-model',{'request':'rescue'})
        self.assertEqual(url,'https://api.openai.com/v1/responses')
        self.assertFalse(dat['store']);self.assertEqual(dat['text']['format']['type'],'json_schema')
        self.assertTrue(dat['text']['format']['strict']);self.assertNotIn('tools',dat)
        self.assertNotIn('api_key',json.dumps(dat))

    def test_gemini_uses_generate_content_json_schema_and_model_is_explicit(self):
        url,dat=api.peticion('gemini','test-gemini',{'request':'rescue'})
        self.assertIn('/models/test-gemini:generateContent',url)
        self.assertEqual(dat['generationConfig']['responseMimeType'],'application/json')
        self.assertEqual(dat['generationConfig']['responseJsonSchema'],api.ESQUEMA)
        for model in ('','../model','sk-not-a-model'):
            with self.assertRaises(ValueError):api.peticion('openai',model,{})

    def test_fake_openai_response_is_parsed_without_any_network_request(self):
        cli=Mock();cli.consulta_raw.return_value={'status':'completed'};cli.extrae.return_value=json.dumps(propuesta())
        dat=api.consulta_propuesta('openai','test-model','test-key-synthetic',{},cliente=cli)
        self.assertEqual(dat,propuesta());cli.consulta_raw.assert_called_once()
        self.assertNotIn('test-key-synthetic',json.dumps(cli.consulta_raw.call_args.args[3]))

    def test_incomplete_and_invalid_responses_do_not_produce_a_plan(self):
        cli=Mock();cli.consulta_raw.return_value={'status':'incomplete'}
        with self.assertRaises(ValueError):api.consulta_propuesta('openai','test-model','test-key-synthetic',{},cliente=cli)
        cli.consulta_raw.return_value={'candidates':[{'finishReason':'MAX_TOKENS'}]}
        with self.assertRaises(ValueError):api.consulta_propuesta('gemini','test-model','test-key-synthetic',{},cliente=cli)
        cli.consulta_raw.return_value={'status':'completed'};cli.extrae.return_value='not json'
        with self.assertRaises(ValueError):api.consulta_propuesta('openai','test-model','test-key-synthetic',{},cliente=cli)

    def test_unknown_ids_commands_and_approval_flags_are_rejected(self):
        for mutate in (lambda p:p.update(command='arbitrary shell'),
                       lambda p:p['selection'][0].update(entry_id='invented'),
                       lambda p:p['selection'][0].update(mode='execute')):
            p=propuesta();mutate(p)
            with self.assertRaises(ValueError):api.valida_propuesta(p,[entrada()])
        p=propuesta();p['recipes']=[dict(receta(),approved=True)]
        with self.assertRaises(ValueError):api.valida_propuesta(p,[entrada()])

    def test_new_sources_use_a_bounded_glob_not_executable_regex(self):
        src=fuente();comp=api.compila_fuente(src)
        self.assertEqual(comp['source']['allowed_hosts'],['example.org'])
        self.assertIsNotNone(__import__('re').fullmatch(comp['slot']['filename_pattern'],'rescue-2.1-x86_64.iso'))
        for glob in ('(a+)+.iso','rescue-*-*.iso','../../secret','rescue-*.iso;reboot'):
            with self.assertRaises(ValueError):api.compila_fuente(dict(src,filename_glob=glob))
        with self.assertRaises(ValueError):api.valida_fuente(dict(src,sha256='a'*64))

    def test_metadata_not_the_model_supplies_resolved_sizes_and_releases(self):
        p=propuesta();p['sources']=[fuente()]
        with tempfile.TemporaryDirectory() as tmp:
            ents,sources,recs,warnings=api.verifica_propuesta(p,[entrada()],CAL,Path(tmp),
                traer=lambda *args:b'<a href="rescue-2.1-x86_64.iso">image</a>',
                comprobar=lambda *args:{'http':'passed','size_bytes':2048},valida_red=lambda *args:None)
        nuevo=next(e for e in ents if e['id']=='rescue')
        self.assertEqual((nuevo['release'],nuevo['size_bytes']),('2.1',2048))
        self.assertEqual(nuevo['selection_mode'],'heavy');self.assertEqual(len(sources),1)
        self.assertEqual(warnings,[])

    def test_unknown_or_over_budget_sizes_remain_origin(self):
        p=propuesta();p['selection'][0]['mode']='light'
        with tempfile.TemporaryDirectory() as tmp:
            ents,_,_,warnings=api.verifica_propuesta(p,[entrada(peso=None)],CAL,Path(tmp))
        self.assertEqual(ents[0]['selection_mode'],'origin');self.assertTrue(warnings)
        with tempfile.TemporaryDirectory() as tmp:
            ents,_,_,warnings=api.verifica_propuesta(p,[entrada(peso=50*1024**3)],CAL,Path(tmp))
        self.assertEqual(ents[0]['selection_mode'],'origin')

    def test_failed_new_source_is_visible_as_origin_without_a_fake_download(self):
        p=propuesta();p['sources']=[fuente()]
        def fail(*args):raise OSError('source unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            ents,_,_,warnings=api.verifica_propuesta(p,[entrada()],CAL,Path(tmp),traer=fail,valida_red=lambda *args:None)
        nuevo=next(e for e in ents if e['id']=='rescue')
        self.assertTrue(nuevo['remote_only']);self.assertEqual(nuevo['selection_mode'],'origin')
        self.assertIsNone(nuevo['size_bytes']);self.assertIn('source unavailable',warnings[-1])

    def test_recipe_assets_are_checked_but_approval_never_comes_from_the_api(self):
        p=propuesta();p['recipes']=[receta()];heads=[]
        def head(*args):heads.append(args[0]);return {'http':'passed','size_bytes':100}
        with tempfile.TemporaryDirectory() as tmp:
            _,_,recs,_=api.verifica_propuesta(p,[entrada()],CAL,Path(tmp),comprobar=head,valida_red=lambda *args:None)
        self.assertEqual(heads,['https://example.org/vmlinuz','https://example.org/initrd'])
        self.assertFalse(recs[0]['approved']);self.assertEqual(recs[0]['hardware_boot'],'not-tested')
        self.assertEqual(perfiles.menu_recetas(perfiles.perfil_desde_seleccion([entrada()],'Custom',LIM,recetas=recs)),[])

    def test_recipes_cannot_include_shell_operators_or_fake_hardware_acceptance(self):
        for args in (['quiet;reboot'],['a\nchain'],['${arbitrary}'],['quiet && reboot']):
            with self.assertRaises(ValueError):perfiles.valida_receta(dict(receta(),kernel_args=args))
        rec={'recipe':receta(),'approved':True,'http':'passed','hardware_boot':'passed'}
        with self.assertRaises(ValueError):perfiles.perfil_desde_seleccion([entrada()],'Custom',LIM,recetas=[rec])

    def test_profiles_export_three_modes_and_a_separate_crawler(self):
        ents=[entrada('a','light'),entrada('b','heavy'),entrada('c','origin',None)]
        perfil=perfiles.perfil_desde_seleccion(ents,'Replica',LIM)
        with tempfile.TemporaryDirectory() as tmp:
            out=perfiles.exporta_perfil(perfil,Path(tmp)/'profile',{'sources':[]})
            self.assertEqual((out/'url.txt').read_text(),'https://example.org/a.iso\nhttps://example.org/b.iso\n')
            self.assertEqual((out/'origin-url.txt').read_text(),'https://example.org/c.iso\n')
            cfg=json.loads((out/'crawler.sources.json').read_text())
            self.assertEqual(len(cfg['download_slots']),2);self.assertEqual(len(cfg['entries']),1)
            self.assertNotIn('goto custom_recipes',(out/'menu-custom.ipxe').read_text())

    def test_profile_export_pins_multiple_versions_without_overlapping_slots(self):
        base=json.loads((DIR_APP/'config/catalog.sources.json').read_text())
        ents=[dict(entrada('old'),original_url='https://example.org/debian-13.6.0-amd64-netinst.iso'),
              dict(entrada('new'),original_url='https://example.org/debian-13.7.0-amd64-netinst.iso')]
        perfil=perfiles.perfil_desde_seleccion(ents,'Two versions',LIM)
        cfg=perfiles.config_desde_perfil(perfil,base)
        self.assertTrue(all(f['format']=='fixed' for f in cfg['download_sources']))
        for ent in ents:self.assertEqual(sum(catalog_downloads.coincide(ent['original_url'],s) for s in cfg['download_slots']),1)

    def test_sourceforge_download_suffix_uses_the_payload_name(self):
        ent=dict(entrada(),original_url='https://sourceforge.net/projects/test/files/image.iso/download')
        cfg=perfiles.config_desde_perfil(perfiles.perfil_desde_seleccion([ent],'SF',LIM),{'sources':[]})
        self.assertTrue(catalog_downloads.coincide(ent['original_url'],cfg['download_slots'][0]))

    def test_local_filename_collisions_and_nested_credentials_are_rejected(self):
        ents=[entrada('one'),dict(entrada('two'),original_url='https://elsewhere.example/one.iso')]
        with self.assertRaises(ValueError):perfiles.perfil_desde_seleccion(ents,'Collision',LIM)
        ent=entrada();ent['verification']={'api_key':'synthetic-key'}
        with self.assertRaises(ValueError):perfiles.perfil_desde_seleccion([ent],'Bad secret',LIM)

    def test_replica_defaults_budgets_and_custom_choices_survive_reopening(self):
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Replica',dict(LIM,ram_gib=8,ssd_gib=20),True)
        with tempfile.TemporaryDirectory() as tmp,patch.object(perfiles,'RUTA_PERFIL',Path(tmp)/'profile.json'):
            perfiles.activa_perfil(perfil)
            self.assertEqual(seleccion.limites_catalogo()['ssd'],20*1024**3)
            self.assertEqual(set(seleccion.preset_catalogo([entrada()],'default',CAL)),{'one'})
            self.assertEqual(set(seleccion.preset_catalogo([entrada()],'custom',CAL)),{'one'})
            perfiles.activa_perfil(perfil)
            self.assertTrue((Path(tmp)/'profile.json.before-profile').is_file())

    def test_saved_custom_does_not_replace_aux_default_unless_requested(self):
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Replica',LIM,False)
        with tempfile.TemporaryDirectory() as tmp,patch.object(perfiles,'RUTA_PERFIL',Path(tmp)/'profile.json'):
            perfiles.activa_perfil(perfil)
            self.assertEqual(seleccion.preset_catalogo([entrada()],'default',CAL),{})
            self.assertEqual(set(seleccion.preset_catalogo([entrada()],'custom',CAL)),{'one'})

    def test_reviewed_recipe_is_emitted_in_both_standalone_and_generated_menus(self):
        rec={'recipe':receta(),'approved':True,'http':'passed','hardware_boot':'not-tested'}
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Boot profile',LIM,recetas=[rec])
        with tempfile.TemporaryDirectory() as tmp:
            out=perfiles.exporta_perfil(perfil,Path(tmp)/'profile',{'sources':[]})
            standalone=(out/'menu-custom.ipxe').read_text()
            self.assertIn(':start',standalone);self.assertIn('initrd --name aux-profile-initrd',standalone)
            from build import motor
            eng=motor();cfg=SimpleNamespace(pxe_url='http://pxe.example.org',base_url='https://aux.example.org',catalog_profile=out/'aux-catalog-profile.json')
            menu=eng.gen_ipxe([],cfg)
            self.assertIn('item custom_recipes Reviewed custom recipes',menu)
            self.assertIn('kernel https://example.org/vmlinuz',menu)
            self.assertIn('hardware not tested',menu)

    def test_profile_entries_appear_in_the_catalogue_and_refresh_actual_sizes(self):
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Replica',LIM)
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp)/'profile.json';pth.write_text(json.dumps(perfil))
            cat=Path(tmp)/'catalog.json';cat.write_text(json.dumps({'entries':[dict(entrada(),id='new-id',size_bytes=9999)]}))
            ent=next(e for e in webapps.modelo(catalog_file=cat,profile_file=pth)['entries'] if e['id']=='one')
            self.assertEqual(ent['size_bytes'],9999)

    def test_cancelled_api_review_makes_no_provider_call(self):
        campos=['28','100','10','test-model','Expand rescue catalogue','']
        with patch.object(catalog_assist_ui,'campo',side_effect=campos),patch.object(catalog_assist_ui,'elige',return_value='openai'), \
             patch.object(api,'consulta_propuesta') as provider:
            self.assertIsNone(catalog_assist_ui.asistencia_interactiva([entrada()]))
        provider.assert_not_called()

    def test_origin_only_profile_does_not_export_local_download_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth=catalog.publica([dict(entrada(modo='origin'),id='origin',selection_mode='origin')],Path(tmp))
            self.assertNotIn('https://example.org/one.iso',(pth/'heavy-url.txt').read_text())

    def test_profile_sync_updates_its_own_lists_not_the_aux_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=perfiles.exporta_perfil(perfiles.perfil_desde_seleccion([entrada()],'Profile',LIM),root/'profile',{'sources':[]})
            cfg=json.loads((p/'crawler.sources.json').read_text());sid=cfg['download_slots'][0]['id']
            cat=root/'current.json';cat.write_text(json.dumps({'entries':[dict(entrada(),source_id=sid,original_url='https://example.org/new.iso')]}))
            from auxlib.catalog_workflow import plan_listas
            changes=plan_listas(p/'crawler.sources.json',cat)
            self.assertTrue(changes);self.assertTrue(all(path.parent==p for path,_,_ in changes))

    def test_active_replica_limits_reach_the_deployment_validator(self):
        from build import motor
        import sys
        eng=motor();perfil=perfiles.perfil_desde_seleccion([entrada()],'Small replica',dict(LIM,ram_gib=8,ssd_gib=20))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'state').mkdir();(root/'fast-boot.json').write_text('{}')
            (root/'state/catalog-profile.json').write_text(json.dumps(perfil));urls=root/'url.txt';urls.write_text('https://example.org/one.iso\n')
            with patch.object(sys,'argv',['deploy.sh','ram','--url-file',str(urls),'--dry-run']):
                cfg=eng.obt_args('deploy',root)
            self.assertEqual((cfg.ram_budget_gib,cfg.ssd_budget_gib,cfg.ram_reserve_percent),(8,20,10))

    def test_profile_timestamp_cannot_inject_commands_into_an_ipxe_header(self):
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Profile',LIM)
        perfil['created_at']='2026-11-10\nchain https://example.org/evil.ipxe'
        with self.assertRaises(ValueError):perfiles.valida_perfil(perfil)

    def test_imported_sources_cannot_hide_an_unbounded_regex(self):
        perfil=perfiles.perfil_desde_seleccion([entrada()],'Profile',LIM,fuentes=[api.compila_fuente(fuente())])
        perfil['sources'][0]['slot']['filename_pattern']='(a+)+' 
        with self.assertRaises(ValueError):perfiles.valida_perfil(perfil)

    def test_assisted_stable_source_cannot_silently_select_a_beta(self):
        src=api.compila_fuente(fuente())
        opciones=[{'original_url':'https://example.org/rescue-2.0-x86_64.iso'},
                  {'original_url':'https://example.org/rescue-3.0-beta1-x86_64.iso'}]
        ent=catalog_downloads.resuelve_slot(src['slot'],opciones)
        self.assertEqual(ent['release'],'2.0')

    def test_assisted_beta_source_does_not_fall_back_to_a_stable_release(self):
        src=api.compila_fuente(dict(fuente(),channel='beta'))
        with self.assertRaises(ValueError):catalog_downloads.resuelve_slot(src['slot'],[{'original_url':'https://example.org/rescue-2.0-x86_64.iso'}])


if __name__=='__main__':unittest.main()
