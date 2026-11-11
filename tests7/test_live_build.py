# Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Exercise Live build boundaries and prevent legacy clients becoming defaults."""
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from build import motor
from auxlib import setup

RAIZ=Path(__file__).resolve().parents[1]


def carga(nom):
    spec=importlib.util.spec_from_file_location('live_'+nom,RAIZ/'iso-assist'/(nom+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod


class ConstruccionLive(unittest.TestCase):
    def lector_iso(self,txt,nom='.discinfo',etiqueta='Fedora-S-dvd-x86_64-45',canal='stderr'):
        def run(cmd,**kwargs):
            if '-ls' in cmd:
                lista="'"+nom+"'\n'EFI'\n'images'\n"
                etq="Volume id    : '"+etiqueta+"'\n"
                return subprocess.CompletedProcess(cmd,0,lista+(etq if canal=='stdout' else ''),
                    etq if canal=='stderr' else '')
            self.assertIn('-extract',cmd)
            self.assertEqual(cmd[-2],'/'+nom)
            Path(cmd[-1]).write_text(txt)
            return subprocess.CompletedProcess(cmd,0,'','')
        return run

    def test_netinst_with_discinfo_and_no_treeinfo_is_identified(self):
        mod=carga('build')
        for rel in ('45','Fedora 45','Fedora-Server 45','Fedora Linux 45'):
            for canal in ('stdout','stderr'):
                with self.subTest(description=rel,stream=canal),patch.object(mod.subprocess,'run',
                        side_effect=self.lector_iso('1762000000.000000\n'+rel+'\nx86_64\n',canal=canal)) as run:
                    self.assertEqual(mod.datos_iso(Path('/fixture/netinst.iso')),('45','x86_64'))
                    self.assertEqual(run.call_count,2)
                    self.assertNotIn('/.treeinfo',str(run.call_args_list))

    def test_treeinfo_metadata_remains_supported(self):
        mod=carga('build')
        with patch.object(mod.subprocess,'run',side_effect=self.lector_iso(
                '[general]\nversion=45\narch=x86_64\n','.treeinfo')):
            self.assertEqual(mod.datos_iso(Path('/fixture/tree.iso')),('45','x86_64'))

    def test_wrong_release_or_architecture_is_not_inferred_from_filename(self):
        mod=carga('build')
        for rel,arq in (('44','x86_64'),('45','aarch64')):
            with self.subTest(release=rel,architecture=arq),patch.object(mod.subprocess,'run',
                    side_effect=self.lector_iso('1762000000\nFedora '+rel+'\n'+arq+'\n',
                    etiqueta='Fedora-S-dvd-'+arq+'-'+rel)):
                self.assertEqual(mod.datos_iso(Path('/fixture/Fedora-45-x86_64.iso')),(rel,arq))

    def test_discinfo_conflict_and_truncated_or_unrecognizable_metadata_fail(self):
        mod=carga('build')
        casos=[('1762000000\n45\naarch64\n','Fedora-S-dvd-x86_64-45'),
               ('1762000000\n44\nx86_64\n','Fedora-S-dvd-x86_64-45'),
               ('1762000000\n45\n','Fedora-S-dvd-x86_64-45'),
               ('1762000000\nOther Linux\nx86_64\n','UNKNOWN'),
               ('x'*17000,'Fedora-S-dvd-x86_64-45')]
        for txt,etq in casos:
            with self.subTest(metadata=txt[:40]),patch.object(mod.subprocess,'run',
                    side_effect=self.lector_iso(txt,etiqueta=etq)),self.assertRaises(ValueError):
                mod.datos_iso(Path('/fixture/netinst.iso'))

    def test_xorriso_error_preserves_the_actual_diagnostic(self):
        mod=carga('build')
        with patch.object(mod.subprocess,'run',return_value=subprocess.CompletedProcess([],5,'',
                'xorriso : FAILURE : Cannot read ISO: Permission denied\n')):
            with self.assertRaisesRegex(ValueError,'Permission denied'):
                mod.datos_iso(Path('/fixture/netinst.iso'))

    def test_missing_both_metadata_formats_is_reported(self):
        mod=carga('build')
        with patch.object(mod.subprocess,'run',return_value=subprocess.CompletedProcess([],0,"'EFI'\n'images'\n",'')):
            with self.assertRaisesRegex(ValueError,'no contiene .discinfo ni .treeinfo'):
                mod.datos_iso(Path('/fixture/netinst.iso'))

    def test_vm_plan_preserves_host_and_checks_installer_identity(self):
        mod=carga('build')
        with tempfile.TemporaryDirectory() as tmp,ExitStack() as ctx:
            pth=Path(tmp);iso=pth/'installer.iso';iso.write_bytes(b'installer fixture')
            cfg=SimpleNamespace(iso=iso,output=pth/'new',sha256=hashlib.sha256(iso.read_bytes()).hexdigest(),ram=8192,vcpus=2)
            ctx.enter_context(patch.object(mod.shutil,'which',return_value='/fixture/tool'))
            ctx.enter_context(patch.object(mod,'valida_kvm'))
            ctx.enter_context(patch.object(mod,'ram_disponible',return_value=20*1024**3))
            ctx.enter_context(patch.object(mod.os,'cpu_count',return_value=4))
            ctx.enter_context(patch.object(mod.shutil,'disk_usage',return_value=SimpleNamespace(free=100*1024**3)))
            met=ctx.enter_context(patch.object(mod,'datos_iso',return_value=('45','x86_64')))
            dat=mod.plan(cfg)
            self.assertFalse(cfg.output.exists())
            self.assertIn('--iso='+str(iso),dat['command'])
            self.assertIn('--ram=8192',dat['command'])
            self.assertEqual(dat['human_terminal_count'],2)
            self.assertFalse(any('--no-virt' in arg or '--no-kvm' in arg for arg in dat['command']))
            for valor in [('44','x86_64'),('45','aarch64')]:
                met.return_value=valor
                with self.assertRaisesRegex(ValueError,'Fedora 45 x86_64'):mod.plan(cfg)
            met.return_value=('45','x86_64')
            cfg.sha256='0'*64
            with self.assertRaisesRegex(ValueError,'no coincide'):mod.plan(cfg)
            cfg.sha256=hashlib.sha256(iso.read_bytes()).hexdigest();cfg.ram=20000
            with self.assertRaisesRegex(ValueError,'RAM de VM'):mod.plan(cfg)
            cfg.ram=8192;cfg.output.mkdir()
            with self.assertRaisesRegex(ValueError,'NUEVA'):mod.plan(cfg)
            cfg.output=RAIZ/'forbidden-output'
            with self.assertRaisesRegex(ValueError,'fuentes'):mod.plan(cfg)

    def test_missing_kvm_fails_without_starting_an_installer(self):
        mod=carga('build')
        with patch.object(mod.Path,'exists',return_value=False),patch.object(mod.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'KVM'):mod.valida_kvm()
        run.assert_not_called()

    def test_embedded_suite_uses_only_verified_declared_files(self):
        mod=carga('suite_payload')
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp)
            for nom in mod.ENTRADAS:(pth/nom).write_text('# launcher fixture\n')
            (pth/'not-declared-secret.json').write_text('must not travel')
            sums=''.join(hashlib.sha256((pth/nom).read_bytes()).hexdigest()+'  '+nom+'\n' for nom in mod.ENTRADAS)
            (pth/'SHA256SUMS').write_text(sums)
            paquete,num=mod.paquete_suite(pth)
            with tarfile.open(fileobj=io.BytesIO(paquete)) as arc:self.assertEqual(set(arc.getnames()),set(mod.ENTRADAS)|{'SHA256SUMS'})
            self.assertEqual(num,8)
            (pth/'aux-catalog').write_text('modified')
            with self.assertRaisesRegex(ValueError,'modificada'):mod.paquete_suite(pth)
            (pth/'aux-catalog').write_text('# launcher fixture\n')
            (pth/'SHA256SUMS').write_text(sums+'a'*64+'  ../escape\n')
            with self.assertRaisesRegex(ValueError,'Ruta'):mod.paquete_suite(pth)

    def test_finish_declares_capabilities_without_claiming_a_boot_test(self):
        mod=carga('finish')
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp)/'source.json'
            dat={'schema':'aux-live-source-v1','human_terminal_count':2,'terminal_protocol':2,
                 'fedora_release':45,'version':'7.0.0-beta.15','suite_sha256':'a'*64,'applications':['aux-catalog']}
            pth.write_text(json.dumps(dat));cap=mod.capacidades(pth)
            self.assertFalse(cap['boot_verified']);self.assertEqual(cap['human_terminal_count'],2)
            dat['human_terminal_count']=1;pth.write_text(json.dumps(dat))
            with self.assertRaises(ValueError):mod.capacidades(pth)

    def test_fedora_installroot_uses_vendor_and_local_repository_directories(self):
        cmd=setup.comandos_base('fedora',Path('/tmp/aux-fixture-root'),True,['base'],'45')[0]
        self.assertIn('--setopt=reposdir=/etc/yum.repos.d,/usr/share/dnf5/repos.d',cmd)


class SeleccionLive(unittest.TestCase):
    def test_legacy_media_remains_manual_until_capability_manifest_is_present(self):
        eng=motor();cfg=SimpleNamespace(pxe_url='http://pxe.example.test',base_url='https://aux.example.test')
        rec=eng.obt_meta('https://example.test/aux-assist-7.0.0-beta.15-x86_64.iso')
        rec.update(assistance_boot=True,_boot={'group':'tools','commands':['echo fixture'],'firmware':None})
        with tempfile.TemporaryDirectory() as tmp:
            pth=Path(tmp);eng.cap_asistencia(rec,pth)
            menu=eng.gen_ipxe([rec],cfg)
            self.assertNotIn('set auto_timeout 60000',menu)
            self.assertIn('legacy client',menu)
            (pth/'aux-live.json').write_text(json.dumps({'schema':'aux-live-capabilities-v1',
                'human_terminal_count':2,'terminal_protocol':2,'suite_sha256':'b'*64,'version':'7.0.0-beta.15'}))
            eng.cap_asistencia(rec,pth);menu=eng.gen_ipxe([rec],cfg)
            self.assertIn('&& set auto_target '+rec['id'],menu)
            self.assertIn('&& set auto_timeout 60000',menu)
            (pth/'aux-live.json').write_text('{invalid')
            eng.cap_asistencia(rec,pth)
            self.assertNotIn('set auto_timeout 60000',eng.gen_ipxe([rec],cfg))

    def test_beta_components_sort_numerically_and_final_release_wins(self):
        eng=motor()
        recs=[{'filename':'aux-assist-7.0.0'+ver+'-x86_64.iso'} for ver in ('-beta.10','-beta.9','','-rc.1')]
        self.assertEqual([r['filename'] for r in sorted(recs,key=eng.orden_asistencia)],
                         [recs[i]['filename'] for i in (1,0,3,2)])


if __name__=='__main__':unittest.main()
