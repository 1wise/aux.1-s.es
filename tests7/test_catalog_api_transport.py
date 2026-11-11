# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Check bounded, secret-redacting API transport and delegated Kali checksum metadata."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
import urllib.error

from auxlib import catalog,catalog_downloads,catalog_api_transport as api,catalog_mirrors


class TransporteYCandidatos(unittest.TestCase):
    def test_transport_uses_provider_headers_and_keeps_keys_out_of_urls(self):
        class Respuesta:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'{"ok":true}'
        abridor=Mock();abridor.open.return_value=Respuesta()
        with patch.object(api.urllib.request,'build_opener',return_value=abridor):
            api.consulta_raw('openai','synthetic-key','https://api.openai.com/v1/responses',{'model':'test'},{'timeout_seconds':10})
            req=abridor.open.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'),'Bearer synthetic-key')
            self.assertNotIn('synthetic-key',req.full_url)
            api.consulta_raw('gemini','synthetic-key','https://generativelanguage.googleapis.com/v1beta/models/test:generateContent',{}, {'timeout_seconds':10})
            self.assertEqual(abridor.open.call_args.args[0].get_header('X-goog-api-key'),'synthetic-key')

    def test_api_errors_do_not_echo_keys_or_retry_paid_calls(self):
        abridor=Mock();abridor.open.side_effect=urllib.error.HTTPError('https://api.openai.com',401,'synthetic-key was refused',None,None)
        with patch.object(api.urllib.request,'build_opener',return_value=abridor),self.assertRaises(RuntimeError) as err:
            api.consulta_raw('openai','synthetic-key','https://api.openai.com/v1/responses',{}, {'timeout_seconds':10})
        self.assertNotIn('synthetic-key',str(err.exception));self.assertEqual(abridor.open.call_count,1)
        self.assertIsNone(api.SinRedireccion().redirect_request(None,None,302,'Found',{},'https://elsewhere.example/'))

    def test_kali_checksum_request_uses_download_redirect_policy_only_for_the_manifest(self):
        fuente={'id':'kali','format':'artifact-html','url':'https://cdimage.kali.org/current/',
                'checksums_url':'https://cdimage.kali.org/current/SHA256SUMS',
                'allowed_hosts':['cdimage.kali.org'],'mirror_redirect_origins':['cdimage.kali.org']}
        llamadas=[]
        def traer(url,*args):
            llamadas.append((url,args))
            return ('a'*64+'  kali-linux-2026.3-installer-amd64.iso\n').encode() if url.endswith('SHA256SUMS') else b'<a href="kali-linux-2026.3-installer-amd64.iso">ISO</a>'
        ents=catalog_downloads.candidatos(fuente,Path('/unused'),traer)
        self.assertEqual(ents[0]['sha256'],'a'*64)
        self.assertEqual(len(llamadas[0][1]),2)
        self.assertEqual(llamadas[1][1][-1],['cdimage.kali.org'])

    def test_small_checksum_get_can_follow_an_explicit_provider_delegation(self):
        class Respuesta:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return ('a'*64+'  image.iso\n').encode()
        abridor=Mock();abridor.open.return_value=Respuesta()
        with tempfile.TemporaryDirectory() as tmp,patch.object(catalog.urllib.request,'build_opener',return_value=abridor) as opener:
            body=catalog.consulta('https://cdimage.kali.org/current/SHA256SUMS',['cdimage.kali.org'],Path(tmp),8388608,['cdimage.kali.org'])
            handler=opener.call_args.args[0]
            self.assertIsInstance(handler,catalog_mirrors.RedireccionDescarga);self.assertTrue(handler.delegada)
            self.assertEqual(abridor.open.call_args.args[0].get_method(),'GET')
            self.assertIn(b'image.iso',body)

    def test_default_metadata_reads_retain_the_strict_host_handler(self):
        class Respuesta:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'{}'
        abridor=Mock();abridor.open.return_value=Respuesta()
        with tempfile.TemporaryDirectory() as tmp,patch.object(catalog.urllib.request,'build_opener',return_value=abridor) as opener:
            catalog.consulta('https://example.org/index.json',['example.org'],Path(tmp))
            self.assertIs(type(opener.call_args.args[0]),catalog.Redireccion)


if __name__=='__main__':unittest.main()
