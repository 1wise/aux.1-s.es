#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Verify the optional API path with fixtures, without provider credentials or API calls."""
import base64
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import ssl
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
import warnings
from unittest.mock import Mock, patch
import urllib.error

DIR_APP = Path(__file__).resolve().parent
ROOT = DIR_APP.parent


def modulo(nom, pth):
    spec = importlib.util.spec_from_file_location(nom, pth)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ai = modulo('fixture_ai', DIR_APP / 'payload/ai.py')
prep = modulo('fixture_prepare', DIR_APP / 'prepare.py')
fin = modulo('fixture_finish', DIR_APP / 'finish.py')
app = modulo('fixture_assist', DIR_APP / 'payload/assist.py')
CFG = ai.valida_cfg({})
HIST = [{'role': 'user', 'content': '¿Qué discos hay?'}, {'role': 'assistant', 'content': 'Revisa lsblk.'}]
GRUB = """set default=0
set timeout=60
menuentry 'Start AUX Assist' --class fedora {
    linux /images/pxeboot/vmlinuz root=live:CDLABEL=AUX aux.assist aux.ai.available=1
    initrd /images/pxeboot/initrd.img
}
"""


class API(unittest.TestCase):
    def test_public_settings_reject_secrets_and_bad_models(self):
        for dat in [{'api_key': 'secret'}, {'openai': {'model': 'ok', 'key': 'secret'}},
                    {'gemini': {'model': '../elsewhere'}}, {'enabled': 'false'},
                    {'max_output_tokens': True}, {'timeout_seconds': 121}]:
            with self.subTest(config=dat), self.assertRaises(ValueError):
                ai.valida_cfg(dat)
        self.assertFalse(ai.valida_cfg({'enabled': False})['enabled'])

    def test_requests_have_only_explicit_conversation_and_limits(self):
        url, dat = ai.peticion('openai', 'fixture-model', HIST, CFG)
        self.assertEqual(url, 'https://api.openai.com/v1/responses')
        self.assertEqual(dat['input'], HIST)
        self.assertFalse(dat['store'])
        self.assertNotIn('tools', dat)
        url, dat = ai.peticion('gemini', 'fixture-model', HIST, CFG)
        self.assertTrue(url.endswith('/fixture-model:generateContent'))
        self.assertEqual([x['role'] for x in dat['contents']], ['user', 'model'])
        self.assertEqual(dat['generationConfig']['maxOutputTokens'], 1024)
        self.assertNotIn('tools', dat)

    def test_all_openai_messages_and_refusals_are_decoded(self):
        dat = {'output': [{'type': 'reasoning'}, {'type': 'message', 'content': [
            {'type': 'output_text', 'text': 'primero'}]}, {'type': 'message', 'content': [
            {'type': 'refusal', 'refusal': 'segundo'}]}]}
        self.assertEqual(ai.extrae('openai', dat), 'primero\nsegundo')
        dat['status'] = 'incomplete'
        self.assertIn('incompleta', ai.extrae('openai', dat))

    def test_gemini_visible_parts_only_and_blocked_response(self):
        dat = {'candidates': [{'content': {'parts': [
            {'thought': True, 'text': 'private reasoning'}, {'text': 'visible'}]}, 'finishReason': 'MAX_TOKENS'}]}
        txt = ai.extrae('gemini', dat)
        self.assertIn('visible', txt)
        self.assertNotIn('private reasoning', txt)
        self.assertIn('incompleta', txt)
        with self.assertRaisesRegex(RuntimeError, 'no devolvió texto'):
            ai.extrae('gemini', {'promptFeedback': {'blockReason': 'SAFETY'}})

    def test_terminal_controls_are_never_printed(self):
        txt = ai.texto_seguro('ok\n\t\x1b]52;c;data\x07\r\u202eend')
        for car in ('\x1b', '\x07', '\r', '\u202e'):
            self.assertNotIn(car, txt)
        self.assertIn('ok\n\t', txt)

    def test_tls_verified_and_key_in_header_only(self):
        for prov in ai.TITULOS:
            rsp = Mock()
            rsp.read.return_value = json.dumps({'output': [], 'candidates': []}).encode()
            abr = Mock()
            abr.open.return_value.__enter__ = Mock(return_value=rsp)
            abr.open.return_value.__exit__ = Mock(return_value=False)
            with patch.object(ai.urllib.request, 'build_opener', return_value=abr) as make, \
                 patch.object(ai, 'extrae', return_value='done'):
                self.assertEqual(ai.consulta(prov, 'fixture-model', 'fixture-secret', HIST, CFG), 'done')
            req = abr.open.call_args.args[0]
            self.assertNotIn('fixture-secret', req.full_url)
            self.assertNotIn('fixture-secret', req.data.decode())
            cab = {key.lower(): val for key, val in req.header_items()}
            self.assertEqual(cab['authorization' if prov == 'openai' else 'x-goog-api-key'],
                'Bearer fixture-secret' if prov == 'openai' else 'fixture-secret')
            ctx = make.call_args.args[1]._context
            self.assertTrue(ctx.check_hostname)
            self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
            self.assertEqual(rsp.read.call_args.args, (ai.MAX_RESPUESTA + 1,))

    def test_redirect_and_error_bodies_never_expose_key(self):
        self.assertIsNone(ai.SinRedireccion().redirect_request(None, None, 302, '', {}, 'http://wrong.test'))
        abr = Mock()
        abr.open.side_effect = urllib.error.HTTPError('https://api.openai.com/v1/responses',
            429, 'fixture-secret', {}, io.BytesIO(b'fixture-secret'))
        with patch.object(ai.urllib.request, 'build_opener', return_value=abr), \
             self.assertRaisesRegex(RuntimeError, 'HTTP 429') as err:
            ai.consulta('openai', 'fixture-model', 'fixture-secret', HIST, CFG)
        self.assertNotIn('fixture-secret', str(err.exception))
        self.assertEqual(abr.open.call_count, 1)

    def test_terminal_clears_context_and_rejects_key_in_prompt(self):
        salida = io.StringIO()
        clave_larga = 'k' * 165
        with patch.object(ai.sys.stdin, 'isatty', return_value=True), \
             patch.object(ai.getpass, 'getpass', return_value=clave_larga), \
             patch('builtins.input', side_effect=['fixture-model', 'O', clave_larga, 'pregunta 1', '/nueva', 'pregunta 2', '/salir']), \
             patch.object(ai, 'consulta', return_value='respuesta') as consulta, contextlib.redirect_stdout(salida):
            ai.terminal('openai', CFG)
        self.assertEqual(consulta.call_count, 2)
        self.assertEqual(consulta.call_args.args[3], [{'role': 'user', 'content': 'pregunta 2'}])
        self.assertNotIn('fixture-secret', salida.getvalue())
        self.assertNotIn(clave_larga, salida.getvalue())
        self.assertIn('Mensaje rechazado', salida.getvalue())

    def test_disabled_and_noninteractive_sessions_do_not_request_keys(self):
        with patch.object(ai.getpass, 'getpass') as clave, self.assertRaises(ValueError):
            ai.terminal('openai', ai.valida_cfg({'enabled': False}))
        clave.assert_not_called()
        with patch.object(ai.sys.stdin, 'isatty', return_value=False), \
             patch.object(ai.getpass, 'getpass') as clave, self.assertRaises(ValueError):
            ai.terminal('gemini', CFG)
        clave.assert_not_called()

    def test_key_prompt_fails_closed_if_terminal_echo_cannot_be_disabled(self):
        def falla(*_):
            warnings.warn('fixture fallback', ai.getpass.GetPassWarning)
        with patch.object(ai.sys.stdin, 'isatty', return_value=True), \
             patch('builtins.input', side_effect=['fixture-model', 'O']), \
             patch.object(ai.getpass, 'getpass', side_effect=falla), \
             patch.object(ai, 'consulta') as api, contextlib.redirect_stdout(io.StringIO()), \
             self.assertRaisesRegex(ValueError, 'desactivar el eco'):
            ai.terminal('openai', CFG)
        api.assert_not_called()

    def test_visible_long_key_and_invalid_mode(self):
        with patch('builtins.input', side_effect=['', 'k' * 165]), \
             patch.object(ai.getpass, 'getpass', side_effect=AssertionError('visible mode')):
            self.assertEqual(ai.pide_clave(), 'k' * 165)
        with patch('builtins.input', return_value='invalid'), self.assertRaises(ValueError):
            ai.pide_clave()

    def test_preload_selects_provider_and_never_prints_the_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            for prov, clave in (('openai','fixture-openai-'+'x'*150),('gemini','fixture-gemini-secret')):
                (Path(tmp)/(prov+'.key')).write_text(clave+'\n')
                out=io.StringIO()
                with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':tmp}), \
                     patch('builtins.input',return_value='') as entrada,contextlib.redirect_stdout(out):
                    self.assertEqual(ai.pide_clave(prov),clave)
                entrada.assert_called_once();self.assertNotIn(clave,out.getvalue())

    def test_manual_override_keeps_the_preloaded_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp)/'openai.key';pth.write_text('fixture-saved-secret\n')
            with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':tmp}), \
                 patch('builtins.input',side_effect=['V','fixture-manual-secret']):
                self.assertEqual(ai.pide_clave('openai'),'fixture-manual-secret')
            self.assertEqual(pth.read_text(),'fixture-saved-secret\n')

    def test_missing_malformed_and_linked_preload_use_manual_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp)/'openai.key'
            for dat in (None,b'',b'x'*600,b'fixture-key\nsecond-line',b'fixture-\x00-key'):
                if dat is None:pth.unlink(missing_ok=True)
                else:pth.write_bytes(dat)
                with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':tmp}), \
                     patch('builtins.input',side_effect=['V','fixture-manual-secret']), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(ai.pide_clave('openai'),'fixture-manual-secret')
            pth.unlink();pth.symlink_to(Path(tmp)/'other')
            with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':tmp}),self.assertRaises(OSError):
                ai.lee_clave_preparada('openai')

    def test_preloaded_terminal_key_reaches_only_the_api_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'openai.key').write_text('fixture-preloaded-secret\n');out=io.StringIO()
            with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':tmp}), \
                 patch.object(ai.sys.stdin,'isatty',return_value=True), \
                 patch('builtins.input',side_effect=['','pregunta','/salir']), \
                 patch.object(ai,'consulta',return_value='respuesta') as consulta,contextlib.redirect_stdout(out):
                ai.terminal('openai',ai.valida_cfg({'openai':{'model':'fixture-model'}}))
            self.assertEqual(consulta.call_args.args[:3],('openai','fixture-model','fixture-preloaded-secret'))
            self.assertNotIn('fixture-preloaded-secret',out.getvalue())

    def test_portable_menu_stages_selected_key_before_service_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp);(pth/'portable_usb.py').touch()
            with patch.object(app,'DIR_APP',pth),patch.object(app,'ia_disponible',return_value=True),patch.object(app,'ejecuta') as run:
                app.inicia_ia('gemini')
            self.assertEqual([c.args[0] for c in run.call_args_list],[
                ['/usr/bin/python3',str(pth/'portable_usb.py'),'api-stage','--provider','gemini'],
                ['systemctl','start','aux-gemini.service'],['chvt','5']])

    def test_recipe_contains_units_and_public_models_without_server_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {'cli': {'nodes': {'excalibur': {'url': 'https://cli.example.test',
                'secret_file': 'SERVER-SECRET-MUST-NOT-ENTER-ISO'}}}, 'ai': ai.valida_cfg({})}
            arc = Path(tmp) / 'config.json'
            arc.write_text(json.dumps(cfg))
            out = Path(tmp) / 'work'
            prep.render(out, pth_cfg=arc)
            txt = (out / 'assist.ks').read_text()
            dat = json.loads(base64.b64decode(txt.split("base64.b64decode('", 1)[1].split("')", 1)[0]))
            self.assertNotIn('SERVER-SECRET-MUST-NOT-ENTER-ISO', str(dat))
            files = {ent['path']: base64.b64decode(ent['data']).decode() for ent in dat}
            for nom in ('aux-gpt.service', 'aux-gemini.service'):
                unit = files['/etc/systemd/system/' + nom]
                self.assertIn('User=aux-ai', unit)
                self.assertIn('Requires=aux-exec.service', unit)
                self.assertIn('SupplementaryGroups=tty', unit)
                self.assertIn('PrivateDevices=no', unit)
                self.assertIn('--agent', unit)
                self.assertNotIn('User=root', unit)
                self.assertNotIn('[Install]', unit)
            self.assertEqual(json.loads(files['/usr/share/aux-assist/ai.json']), CFG)
            cfg['ai']['openai']['api_key'] = 'forbidden'
            arc.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError):
                prep.render(Path(tmp) / 'rejected', pth_cfg=arc)

    def test_grub_only_advertises_declared_ai_and_keeps_default(self):
        txt = fin.configura(GRUB)
        self.assertIn('set timeout=5', txt)
        self.assertIn('set default=0', txt)
        for prov in ai.TITULOS:
            self.assertIn('--id aux-ai-' + prov, txt)
            self.assertIn(' aux.ai=' + prov, txt)
        self.assertLess(txt.index("menuentry 'Start AUX Assist'"), txt.index("menuentry 'GPT Assist"))
        self.assertNotIn('--id aux-ai-', fin.configura(GRUB.replace(' aux.ai.available=1', '')))

    @unittest.skipUnless((ROOT / 'generate.sh').is_file() and (ROOT / 'src/common.py').is_file(),
                         'iPXE integration requires the complete AUX/PXE source bundle')
    def test_ipxe_reuses_image_and_does_not_change_automatic_default(self):
        import sys
        sys.path.insert(0, str(ROOT / 'src'))
        eng = ModuleType('fixture_generate');eng.__file__ = str(ROOT / 'generate.sh')
        txt = (ROOT / 'generate.sh').read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
        exec(compile(txt, str(ROOT / 'generate.sh'), 'exec'), eng.__dict__)
        with tempfile.TemporaryDirectory() as tmp:
            web = Path(tmp)
            rec = eng.obt_meta('https://example.test/aux-assist-6.3.0-dev.1-x86_64.iso')
            tree = web / rec['tree']
            for rel in ['images/pxeboot/vmlinuz', 'images/pxeboot/initrd.img', 'LiveOS/squashfs.img']:
                arc = tree / rel;arc.parent.mkdir(parents=True, exist_ok=True);arc.write_bytes(b'fixture')
            arc = tree / 'boot/grub2/grub.cfg';arc.parent.mkdir(parents=True)
            arc.write_text(GRUB.replace('root=live:CDLABEL=AUX', 'root=live:CDLABEL=AUX rd.live.image'))
            cfg = SimpleNamespace(output=web, pxe_url='http://pxe.test', base_url='https://aux.test', boot={}, ai={})
            rec.update(published=True, status='deployed')
            rec['_boot'] = eng.gen_fedora(rec, cfg, tree)
            self.assertTrue(rec['ai_assist'])
            menu = eng.gen_ipxe([rec], cfg)
            self.assertIn('item ai_menu 0.A.', menu)
            self.assertIn('set auto_timeout 60000', menu)
            self.assertIn('set auto_target ' + rec['id'], menu)
            self.assertNotIn('set auto_target ai_', menu)
            for prov in ai.TITULOS:
                self.assertIn(' aux.ai=' + prov + ' || goto error', menu)
            cfg.ai = {'enabled': False}
            self.assertNotIn(':ai_menu', eng.gen_ipxe([rec], cfg))
            cfg.ai = {};rec['ai_assist'] = False
            self.assertNotIn(':ai_menu', eng.gen_ipxe([rec], cfg))

    def test_local_menu_starts_only_the_selected_service_and_vt(self):
        for prov, uni, tty in [('openai', 'aux-gpt.service', '4'), ('gemini', 'aux-gemini.service', '5')]:
            with patch.object(app, 'ia_disponible', return_value=True), patch.object(app, 'ejecuta') as run:
                app.inicia_ia(prov)
            self.assertEqual([call.args[0] for call in run.call_args_list],
                             [['systemctl', 'start', uni], ['chvt', tty]])


if __name__ == '__main__':
    unittest.main()
