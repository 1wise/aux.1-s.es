# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Test reviewed URL recovery, daily discovery and explicit provider invocation."""
import contextlib
import io
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
from types import SimpleNamespace
import unittest
import urllib.error
from unittest.mock import patch

from auxlib import catalog, catalog_downloads as desc, catalog_repair as repara
from auxlib import catalog_repair_ui as ui, catalog_assist as api, catalog_assist_ui as asist, catalog_workflow as flujo


def url(ver, host='upstream.example'):
    return 'https://' + host + '/tool-' + str(ver) + '-amd64-beta.iso'


def config():
    return {'download_lists': {'all': 'url.txt'}, 'sources': [],
        'download_sources': [{'id': 'upstream', 'format': 'artifact-html',
            'url': 'https://upstream.example/releases/', 'allowed_hosts': ['upstream.example', 'mirror.example']}],
        'download_slots': [{'id': 'd17-tool', 'source_id': 'upstream', 'latest_available': True,
            'filename_pattern': r'tool-(?P<release>[0-9]+)-amd64-beta\.iso',
            'family': 'tool', 'architecture': 'x86_64', 'kind': 'image', 'download_class': 'light', 'channel': 'beta'}]}


def fila():
    return {'slot_id': 'd17-tool', 'previous_url': url(1), 'original_url': url(1), 'release': '1',
        'source_index': 'https://upstream.example/releases/', 'status': 'resolved', 'http': {'http': 'passed'},
        'unavailable_newer_versions': [{'release': '2', 'url': url(2), 'error': 'HTTP 404'}]}


class Recuperacion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)
        self.cfg = SimpleNamespace(config=self.pth / 'sources.json', output=self.pth / 'state',
            cache=self.pth / 'cache', url_file=self.pth / 'url.txt', select=None, evidence=None, download=False)
        self.cfg.config.write_text(json.dumps(config()))
        self.cfg.url_file.write_text(url(1) + '\n')
        self.cfg.output.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def candidata(self, ver=2, host='mirror.example'):
        pth = self.cfg.output / 'url-candidates.json'
        repara.guarda_candidata(pth, fila(), url(ver, host), fila()['source_index'])
        return repara.lee_candidatas(pth)

    def rastrea(self, opciones, vals=(), comprobar=None):
        with patch.object(desc, 'candidatos', side_effect=opciones if isinstance(opciones, Exception) else None,
                          return_value=opciones), patch('auxlib.catalog_mirrors.valida_espejo'), \
             contextlib.redirect_stdout(io.StringIO()):
            return desc.rastrea_descargas(config(), self.cfg.config, self.cfg.cache, lambda *a: b'',
                comprobar or (lambda *a: {'http': 'passed', 'size_bytes': 100}), candidatas=vals)

    def test_available_fallback_is_an_optional_issue_and_clean_result_is_not(self):
        self.assertEqual(repara.pendientes({'resources': [fila()]}), [fila()])
        limpia = dict(fila(), unavailable_newer_versions=[])
        self.assertEqual(repara.pendientes({'resources': [limpia]}), [])
        self.assertEqual(len(repara.pendientes({'resources': [dict(limpia, status='failed')]})), 1)

    def test_manual_candidate_does_not_pin_a_release_when_upstream_updates_next_day(self):
        vals = self.candidata(2)
        uno, _ = self.rastrea([{'original_url': url(1)}], vals)
        igual, _ = self.rastrea([{'original_url': url(2)}], vals)
        dos, _ = self.rastrea([{'original_url': url(3)}], vals)
        self.assertEqual((uno[0]['release'], dos[0]['release']), ('2', '3'))
        self.assertEqual(igual[0]['original_url'], url(2))
        self.assertNotIn('candidate_origin', dos[0])

    def test_another_url_for_the_same_filename_is_tried_after_404(self):
        def comprueba(dst, *args):
            if dst == url(3):
                raise urllib.error.HTTPError(dst, 404, 'Not Found', None, None)
            return {'http': 'passed', 'size_bytes': 100}
        ents, inf = self.rastrea([{'original_url': url(3)}, {'original_url': url(3, 'mirror.example')}],
                                  comprobar=comprueba)
        self.assertEqual(ents[0]['original_url'], url(3, 'mirror.example'))
        self.assertEqual(inf['http_passed'], 1)
        self.assertEqual(inf['resources'][0]['unavailable_newer_versions'][0]['url'], url(3))

    def test_manual_url_can_recover_an_unavailable_index_and_keeps_warning(self):
        ents, inf = self.rastrea(ValueError('index offline'), self.candidata())
        self.assertTrue(inf['complete'])
        self.assertEqual(ents[0]['candidate_origin'], 'manual')
        self.assertEqual(inf['resources'][0]['source_warning'], 'index offline')
        self.assertEqual(ents[0]['verification']['download_hash'], 'not-checked')
        self.assertEqual(ents[0]['verification']['source_signature'], 'not-checked')

    def test_unmapped_url_can_bind_to_a_reviewed_existing_rule(self):
        vieja = 'https://upstream.example/renamed-old.iso'
        sin_regla = {'previous_url': vieja, 'status': 'unmapped'}
        ent = repara.comprueba_candidata(config(), sin_regla, url(2), fila()['source_index'],
            comprobar=lambda *a: {'http': 'passed'}, valida_red=lambda *a: None)
        self.assertEqual(ent['slot_id'], 'd17-tool')
        self.cfg.url_file.write_text(vieja + '\n')
        pth = self.cfg.output / 'url-candidates.json'
        repara.guarda_candidata(pth, dict(sin_regla, slot_id=ent['slot_id']), url(2), fila()['source_index'])
        ents, inf = self.rastrea([{'original_url': url(3)}], repara.lee_candidatas(pth))
        self.assertTrue(inf['complete'])
        self.assertEqual(ents[0]['release'], '3')

    def test_recovered_unmapped_url_reaches_reviewed_download_lists(self):
        vieja='https://upstream.example/renamed-old.iso'
        for nom in ('url.txt','light-url.txt','heavy-url.txt'):(self.pth/nom).write_text(vieja+'\n')
        pth=self.cfg.output/'url-candidates.json'
        repara.guarda_candidata(pth,dict(fila(),previous_url=vieja),url(2),fila()['source_index'])
        from functools import partial
        real=desc.rastrea_descargas
        with patch.object(desc,'candidatos',return_value=[{'original_url':url(3)}]), \
             patch.object(desc,'rastrea_descargas',side_effect=partial(real,comprobar=lambda *a:{'http':'passed','size_bytes':100})), \
             patch('auxlib.catalog_mirrors.valida_espejo'),contextlib.redirect_stdout(io.StringIO()):
            catalog.actualiza(self.cfg)
        cambios=flujo.plan_listas(self.cfg.config,self.cfg.output/'current/catalog.json')
        self.assertEqual(len(cambios),3)
        self.assertTrue(all(nuevo==url(3)+'\n' for _,_,nuevo in cambios))
        self.assertEqual(self.cfg.url_file.read_text(),vieja+'\n')

    def test_matching_official_hash_is_reused_but_not_claimed_as_verified(self):
        vals = self.candidata()
        def comprueba(dst,*args):
            if dst==url(2):raise urllib.error.HTTPError(dst,404,'Not Found',None,None)
            return {'http':'passed','size_bytes':100}
        ents, _ = self.rastrea([{'original_url': url(2), 'sha256': 'a' * 64}], vals,comprueba)
        self.assertEqual(ents[0]['sha256'], 'a' * 64)
        self.assertEqual(ents[0]['original_url'], url(2, 'mirror.example'))
        self.assertEqual(ents[0]['verification']['download_hash'], 'not-checked')

    def test_wrong_architecture_channel_and_credentials_are_rejected_before_http(self):
        invalidas = [url(2).replace('amd64', 'arm64'), url(2).replace('-beta', ''),
                     'http://mirror.example/tool-2-amd64-beta.iso', url(2) + '?api_key=secret']
        for dst in invalidas:
            with self.subTest(url=dst), patch.object(desc, 'comprueba_enlace') as head:
                with self.assertRaises(ValueError):
                    repara.comprueba_candidata(config(), fila(), dst, fila()['source_index'])
                head.assert_not_called()

    def test_nonpublic_destination_is_rejected_before_http(self):
        with patch('auxlib.catalog_mirrors.valida_espejo', side_effect=ValueError('private destination')), \
             patch.object(desc, 'comprueba_enlace') as head, self.assertRaisesRegex(ValueError, 'private'):
            repara.comprueba_candidata(config(), fila(), url(2), fila()['source_index'])
        head.assert_not_called()

    def test_current_rules_can_retire_an_old_candidate_without_blocking_discovery(self):
        vals = self.candidata()
        slot = dict(config()['download_slots'][0], filename_pattern=r'new-(?P<release>[0-9]+)-amd64-beta\.iso')
        self.assertEqual(repara.opciones_guardadas(vals, slot, config()['download_sources'][0], []), [])

    def test_saved_candidates_keep_backup_and_only_eight_recent_urls_per_slot(self):
        for ver in range(12):
            self.candidata(ver)
        pth = self.cfg.output / 'url-candidates.json'
        vals = repara.lee_candidatas(pth)
        self.assertEqual(len(vals), 8)
        self.assertEqual(vals[-1]['original_url'], url(11, 'mirror.example'))
        self.assertTrue(pth.with_name(pth.name + '.before-review').is_file())

    def test_real_catalogue_update_reads_the_saved_candidate_register(self):
        self.candidata()
        with patch.object(desc, 'candidatos', return_value=[{'original_url': url(1)}]), \
             patch.object(desc, 'comprueba_enlace'), patch('auxlib.catalog_mirrors.valida_espejo'), \
             patch('urllib.request.build_opener') as network, contextlib.redirect_stdout(io.StringIO()):
            # rastrea_descargas binds the HTTP checker at definition time.
            from functools import partial
            real = desc.rastrea_descargas
            with patch.object(desc, 'rastrea_descargas', side_effect=partial(real,
                    comprobar=lambda *a: {'http': 'passed', 'size_bytes': 100})):
                out = catalog.actualiza(self.cfg)
        network.assert_not_called()
        dat = json.loads((out / 'catalog.json').read_text())
        self.assertEqual(dat['entries'][0]['original_url'], url(2, 'mirror.example'))
        self.assertTrue(json.loads((self.cfg.output / 'crawl-report.json').read_text())['publication_complete'])
        self.candidata(4)
        with self.assertRaisesRegex(ValueError, 'URL revisadas cambiaron'):
            flujo.plan_listas(self.cfg.config, self.cfg.output / 'current/catalog.json')

    def test_provider_schema_is_the_recovery_schema_for_both_providers(self):
        for prov in ('openai', 'gemini'):
            _, body = api.peticion(prov, 'fixture-model', {'request': 'fixture'},
                                   esquema=ui.ESQUEMA, instruccion=ui.INSTRUCCION)
            esquema = body['text']['format']['schema'] if prov == 'openai' else body['generationConfig']['responseJsonSchema']
            self.assertEqual(esquema, ui.ESQUEMA)

    def test_provider_unknown_fields_commands_and_private_credentials_are_not_accepted(self):
        base = {'summary': 'Candidate', 'candidates': [{'url': url(2),
                'reference_url': fila()['source_index'], 'reason': 'Review this URL'}]}
        self.assertEqual(repara.valida_sugerencias(base), base)
        for dat in (dict(base, commands=['touch /tmp/no']), dict(base, summary='\x1b[31m'),
                    dict(base, candidates=[dict(base['candidates'][0], url=url(2) + '?token=secret')])):
            with self.assertRaises(ValueError):
                repara.valida_sugerencias(dat)

    def test_cancelling_api_review_makes_no_paid_call_or_key_request(self):
        for prov in ('openai', 'gemini'):
            with patch.object(ui, 'campo', return_value='fixture-model'), \
                 patch.object(asist, 'campo', return_value=''), \
                 patch.object(asist.getpass, 'getpass') as clave, patch.object(api, 'consulta_propuesta') as provider:
                self.assertIsNone(ui.propone_api(self.cfg, config(), fila(), prov))
            provider.assert_not_called()
            clave.assert_not_called()

    def test_provider_suggestion_requires_http_review_and_preserves_only_public_origin(self):
        val = {'url': url(2, 'mirror.example'), 'reference_url': fila()['source_index'], 'reason': 'Candidate only'}
        for prov in ('openai', 'gemini'):
            with patch.object(ui, 'elige', side_effect=(prov, val)), \
                 patch.object(ui, 'campo', side_effect=('fixture-model', '', 'GUARDAR')), \
                 patch.object(asist, 'campo', return_value='CONSULTAR'), \
                 patch.dict(asist.os.environ, {'OPENAI_API_KEY': 'PRIVATE-API-KEY', 'GEMINI_API_KEY': 'PRIVATE-API-KEY'}), \
                 patch.object(api, 'consulta_propuesta', return_value={'summary': 'Review', 'candidates': [val]}) as provider, \
                 patch('auxlib.catalog_mirrors.valida_espejo'), \
                 patch.object(desc, 'comprueba_enlace', return_value={'http': 'passed'}), \
                 contextlib.redirect_stdout(io.StringIO()) as log:
                self.assertTrue(ui.revisa_recurso(self.cfg, config(), fila()))
            provider.assert_called_once()
            self.assertEqual(provider.call_args.kwargs['esquema'], ui.ESQUEMA)
            pth = self.cfg.output / 'url-candidates.json'
            self.assertNotIn('PRIVATE-API-KEY', pth.read_text() + log.getvalue())
            self.assertEqual(repara.lee_candidatas(pth)[-1]['candidate_origin'], prov)

    def test_failed_http_candidate_is_never_saved(self):
        with patch('auxlib.catalog_mirrors.valida_espejo'), \
             patch.object(desc, 'comprueba_enlace', side_effect=ValueError('HTTP failed')), \
             patch.object(ui, 'campo') as confirm, self.assertRaises(ValueError), \
             contextlib.redirect_stdout(io.StringIO()):
            ui.revisa_url(self.cfg, config(), fila(), url(2), fila()['source_index'], 'manual')
        confirm.assert_not_called()
        self.assertFalse((self.cfg.output / 'url-candidates.json').exists())

    def test_blank_manual_url_keeps_the_provider_choices_available(self):
        with patch.object(ui, 'elige', side_effect=('manual', 'gemini', 'back')), \
             patch.object(ui, 'campo', return_value=''), patch.object(ui, 'propone_api', return_value=None) as provider:
            self.assertFalse(ui.revisa_recurso(self.cfg, config(), fila()))
        self.assertEqual(provider.call_args.args[-1], 'gemini')

    def test_manual_review_stores_candidate_and_retry_requires_explicit_choice(self):
        (self.cfg.output / 'crawl-report.json').write_text(json.dumps({'resources': [fila()]}))
        with patch.object(ui, 'elige', side_effect=(fila(), 'manual', 'retry')), \
             patch.object(ui, 'campo', side_effect=(url(2, 'mirror.example'), fila()['source_index'], 'GUARDAR')), \
             patch('auxlib.catalog_mirrors.valida_espejo'), \
             patch.object(desc, 'comprueba_enlace', return_value={'http': 'passed', 'size_bytes': 100}), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(ui.recupera_interactivo(self.cfg))
        self.assertEqual(len(repara.lee_candidatas(self.cfg.output / 'url-candidates.json')), 1)

    def test_both_successful_warning_and_failed_crawl_offer_the_recovery_menu(self):
        informe = {'resolved': 1, 'http_passed': 1, 'total': 1, 'resources': [fila()]}
        (self.cfg.output / 'crawl-report.json').write_text(json.dumps(informe))
        for resultado in (self.pth / 'release', ValueError('incomplete')):
            with patch.object(catalog, 'actualiza', side_effect=resultado if isinstance(resultado, Exception) else None,
                              return_value=resultado), patch('auxlib.console_ui.campo', return_value=''), \
                 patch.object(ui, 'recupera_interactivo', return_value=False) as recupera, \
                 contextlib.redirect_stdout(io.StringIO()):
                salida = flujo.ejecuta_rastreo_interactivo(self.cfg)
            recupera.assert_called_once_with(self.cfg)
            self.assertEqual(salida.succeeded, not isinstance(resultado, Exception))

    def test_real_terminal_allows_blank_manual_url_then_cancels_provider_review(self):
        raiz=Path(__file__).resolve().parents[1]
        fd,esclavo=pty.openpty()
        fcntl.ioctl(esclavo,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0))
        codigo=('from tests7.test_catalog_repair import *; '
                'cfg=SimpleNamespace(output=Path('+repr(str(self.cfg.output))+'),cache=Path('+repr(str(self.cfg.cache))+')); '
                'api.consulta_propuesta=lambda *a,**k: (_ for _ in ()).throw(AssertionError("unexpected provider call")); '
                'print("RECOVERY_RESULT",ui.revisa_recurso(cfg,config(),fila()))')
        proc=subprocess.Popen([sys.executable,'-c',codigo],cwd=raiz,stdin=esclavo,stdout=esclavo,stderr=esclavo,
                              env=os.environ|{'TERM':'xterm-256color'},start_new_session=True)
        os.close(esclavo)
        def espera(txt):
            datos=b'';fin=time.monotonic()+8
            while txt.encode() not in datos and time.monotonic()<fin:
                if select.select([fd],[],[],.1)[0]:
                    try:datos+=os.read(fd,65536)
                    except OSError:break
            self.assertIn(txt.encode(),datos,datos.decode(errors='replace')[-2000:])
        try:
            espera('Introducir URL manual')
            os.write(fd,b'j\r');espera('URL HTTPS del archivo')
            os.write(fd,b'\r');espera('Introducir URL manual')
            os.write(fd,b'jj\r');espera('Modelo API disponible')
            os.write(fd,b'fixture-model\r');espera('Escribir CONSULTAR')
            os.write(fd,b'\x1b');espera('RECOVERY_RESULT False')
            self.assertEqual(proc.wait(timeout=5),0)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=5)
            os.close(fd)
