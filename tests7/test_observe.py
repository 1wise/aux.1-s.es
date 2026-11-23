# Timestamp: 2026-11-22 | Version: 8.0.0-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Check observation boundaries with isolated process and HTTPS fixtures."""
import contextlib
import io
import json
from pathlib import Path
import ssl
import stat
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from auxlib import observe as obs


class ObservacionLocal(unittest.TestCase):
    def test_schema_precedes_every_select_and_limit_is_bounded(self):
        with patch.object(obs, 'osquery', side_effect=[[{'name': 'hostname'}], [{'hostname': 'fixture'}]]) as query:
            res = obs.consulta_local('system', 12)
        self.assertEqual(query.call_args_list[0].args, ('PRAGMA table_info(system_info);',))
        self.assertEqual(query.call_args_list[1].args, ('SELECT * FROM system_info LIMIT 12;',))
        self.assertEqual(res['rows'], [{'hostname': 'fixture'}])

    def test_missing_table_does_not_issue_select(self):
        with patch.object(obs, 'osquery', return_value=[]) as query, self.assertRaises(ValueError):
            obs.consulta_local('rpm')
        self.assertEqual(query.call_count, 1)

    def test_operator_cannot_pass_sql_as_a_table_or_exceed_the_limit(self):
        for nom, limite in [('system; DROP TABLE x', 1), ('system', 1001), ('system', 0)]:
            with self.subTest(query=nom, limit=limite), self.assertRaises(ValueError):
                obs.consulta_local(nom, limite)

    def test_api_rejects_plaintext_credentials_and_ambiguous_bases(self):
        for url in ('http://example.org', 'https://token@example.org', 'https://example.org?token=x', 'https://example.org/path'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                obs.url_api(url)


class Enrolamiento(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.end = self.root / 'endpoints.json'
        self.end.write_text(json.dumps({nom: '/environment/' + str(n) for n, nom in enumerate(obs.ENDPOINTS)}))
        self.ca = self.root / 'ca.pem'
        self.ca.write_text('fixture CA path')
        self.out = self.root / 'private-agent'

    def tearDown(self):
        self.tmp.cleanup()

    def prepara(self, apply=False):
        return obs.prepara_enrolamiento('tls.example.org:9443', self.end, self.ca,
            '/etc/osquery/enroll.secret', self.out, apply)

    def test_plan_has_no_side_effects_and_does_not_read_enrollment_secret(self):
        plan = self.prepara()
        self.assertFalse(self.out.exists())
        self.assertIn('--distributed_plugin=tls', plan['flags'])
        self.assertIn('--enroll_secret_path=/etc/osquery/enroll.secret', plan['flags'])

    def test_apply_creates_private_flags_once_without_starting_a_service(self):
        with patch.object(obs.subprocess, 'run') as run:
            self.prepara(True)
        run.assert_not_called()
        self.assertEqual(stat.S_IMODE(self.out.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.out / 'osquery.flags').stat().st_mode), 0o600)
        with self.assertRaises(ValueError):
            self.prepara(True)

    def test_missing_or_redirecting_endpoints_are_rejected(self):
        for dat in ({}, {nom: '//other.example/path' for nom in obs.ENDPOINTS}):
            self.end.write_text(json.dumps(dat))
            with self.assertRaises(ValueError):
                self.prepara()


class ApiHttps(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.cert = root / 'cert.pem'
        key = root / 'key.pem'
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(key), '-out', str(cls.cert), '-days', '1',
            '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1'],
            check=True, capture_output=True)
        cls.seen = []
        cls.mode = 'ok'

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                cls.seen.append((self.path, self.headers.get('Authorization')))
                if cls.mode == 'redirect':
                    self.send_response(302)
                    self.send_header('Location', cls.url + '/must-not-receive-token')
                    self.end_headers()
                    return
                if cls.mode == 'unauthorized':
                    self.send_response(401)
                    self.end_headers()
                    self.wfile.write(b'fixture-secret-do-not-print')
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'[{"name":"fixture","enroll_secret":"private-value"}]')

        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cls.cert, key)
        cls.server.socket = tls.wrap_socket(cls.server.socket, server_side=True)
        cls.url = 'https://127.0.0.1:' + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def setUp(self):
        type(self).mode = 'ok'
        self.seen.clear()
        ctx = ssl.create_default_context(cafile=str(self.cert))
        self.tls = patch.object(obs.ssl, 'create_default_context', return_value=ctx)
        self.tls.start()
        self.addCleanup(self.tls.stop)

    def test_https_read_auth_and_redaction(self):
        result = obs.consulta_api(self.url, 'fixture-token', 'environments')
        self.assertEqual(self.seen, [('/api/v1/environments', 'Bearer fixture-token')])
        self.assertEqual(result['data'][0]['enroll_secret'], '[oculto]')

    def test_redirect_does_not_forward_token(self):
        type(self).mode = 'redirect'
        with self.assertRaisesRegex(ValueError, 'redirige'):
            obs.consulta_api(self.url, 'fixture-token', 'environments')
        self.assertEqual(len(self.seen), 1)

    def test_auth_failure_does_not_include_response_body_or_token(self):
        type(self).mode = 'unauthorized'
        with self.assertRaises(ValueError) as error:
            obs.consulta_api(self.url, 'fixture-token', 'environments')
        self.assertNotIn('fixture', str(error.exception))

    def test_result_endpoint_uses_explicit_page_and_size(self):
        obs.consulta_api(self.url, 'fixture-token', 'results', 'lab', 'inventory', 2, 25)
        self.assertEqual(self.seen[0][0], '/api/v1/queries/lab/results/inventory?page=2&page_size=25')


if __name__ == '__main__':
    unittest.main()
