# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Honor a provider's download redirects without relaxing metadata host checks."""
import ipaddress
import socket
import urllib.parse
import urllib.request

from .catalog import Redireccion, url_segura


def valida_espejo(url):
    url_segura(url)
    host=urllib.parse.urlsplit(url).hostname
    puerto=urllib.parse.urlsplit(url).port or 443
    destinos=socket.getaddrinfo(host,puerto,type=socket.SOCK_STREAM)
    ips=[ipaddress.ip_address(ent[4][0]) for ent in destinos]
    if not ips or any(not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified for ip in ips):
        raise ValueError('La redirección de descarga requiere un destino HTTPS público: '+host)


class RedireccionDescarga(Redireccion):
    def __init__(self,hosts,url,origenes=()):
        super().__init__(hosts)
        # Only an explicitly configured redirector can delegate this image request.
        url_segura(url,hosts)
        self.delegada=urllib.parse.urlsplit(url).hostname in origenes

    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not self.delegada:
            nueva=super().redirect_request(req,fp,code,msg,headers,newurl)
        else:
            valida_espejo(newurl)
            nueva=urllib.request.HTTPRedirectHandler.redirect_request(self,req,fp,code,msg,headers,newurl)
        # urllib otherwise changes redirected HEAD requests into ordinary GET requests.
        if nueva is not None and req.get_method()=='HEAD':nueva.method='HEAD'
        return nueva
