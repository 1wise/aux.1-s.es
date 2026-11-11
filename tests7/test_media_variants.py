# Timestamp: 2026-11-10 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Keep prepared variants independent and preserve existing tree ownership."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

RAIZ = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('aux_media_common', RAIZ/'src/common.py')
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)


def carga_tarea(nombre):
    pth = RAIZ/(nombre+'.sh')
    txt = pth.read_text().split("<<'AUXPY'\n", 1)[1].rsplit('\nAUXPY\n', 1)[0]
    mod = ModuleType('aux_media_'+nombre)
    mod.__file__ = str(pth)
    with patch.dict(sys.modules, {'common': BASE}):
        exec(compile(txt, str(pth), 'exec'), mod.__dict__)
    return mod


def configura(raiz):
    cfg = SimpleNamespace(cache=raiz/'cache', output=raiz/'public', ram_dir=raiz/'ram',
                          mode='ram', ram_budget_gib=28, ram_reserve_percent=10,
                          quiet=True, pxe_url='http://pxe.example.org', only=None)
    for pth in (cfg.cache, cfg.output, cfg.ram_dir):
        pth.mkdir()
    return cfg


class VariantesMedios(unittest.TestCase):
    def test_memtest_normal_and_grub_have_separate_tree_names(self):
        normal = BASE.obt_meta('https://www.memtest.org/download/v9.00/mt86plus_9.00_x86_64.iso.zip')
        grub = BASE.obt_meta('https://www.memtest.org/download/v9.00/mt86plus_9.00_x86_64.grub.iso.zip')
        self.assertEqual(normal['tree'], 'mt86plus_9.00_x86_64')
        self.assertEqual(grub['tree'], 'mt86plus_9.00_x86_64.grub')
        self.assertNotEqual(normal['id'], grub['id'])

    def test_ambiguous_archive_list_fails_before_touching_files(self):
        with self.assertRaisesRegex(ValueError, 'Prepared tree collision'):
            BASE.obt_catalog('https://example.org/rescue.iso\nhttps://example.org/rescue.zip\n')

    def test_unfiltered_cache_discovery_rejects_the_same_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = configura(Path(tmp))
            for nom in ('rescue.iso', 'rescue.zip'):
                (cfg.cache/nom).write_bytes(b'untouched')
            with self.assertRaisesRegex(ValueError, 'Prepared tree collision'):
                BASE.lee_cache(cfg)
            self.assertEqual(list(cfg.output.iterdir()), [])

    def test_both_variants_deploy_and_repeat_without_reextracting_or_crossing(self):
        mod = carga_tarea('deploy')
        nombres = ['mt86plus_9.00_x86_64.iso.zip', 'mt86plus_9.00_x86_64.grub.iso.zip']
        for orden in (nombres, list(reversed(nombres))):
            with self.subTest(order=orden), tempfile.TemporaryDirectory() as tmp:
                cfg = configura(Path(tmp))
                recursos = []
                for nom in orden:
                    with zipfile.ZipFile(cfg.cache/nom, 'w') as arc:
                        arc.writestr('boot/memtest.efi', nom.encode())
                    recursos.append(BASE.obt_meta('https://www.memtest.org/download/v9.00/'+nom))
                # Only the tmpfs type probe is simulated; ZIP extraction, links and states are real.
                with patch.object(mod.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'tmpfs\n', '')), \
                     patch.object(mod, 'ext_archive', wraps=mod.ext_archive) as extrae:
                    for _ in range(2):
                        for rec in recursos:
                            mod.valida_cache(rec, cfg, {})
                            mod.prep_ram(rec, cfg)
                            self.assertEqual(rec['deployment'], 'ram')
                    self.assertEqual(extrae.call_count, 2)
                for rec in recursos:
                    self.assertEqual((cfg.output/rec['tree']/'boot/memtest.efi').read_bytes(), rec['filename'].encode())
                    self.assertEqual((cfg.output/rec['tree']).resolve(), cfg.ram_dir/rec['tree'])
                gen = carga_tarea('generate')
                encontrados = gen.descubre([], cfg)
                self.assertEqual({r['tree'] for r in encontrados}, {r['tree'] for r in recursos})

    def test_unmanaged_grub_link_still_cannot_replace_another_tree(self):
        mod = carga_tarea('deploy')
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            cfg = configura(raiz)
            ajeno = raiz/'unrelated'
            ajeno.mkdir()
            (ajeno/'keep').write_text('preserved')
            rec = BASE.obt_meta('https://www.memtest.org/download/v9.00/mt86plus_9.00_x86_64.grub.iso.zip')
            with zipfile.ZipFile(cfg.cache/rec['filename'], 'w') as arc:
                arc.writestr('boot/memtest.efi', b'new')
            (cfg.output/rec['tree']).symlink_to(ajeno)
            mod.valida_cache(rec, cfg, {})
            with patch.object(mod.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'tmpfs\n', '')), \
                 self.assertRaisesRegex(ValueError, 'Existing unmanaged tree link'):
                mod.prep_ram(rec, cfg)
            self.assertEqual((ajeno/'keep').read_text(), 'preserved')
            self.assertEqual((cfg.output/rec['tree']).resolve(), ajeno)

    def test_fedora_secondary_architectures_are_never_reported_as_x86(self):
        for arq in ('s390x', 'ppc64le'):
            for edicion in ('Server', 'Everything'):
                with self.subTest(architecture=arq, edition=edicion):
                    rec = BASE.obt_meta('https://download.fedoraproject.org/Fedora-'+edicion+'-netinst-'+arq+'-45-1.4.iso')
                    self.assertEqual((rec['arch'], rec['release']), (arq, '45'))


if __name__ == '__main__':
    unittest.main()
