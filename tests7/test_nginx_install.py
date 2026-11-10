# Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
# Author & Credits: https://www.alawise.es/1-s
"""Reject conflicting active CLI zones before the installer mutates the server."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('aux_install_web', RAIZ / 'install-web.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class InstalacionNginx(unittest.TestCase):
    def test_active_legacy_zone_is_reported(self):
        txt = '''# configuration file /etc/nginx/nginx.conf:
http { include /etc/nginx/conf.d/*.conf; }
# configuration file /etc/nginx/conf.d/cli.1-s.es.conf:
limit_req_zone $aux_pair_key
    zone=aux_pair:1m rate=6r/m;
'''
        self.assertEqual(web.zonas_externas(txt,Path('/etc/nginx/conf.d/aux-cli.conf')),
                         ['/etc/nginx/conf.d/cli.1-s.es.conf'])

    def test_managed_zone_other_names_and_comments_are_accepted(self):
        txt = '''# configuration file /etc/nginx/nginx.conf:
http { include /etc/nginx/conf.d/*.conf; }
# configuration file /etc/nginx/conf.d/aux-cli.conf:
limit_req_zone $aux_pair_key zone=aux_pair:1m rate=6r/m;
# configuration file /etc/nginx/conf.d/other.conf:
# limit_req_zone $aux_pair_key zone=aux_pair:1m rate=6r/m;
limit_req_zone $binary_remote_addr zone=other:1m rate=1r/s;
'''
        self.assertEqual(web.zonas_externas(txt,Path('/etc/nginx/conf.d/aux-cli.conf')),[])

    def test_native_nginx_failure_aborts(self):
        res = subprocess.CompletedProcess(['nginx','-T'],1,'','aux_pair is already bound')
        with patch.object(web.subprocess,'run',return_value=res), self.assertRaisesRegex(ValueError,'aux_pair'):
            web.comprueba_nginx()

    def test_existing_valid_legacy_config_blocks_a_second_zone(self):
        txt = '# configuration file /etc/nginx/conf.d/cli.1-s.es.conf:\nlimit_req_zone $aux_pair_key zone=aux_pair:1m rate=6r/m;\n'
        res = subprocess.CompletedProcess(['nginx','-T'],0,txt,'syntax is ok')
        with patch.object(web.subprocess,'run',return_value=res), self.assertRaisesRegex(ValueError,'cli.1-s.es.conf'):
            web.comprueba_nginx()

    def test_guard_runs_before_server_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp)/'server'
            with patch.object(web.os,'geteuid',return_value=0), \
                 patch.object(web.shutil,'which',return_value='/test/tool'), \
                 patch.object(web,'comprueba_nginx',side_effect=ValueError('legacy zone')), \
                 patch.object(web,'usuario') as usr:
                with self.assertRaisesRegex(ValueError,'legacy zone'):
                    web.instala(RAIZ,dst,True)
                usr.assert_not_called()
                self.assertFalse(dst.exists())


if __name__ == '__main__':
    unittest.main()
