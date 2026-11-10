#!/usr/bin/env python3
# Timestamp: 2026-10-13 | Version: 5.1.0
# Author & Credits: https://www.alawise.es/1-s
"""Exercise central settings and actual PHP host routing without a browser."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
from unittest.mock import patch


def main():
    par = argparse.ArgumentParser()
    par.add_argument('--php', default='php')
    args = par.parse_args()
    pth_app = Path(__file__).resolve().parent
    arc_gen = pth_app / 'generate.sh'
    body = arc_gen.read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
    eng = ModuleType('gen_routing')
    eng.__file__ = str(arc_gen)
    exec(compile(body, str(arc_gen), 'exec'), eng.__dict__)
    eng.carga_recursos()
    with tempfile.TemporaryDirectory(prefix='aux-routing-') as tmp:
        pth = Path(tmp)
        cfg_dat = json.loads((pth_app / 'fast-boot.json').read_text())
        cfg_dat['output'], cfg_dat['cache'] = str(pth / 'html'), str(pth / 'cache')
        cfg_dat['tec']['public_url'] = 'https://people.example.test'
        cfg_dat['tec']['web_dir'] = str(pth_app / 'tec/web')
        cfg_dat['boot']['assist_timeout_seconds'] = 17
        cfg_dat['bastion']['cli_hosts'] = ['p.example.test']
        arc_cfg = pth / 'fast-boot.json'
        arc_cfg.write_text(json.dumps(cfg_dat))
        with patch('sys.argv', ['generate.sh', '--config', str(arc_cfg)]):
            cfg = eng.obt_args('generate', pth_app)
        eng.gen_pages([], cfg, state='source')
        for name in ['index.html', 'cli.html']:
            assert 'people.example.test' in (cfg.output / name).read_text()
            assert 'CC BY-NC-SA 4.0' in (cfg.output / name).read_text()
            assert 'PXE&gt;' in (cfg.output / name).read_text()
        def run_host(host):
            code = '$_SERVER["HTTP_HOST"]=$argv[1]; include $argv[2];'
            return subprocess.run([args.php, '-n', '-r', code, host, str(cfg.output / 'index.php')],
                                  capture_output=True, text=True, check=True).stdout
        assert run_host('P.EXAMPLE.TEST:443') == (cfg.output / 'cli.html').read_text()
        for host in ['b.example.test', 'p.example.test.attacker.test', 'p.1-s.es']:
            assert run_host(host) != (cfg.output / 'cli.html').read_text()
        rec = eng.obt_meta('https://example.test/aux-rescue-5.1.0-x86_64.iso')
        rec.update(assistance_boot=True, _boot={'commands': ['echo test'], 'firmware': None, 'group': 'tools'})
        assert 'set auto_timeout 17000' in eng.gen_ipxe([rec], cfg)
        pool = (cfg.output / 'downloads/tec/php-fpm.conf.example').read_text()
        assert 'env[AUX_ASSIST_CONFIG]' in pool and 'env[AUX_ASSIST_PUBLIC_URL]' not in pool
        cfg_dat['boot']['assist_timeout_seconds'] = 'invalid'
        arc_cfg.write_text(json.dumps(cfg_dat))
        with patch('sys.argv', ['generate.sh', '--config', str(arc_cfg)]):
            try:
                eng.obt_args('generate', pth_app)
                raise AssertionError('Invalid timeout accepted')
            except SystemExit as exc:
                assert exc.code == 2
    print('PASS: central URLs, license, timeout, pool config and actual PHP Bastion host routing')


if __name__ == '__main__':
    main()
