#!/usr/bin/env python3
# Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Exercise the real file transaction path; no host packages/services/disks change."""
import base64
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'payload'))
import ai
import ai_agent
import aux_exec


def plan(**campos):
    dat = {'action': 'write_file', 'target': 'hola.txt', 'content': 'Hola món · ñ\n',
           'state': '', 'reason': 'Probar una escritura reversible.'}
    dat.update(campos)
    return dat


class Ejecutor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pth = Path(self.tmp.name)
        self.motor = aux_exec.Motor(self.pth / 'state', self.pth / 'managed')

    def tearDown(self):
        self.tmp.cleanup()

    def propone(self, dat=None):
        return self.motor.atiende({'op': 'propose', 'plan': dat or plan()}, os.geteuid())

    def aplica(self, dat, **kw):
        return self.motor.aplica(dat['id'], dat['digest'], **kw)

    def test_propose_and_dry_run_never_write_target(self):
        dat = self.propone()
        self.assertEqual(dat['status'], 'pending')
        self.assertFalse(self.motor.pth_trb.exists())
        self.assertTrue(self.aplica(dat, dry_run=True)['dry_run'])
        self.assertFalse(self.motor.pth_trb.exists())
        self.assertEqual(self.motor.lee(dat['id'])['status'], 'pending')

    def test_real_apply_undo_and_no_replay(self):
        dat = self.propone()
        self.assertEqual(self.aplica(dat)['status'], 'applied')
        arc = self.motor.pth_trb / 'hola.txt'
        self.assertEqual(arc.read_text(), plan()['content'])
        self.assertEqual(arc.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            self.aplica(dat)
        self.assertEqual(self.aplica(dat, undo=True)['status'], 'undone')
        self.assertFalse(arc.exists())
        with self.assertRaises(ValueError):
            self.aplica(dat, undo=True)

    def test_existing_file_restored_exactly(self):
        self.motor.pth_trb.mkdir(mode=0o700)
        arc = self.motor.pth_trb / 'hola.txt'
        arc.write_text('contenido previo\n')
        arc.chmod(0o600)
        dat = self.propone()
        self.aplica(dat)
        self.aplica(dat, undo=True)
        self.assertEqual(arc.read_text(), 'contenido previo\n')

    def test_changed_target_blocks_undo(self):
        dat = self.propone()
        self.aplica(dat)
        arc = self.motor.pth_trb / 'hola.txt'
        arc.write_text('cambio de un técnico')
        with self.assertRaisesRegex(ValueError, 'cambió después'):
            self.aplica(dat, undo=True)
        self.assertEqual(arc.read_text(), 'cambio de un técnico')

    def test_target_change_during_confirmation_aborts_apply(self):
        dat = self.propone()
        previo = self.aplica(dat, dry_run=True)['current']
        self.motor.pth_trb.mkdir(mode=0o700)
        arc = self.motor.pth_trb / 'hola.txt'
        arc.write_text('nuevo cambio')
        arc.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'durante la confirmación'):
            self.aplica(dat, precondicion={'current': previo})
        self.assertEqual(arc.read_text(), 'nuevo cambio')

    def test_socket_cannot_approve_apply_or_undo(self):
        dat = self.propone()
        for op in ('approve', 'apply', 'undo', 'exec', 'shell'):
            with self.subTest(op=op), self.assertRaises(ValueError):
                self.motor.atiende({'op': op, 'id': dat['id']}, os.geteuid())
        self.assertFalse(self.motor.pth_trb.exists())

    def test_real_unix_socket_uses_peer_uid_and_cannot_approve(self):
        try:
            prueba = aux_exec.socket.socket(aux_exec.socket.AF_UNIX, aux_exec.socket.SOCK_STREAM)
        except PermissionError:
            self.skipTest('AF_UNIX creation is prohibited by this runtime; test on the booted ISO')
        else:
            prueba.close()
        ready = threading.Event()
        servidores = []
        base = aux_exec.socketserver.UnixStreamServer
        class PruebaServidor(base):
            def serve_forever(self, *args, **kwargs):
                servidores.append(self)
                ready.set()
                super().serve_forever(*args, **kwargs)
        pth_sock = self.pth / 'control.sock'
        with patch.object(aux_exec.socketserver, 'UnixStreamServer', PruebaServidor), \
             patch.object(aux_exec.grp, 'getgrnam', return_value=SimpleNamespace(gr_gid=os.getgid())), \
             patch.object(aux_exec.os, 'chown'):
            hilo = threading.Thread(target=aux_exec.sirve, args=(self.motor, pth_sock), daemon=True)
            hilo.start()
            self.assertTrue(ready.wait(3))
            try:
                dat = aux_exec.cliente({'op': 'propose', 'plan': plan()}, pth_sock)
                self.assertEqual(dat['owner'], os.geteuid())
                self.assertEqual(dat['status'], 'pending')
                with self.assertRaisesRegex(ValueError, 'aprobación'):
                    aux_exec.cliente({'op': 'approve', 'id': dat['id']}, pth_sock)
                self.assertFalse(self.motor.pth_trb.exists())
                self.assertEqual(pth_sock.stat().st_mode & 0o777, 0o660)
            finally:
                servidores[0].shutdown()
                hilo.join(3)
        self.assertFalse(pth_sock.exists())

    def test_owner_and_digest_are_checked(self):
        dat = self.propone()
        with self.assertRaises(ValueError):
            self.motor.atiende({'op': 'get', 'id': dat['id']}, os.geteuid() + 1)
        with self.assertRaises(ValueError):
            self.motor.aplica(dat['id'], '0' * 64)
        dat['plan']['content'] = 'plan alterado'
        self.motor.guarda(dat)
        with self.assertRaisesRegex(ValueError, 'cambió después'):
            self.aplica(dat)

    def test_expiry_cancel_and_revocation(self):
        dat = self.propone()
        dat['expires'] = time.time() - 1
        self.motor.guarda(dat)
        self.assertEqual(self.motor.lee(dat['id'])['status'], 'expired')
        with self.assertRaises(ValueError):
            self.aplica(dat)
        dat = self.propone()
        self.motor.atiende({'op': 'cancel', 'id': dat['id']}, os.geteuid())
        with self.assertRaises(ValueError):
            self.aplica(dat)
        dat = self.propone()
        (self.motor.pth_est / 'revoked').touch()
        with self.assertRaises(ValueError):
            self.aplica(dat)
        with self.assertRaises(ValueError):
            self.propone()

    def test_symlinks_hardlinks_and_public_files_blocked(self):
        self.motor.pth_trb.mkdir(mode=0o700)
        arc = self.motor.pth_trb / 'hola.txt'
        externo = self.pth / 'other.txt'
        externo.write_text('no tocar')
        externo.chmod(0o600)
        arc.symlink_to(externo)
        with self.assertRaises(OSError):
            self.aplica(self.propone())
        arc.unlink()
        os.link(externo, arc)
        with self.assertRaises(ValueError):
            self.aplica(self.propone())
        arc.unlink()
        arc.write_text('público')
        arc.chmod(0o644)
        with self.assertRaises(ValueError):
            self.aplica(self.propone())
        self.assertEqual(externo.read_text(), 'no tocar')

    def test_validation_blocks_injection_disks_and_secrets(self):
        casos = [plan(action='shell'), plan(action='install_package', target='tmux'),
                 plan(target='../etc/passwd'), plan(target='/dev/sda'), plan(target='run.sh'),
                 plan(content='\x1b[2J'), plan(content='BEGIN PRIVATE KEY'),
                 plan(action='service_state', target='sshd.service', state='active', content=''),
                 plan(action='service_state', target='chronyd.service', state='restart', content=''),
                 plan(action='diagnostic', target='memory; reboot', content='')]
        for dat in casos:
            with self.subTest(dat=dat), self.assertRaises(ValueError):
                self.propone(dat)

    def test_audit_does_not_include_file_content(self):
        dat = self.propone()
        self.aplica(dat)
        audit = (self.motor.pth_est / 'audit.jsonl').read_text()
        self.assertNotIn('Hola', audit)
        self.assertNotIn('Probar una', audit)
        self.assertIn(dat['digest'], audit)
        self.assertEqual((self.motor.pth_est / (dat['id'] + '.json')).stat().st_mode & 0o777, 0o600)

    def test_diagnostic_uses_fixed_argv(self):
        dat = self.propone(plan(action='diagnostic', target='memory', content=''))
        with patch.object(self.motor, 'comando', return_value=(0, 'RAM fixture')) as cmd:
            rsp = self.aplica(dat)
        cmd.assert_called_once_with(['/usr/bin/free', '-h'])
        self.assertEqual(rsp['result'], 'RAM fixture')
        with self.assertRaises(ValueError):
            self.aplica(dat, undo=True)

    def test_service_state_restoration_with_fixture(self):
        dat = self.propone(plan(action='service_state', target='chronyd.service', state='inactive', content=''))
        with patch.object(self.motor, 'estado_servicio', side_effect=['active', 'inactive']), \
             patch.object(self.motor, 'comando', return_value=(0, '')) as cmd:
            self.assertEqual(self.aplica(dat)['status'], 'applied')
            cmd.assert_called_once_with(['/usr/bin/systemctl', 'stop', 'chronyd.service'])
        with patch.object(self.motor, 'estado_servicio', side_effect=['inactive', 'active']), \
             patch.object(self.motor, 'comando', return_value=(0, '')) as cmd:
            self.assertEqual(self.aplica(dat, undo=True)['status'], 'undone')
            cmd.assert_called_once_with(['/usr/bin/systemctl', 'start', 'chronyd.service'])

    def test_failure_is_not_claimed_as_rolled_back(self):
        dat = self.propone()
        with patch.object(self.motor, 'escribe', side_effect=OSError('fixture')):
            rsp = self.aplica(dat)
        self.assertEqual(rsp['status'], 'needs_review')
        self.assertEqual(rsp['before'], {'exists': False})

    def test_undo_request_is_not_execution(self):
        dat = self.propone()
        self.aplica(dat)
        rsp = self.motor.atiende({'op': 'undo_request', 'id': dat['id']}, os.geteuid())
        self.assertTrue(rsp['undo_requested'])
        self.assertEqual(rsp['status'], 'applied')
        self.assertTrue((self.motor.pth_trb / 'hola.txt').exists())


class Proveedores(unittest.TestCase):
    def test_openai_strict_schema_and_no_remote_execution_tool(self):
        _, dat = ai_agent.peticion_agente('openai', 'fixture', [], ai.valida_cfg({}))
        self.assertFalse(dat['store'])
        self.assertFalse(dat['parallel_tool_calls'])
        fun = dat['tools'][0]
        self.assertTrue(fun['strict'])
        self.assertFalse(fun['parameters']['additionalProperties'])
        self.assertEqual(set(fun['parameters']['required']), set(fun['parameters']['properties']))
        self.assertEqual(fun['name'], 'propose_action')

    def test_gemini_signature_and_call_id_survive(self):
        contenido = {'role': 'model', 'parts': [{'functionCall': {
            'name': 'propose_action', 'id': 'fixture-id', 'args': plan()}, 'thoughtSignature': 'opaque-signature'}]}
        sal, llamadas, _ = ai_agent.extrae_turno('gemini', {'candidates': [{'content': contenido}]})
        self.assertEqual(sal, [contenido])
        rsp = ai_agent.salida_herramienta('gemini', llamadas[0], {'status': 'pending'})
        self.assertEqual(rsp['parts'][0]['functionResponse']['id'], 'fixture-id')

    def test_both_providers_only_submit_pending_proposals(self):
        for prov in ('openai', 'gemini'):
            call = {'name': 'propose_action'}
            if prov == 'openai':
                call.update(type='function_call', call_id='call-1', arguments=json.dumps(plan()))
                answers = [{'output': [call]}, {'output': [{'type': 'message', 'content': [
                    {'type': 'output_text', 'text': 'Esperando aprobación local.'}]}]}]
            else:
                call['args'] = plan()
                answers = [{'candidates': [{'content': {'role': 'model', 'parts': [{'functionCall': call}]}}]},
                           {'candidates': [{'content': {'role': 'model', 'parts': [{'text': 'Pendiente.'}]}}]}]
            with patch.object(ai_agent, 'print'), patch('builtins.input', side_effect=AssertionError('No approval prompt allowed here')):
                enviados = []
                def local(req):
                    enviados.append(req)
                    return {'id': 'a' * 24, 'digest': 'b' * 64, 'status': 'pending'}
                ai_agent.turno(prov, 'fixture', 'fixture-key', [], ai.valida_cfg({}),
                               enviar=lambda *a: answers.pop(0), local=local)
            self.assertEqual([ent['op'] for ent in enviados], ['propose'])

    def test_partial_or_multiple_calls_are_rejected(self):
        with self.assertRaises(ValueError):
            ai_agent.extrae_turno('openai', {'status': 'incomplete', 'output': []})
        with self.assertRaises(ValueError):
            ai_agent.extrae_turno('gemini', {'candidates': [{'finishReason': 'MAX_TOKENS'}]})
        with self.assertRaises(ValueError):
            ai_agent.llamada('gemini', {'name': 'execute', 'args': plan()})


if __name__ == '__main__':
    unittest.main()
