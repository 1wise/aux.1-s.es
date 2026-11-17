#!/usr/bin/env python3
# Timestamp: 2026-10-13 | Version: 5.0.7
# Author & Credits: https://www.alawise.es/1-s
"""Exercise the combined vhosts on temporary ports/files with a temporary certificate."""
import argparse
import http.client
import os
from pathlib import Path
import pwd
import socket
import ssl
import subprocess
import tempfile
import time


def puerto():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    arg = argparse.ArgumentParser(description=__doc__)
    arg.add_argument('--nginx', default='nginx')
    arg.add_argument('--config-dir', default='/etc/nginx')
    arg.add_argument('--template', type=Path, default=Path(__file__).with_name('aux-pxe-tec.conf.example'))
    cfg = arg.parse_args()
    conf_base = cfg.template.read_text()
    with tempfile.TemporaryDirectory(prefix='aux-nginx-') as tmp:
        pth = Path(tmp)
        for nom in ('html', 'web'):
            (pth / nom).mkdir(mode=0o755)
            (pth / nom / 'probe.txt').write_text(nom)
        (pth / 'html/index.html').write_text('AUX_INDEX')
        (pth / 'html/cli.html').write_text('PXE_INDEX')
        (pth / 'html/assets').mkdir()
        (pth / 'html/assets/portal.css').write_text('body { color: green; }')
        (pth / 'html/assets/portal.js').write_text('console.log("ok");')
        (pth / 'html/menu.ipxe').write_text('#!ipxe\necho ok\n')
        (pth / 'html/fedora').mkdir()
        (pth / 'html/fedora/.treeinfo').write_text('[stage2]\nmainimage=images/install.img\n')
        (pth / 'html/.secret').write_text('private')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                        '-subj', '/CN=localhost', '-days', '1', '-keyout', str(pth / 'key.pem'),
                        '-out', str(pth / 'cert.pem')], check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        pt_http, pt_tls = puerto(), puerto()
        conf = conf_base.replace('listen 80;', f'listen 127.0.0.1:{pt_http};')
        conf = conf.replace('listen [::]:80;', '').replace('listen [::]:443 ssl;', '')
        conf = conf.replace('listen 443 ssl;', f'listen 127.0.0.1:{pt_tls} ssl;')
        conf = conf.replace('/var/www/aux.1-s.es', str(pth))
        conf = conf.replace('/etc/letsencrypt/live/ntp1.1-s.eu/fullchain.pem', str(pth / 'cert.pem'))
        conf = conf.replace('/etc/letsencrypt/live/ntp1.1-s.eu/privkey.pem', str(pth / 'key.pem'))
        conf = conf.replace('/var/log/nginx', str(pth))
        conf = conf.replace('/etc/nginx/mime.types', str(Path(cfg.config_dir) / 'mime.types'))
        conf = conf.replace('include fastcgi_params;', 'include ' + str(Path(cfg.config_dir) / 'fastcgi_params') + ';')
        arc_conf = pth / 'nginx.conf'
        # Current uid permits private temporary roots without changing their ownership.
        temp_paths = ' '.join(nom + ' ' + str(pth / nom) + ';' for nom in
                              ('client_body_temp_path', 'proxy_temp_path', 'fastcgi_temp_path', 'uwsgi_temp_path', 'scgi_temp_path'))
        user = pwd.getpwuid(os.getuid()).pw_name
        arc_conf.write_text(f'user {user}; daemon off; master_process off; pid {pth}/nginx.pid; error_log stderr; events {{ }} http {{ access_log off; {temp_paths} {conf} }}')
        cmd = [cfg.nginx, '-p', str(pth), '-c', str(arc_conf)]
        syntax = subprocess.run(cmd + ['-t'], capture_output=True, text=True)
        if syntax.returncode:
            raise RuntimeError(syntax.stderr)
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                try:
                    with socket.create_connection(('127.0.0.1', pt_http), timeout=.1):
                        break
                except OSError:
                    time.sleep(.05)
            ctx = ssl._create_unverified_context()  # Temporary self-signed fixture only.
            def fetch(host, path, tls=False):
                con = http.client.HTTPSConnection('127.0.0.1', pt_tls, context=ctx) if tls else http.client.HTTPConnection('127.0.0.1', pt_http)
                con.request('GET', path, headers={'Host': host})
                res = con.getresponse()
                ret = res.status, res.getheader('Content-Type', ''), res.read(), res.getheader('Location')
                con.close()
                return ret
            for host in ('aux.1-s.es', 'aux.1-s.eu', 'pxe.1-s.es', 'pxe.1-s.eu'):
                for tls in (False, True):
                    expected = b'AUX_INDEX' if host.startswith('aux.') else b'PXE_INDEX'
                    assert fetch(host, '/', tls)[2] == expected, (host, tls, 'index')
                    assert fetch(host, '/assets/portal.css', tls)[:2] == (200, 'text/css')
                    assert fetch(host, '/assets/portal.js', tls)[0] == 200
                    assert fetch(host, '/menu.ipxe', tls)[:2] == (200, 'text/plain')
                    assert fetch(host, '/fedora/.treeinfo', tls)[0] == 200
                    assert fetch(host, '/.secret', tls)[0] == 403
            for host in ('tec.1-s.es', 'tec.1-s.eu'):
                assert fetch(host, '/')[0::3] == (308, 'https://tec.1-s.es/'), host
                assert fetch(host, '/probe.txt', True)[2] == b'web'
                assert fetch(host, '/manage.php', True)[0] == 404
            assert fetch('aux.1-s.es', '/assist/profiles.php')[3] == 'https://tec.1-s.es/profiles.php'
            print('PASS: six names, AUX/PXE HTTP+HTTPS, TEC redirect/webroot, CSS/iPXE MIME, public tree metadata and private paths')
        finally:
            proc.terminate()
            proc.communicate(timeout=5)


if __name__ == '__main__':
    main()
