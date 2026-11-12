# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Exercise task review, refreshed URL selection and remote iPXE menu boundaries."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from auxlib import catalog, catalog_workflow as flujo, task_ui, remote_menu, localtools
from test_catalog_console import Pantalla, entrada
import curses


class FlujoDespliegue(unittest.TestCase):
    def test_gentoo_reads_the_latest_pointer_size_and_official_checksum(self):
        fuente={'id':'gentoo','url':'https://distfiles.gentoo.org/current/latest.txt',
                'allowed_hosts':['distfiles.gentoo.org'],'format':'gentoo-latest',
                'pattern':r'install-(?P<release>[0-9]+)\.iso',
                'defaults':{'family':'gentoo','architecture':'x86_64','kind':'installer','download_class':'light'}}
        def traer(url,*args):
            return b'install-20261108.iso 1024\n' if url.endswith('latest.txt') else ('a'*64+'  install-20261108.iso\n').encode()
        ent=catalog.descubre(fuente,Path('/unused'),traer)[0]
        self.assertEqual((ent['release'],ent['size_bytes'],ent['sha256']),('20261108',1024,'a'*64))
        self.assertEqual(ent['original_url'],'https://distfiles.gentoo.org/current/install-20261108.iso')
        with self.assertRaises(ValueError):catalog.descubre(fuente,Path('/unused'),lambda *args:b'bad latest file')

    def test_crawl_is_accessible_from_the_catalogue_without_exporting_selection(self):
        scr=Pantalla([curses.KEY_F5])
        accion=localtools.seleccion_catalogo(scr,[entrada('one','light',1024)])
        self.assertEqual(accion['action'],'crawl')
        self.assertTrue(any('Rastrear / actualizar' in txt for txt in scr.textos))

    def test_list_review_is_read_only_and_apply_retains_recovery_copies(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)
            config=raiz/'sources.json'; cat=raiz/'catalog.json'
            config.write_text(json.dumps({'sync_rules':[{'source_id':'gentoo','url_pattern':r'https://example.org/old\.iso'}]}))
            cat.write_text(json.dumps({'entries':[{'source_id':'gentoo','original_url':'https://example.org/new.iso'}]}))
            for nom in ('url.txt','light-url.txt','heavy-url.txt'): (raiz/nom).write_text('https://example.org/old.iso\n')
            cambios=flujo.plan_listas(config,cat,raiz)
            self.assertEqual((raiz/'url.txt').read_text(),'https://example.org/old.iso\n')
            flujo.aplica_listas(cambios)
            self.assertEqual((raiz/'url.txt').read_text(),'https://example.org/new.iso\n')
            self.assertEqual((raiz/'url.txt.before-crawl').read_text(),'https://example.org/old.iso\n')

    def test_cancel_after_review_only_runs_the_real_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(task_ui.sys.stdin,'isatty',return_value=True), \
             patch.object(task_ui.sys.stdout,'isatty',return_value=True), \
             patch.object(task_ui,'elige',side_effect=['review','exit']), \
             patch.object(task_ui,'campo',return_value=''), \
             patch.object(task_ui.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'plan\n','')) as run, \
             self.assertRaises(KeyboardInterrupt):
            task_ui.prepara_tarea('deploy',Path(tmp),['-i','disk','--mode','mount'])
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.args[0][-1],'--dry-run')
        self.assertIn('mount',run.call_args.args[0])

    def test_forced_dry_run_cannot_become_execution(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(task_ui.sys.stdin,'isatty',return_value=True), \
             patch.object(task_ui.sys.stdout,'isatty',return_value=True), \
             patch.object(task_ui,'elige',return_value='review'), \
             patch.object(task_ui,'campo',return_value='EJECUTAR'), \
             patch.object(task_ui.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'plan','')):
            args=task_ui.prepara_tarea('download',Path(tmp),['--interactive','--dry-run'])
        self.assertIn('--dry-run',args)

    def test_execution_requires_review_and_exact_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(task_ui.sys.stdin,'isatty',return_value=True), \
             patch.object(task_ui.sys.stdout,'isatty',return_value=True), \
             patch.object(task_ui,'elige',return_value='review'), \
             patch.object(task_ui,'campo',return_value='EJECUTAR'), \
             patch.object(task_ui.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'plan','')) as run:
            args=task_ui.prepara_tarea('download',Path(tmp),['-i','--list','heavy','--jobs','2'])
        self.assertNotIn('-i',args)
        self.assertEqual(args[args.index('--list')+1],'heavy')
        self.assertEqual(args[args.index('--jobs')+1],'2')
        self.assertEqual(run.call_args.args[0][-1],'--dry-run')

    def test_remote_menus_initialize_provider_and_never_chain_plain_images(self):
        ent=entrada('debian','light',remote=True)
        ent['original_url']='https://boot.netboot.xyz/debian.ipxe'
        img=entrada('other','heavy'); img['original_url']='https://example.org/disk.iso'
        malicious=dict(img,original_url='https://example.org/${target}.iso')
        txt='\n'.join(remote_menu.menu_origen([ent,dict(ent,release='other'),img,malicious]))
        self.assertEqual(txt.count('chain --autofree https://boot.netboot.xyz/debian.ipxe'),1)
        self.assertIn('set menu debian',txt)
        self.assertLess(txt.index('chain --autofree https://boot.netboot.xyz/boot.cfg'),txt.index('set menu debian'))
        self.assertIn('echo https://example.org/disk.iso',txt)
        self.assertNotIn('chain --autofree https://example.org/disk.iso',txt)
        self.assertNotIn('${target}.iso',txt)

    def test_three_shell_commands_advertise_both_interactive_flags(self):
        raiz=Path(__file__).resolve().parents[1]
        for nom in ('download','deploy','generate'):
            rsp=subprocess.run(['bash',str(raiz/(nom+'.sh')),'--help'],capture_output=True,text=True)
            self.assertEqual(rsp.returncode,0,rsp.stderr)
            self.assertIn('-i, --interactive',rsp.stdout)


if __name__=='__main__':unittest.main()
