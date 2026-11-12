# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Check delegated image redirects, retained host restrictions and header-only probes."""
import socket
import unittest
from unittest.mock import patch,Mock
import urllib.request

from auxlib import catalog, catalog_mirrors as espejos, catalog_downloads as desc


class EspejosCatalogo(unittest.TestCase):
    url='https://download.fedoraproject.org/pub/fedora/image.iso'
    espejo='https://mirror.cpsc.ucalgary.ca/mirror/fedora/image.iso'

    def direcciones(self,ips=('8.8.8.8',)):
        return [(socket.AF_INET6 if ':' in ip else socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ips]

    def test_public_provider_selected_mirror_keeps_the_head_method(self):
        redir=espejos.RedireccionDescarga(['download.fedoraproject.org'],self.url,['download.fedoraproject.org'])
        req=urllib.request.Request(self.url,method='HEAD')
        with patch.object(espejos.socket,'getaddrinfo',return_value=self.direcciones()):
            nueva=redir.redirect_request(req,None,302,'Found',{},self.espejo)
        self.assertEqual(nueva.get_method(),'HEAD')
        self.assertEqual(nueva.full_url,self.espejo)

    def test_unconfigured_origin_cannot_delegate_download_requests(self):
        for origen in ('https://example.org/image.iso',self.url):
            hosts=['example.org'] if 'example.org' in origen else ['download.fedoraproject.org']
            redir=espejos.RedireccionDescarga(hosts,origen,['cdimage.kali.org'])
            with self.assertRaises(ValueError):
                redir.redirect_request(urllib.request.Request(origen,method='HEAD'),None,302,'Found',{},self.espejo)

    def test_configured_non_delegated_image_redirect_keeps_head(self):
        redir=espejos.RedireccionDescarga(['download.fedoraproject.org','mirror.cpsc.ucalgary.ca'],self.url)
        nueva=redir.redirect_request(urllib.request.Request(self.url,method='HEAD'),None,302,'Found',{},self.espejo)
        self.assertEqual(nueva.get_method(),'HEAD')

    def test_private_loopback_link_local_and_mixed_dns_results_are_rejected(self):
        for ips in [('127.0.0.1',),('10.42.0.42',),('169.254.169.254',),('::1',),('fe80::1',),('224.0.0.1',),('ff02::1',),('8.8.8.8','192.168.1.1')]:
            with self.subTest(ips=ips),patch.object(espejos.socket,'getaddrinfo',return_value=self.direcciones(ips)),self.assertRaises(ValueError):
                espejos.valida_espejo(self.espejo)

    def test_plain_http_and_embedded_credentials_are_rejected(self):
        for url in ('http://mirror.example.org/image.iso','https://user:pass@mirror.example.org/image.iso'):
            with self.assertRaises(ValueError):espejos.valida_espejo(url)

    def test_metadata_redirects_still_require_configured_hosts(self):
        redir=catalog.Redireccion(['download.fedoraproject.org'])
        with self.assertRaises(ValueError):
            redir.redirect_request(urllib.request.Request(self.url),None,302,'Found',{},self.espejo)

    def test_ipv6_public_mirror_and_missing_dns_answers(self):
        with patch.object(espejos.socket,'getaddrinfo',return_value=self.direcciones(('2606:4700:4700::1111',))):
            espejos.valida_espejo(self.espejo)
        with patch.object(espejos.socket,'getaddrinfo',return_value=[]),self.assertRaises(ValueError):
            espejos.valida_espejo(self.espejo)

    def test_probe_reports_delegated_policy_without_reading_an_image(self):
        class Respuesta:
            headers={'Content-Length':'100'}
            url='https://kali.mirror.rafal.ca/image.iso'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):raise AssertionError('The crawler must not read an image body.')
        abridor=Mock();abridor.open.return_value=Respuesta()
        with patch.object(desc.urllib.request,'build_opener',return_value=abridor):
            dat=desc.comprueba_enlace('https://cdimage.kali.org/image.iso',['cdimage.kali.org'],100,['cdimage.kali.org'])
        self.assertEqual(dat['redirect_policy'],'provider-delegated-https')
        self.assertEqual(dat['size_bytes'],100)


if __name__=='__main__':unittest.main()
