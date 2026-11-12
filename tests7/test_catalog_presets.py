# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Exercise shared budgets, presets and two-panel edits."""
import curses
import unittest
from unittest.mock import patch
from auxlib import catalog_selection as plan, localtools
from test_catalog_console import entrada, Pantalla


class PresetsCatalogo(unittest.TestCase):
    def setUp(self):
        self.lim = {'ram': 10, 'ssd': 20, 'ram_total': 10, 'reserve_percent': 0}

    def test_exact_boundary_counts_light_in_ssd_and_respects_ram(self):
        sel = {}
        plan.incorpora_catalogo(entrada('a','light',10),sel,self.lim)
        plan.incorpora_catalogo(entrada('b','heavy',10),sel,self.lim)
        self.assertEqual(plan.uso_catalogo(sel.values()),{'ram':10,'ssd':20,'unknown':0})
        self.assertEqual(plan.incorpora_catalogo(entrada('c','heavy',1),sel,self.lim),'sin espacio')
        self.assertEqual(plan.modo_catalogo(sel['c']),'origin')

    def test_unknown_size_is_not_assumed_to_be_zero(self):
        sel = {}
        self.assertEqual(plan.incorpora_catalogo(entrada('a','light'),sel,self.lim),'sin tamaño')
        self.assertEqual(sel['a']['requested_selection_mode'],'light')
        self.assertTrue(plan.cabe_catalogo(sel.values(),self.lim))

    def test_reclassifying_heavy_to_light_cannot_exceed_ram(self):
        ent=entrada('a','heavy',15);sel={}
        plan.incorpora_catalogo(ent,sel,self.lim)
        self.assertEqual(plan.incorpora_catalogo(ent,sel,self.lim,'light'),'sin espacio')
        self.assertEqual(plan.uso_catalogo(sel.values())['ram'],0)

    def test_default_preserves_current_lists_and_ignores_unlisted_entries(self):
        a=entrada('a','heavy',5);b=entrada('b','light',5)
        with patch.object(plan,'urls_defecto',return_value={a['original_url']:'light'}):
            sel=plan.preset_catalogo([a,b],'default',self.lim)
        self.assertEqual(set(sel),{'a'})
        self.assertEqual(sel['a']['download_class'],'light')

    def test_suggested_includes_rescatux_and_is_bounded(self):
        datos=[entrada('rescatux','light',5),entrada('fedora','heavy',30)]
        sel=plan.preset_catalogo(datos,'suggested',self.lim)
        self.assertIn('rescatux',sel)
        self.assertEqual(plan.modo_catalogo(sel['fedora']),'origin')
        self.assertTrue(plan.cabe_catalogo(sel.values(),self.lim))

    def test_select_all_and_remove_from_right_panel(self):
        datos=[entrada('a','light',10),entrada('b','heavy',11),entrada('c','heavy')]
        scr=Pantalla(['a','\t',' ','s'])
        with patch.object(plan,'limites_catalogo',return_value=self.lim):
            sel=localtools.seleccion_catalogo(scr,datos)
        self.assertEqual({e['id'] for e in sel},{'b','c'})
        self.assertTrue(plan.cabe_catalogo(sel,self.lim))
        self.assertTrue(any('SELECCIONADAS' in t for t in scr.textos))
        self.assertEqual(sel.preset,'custom')

    def test_switching_presets_restores_custom_selection(self):
        scr=Pantalla(['a','p',curses.KEY_UP,curses.KEY_UP,'\n',
                      'p',curses.KEY_DOWN,curses.KEY_DOWN,'\n','s'])
        sel=localtools.seleccion_catalogo(scr,[entrada('a','light',1)])
        self.assertEqual([e['id'] for e in sel],['a'])
        self.assertEqual(sel.preset,'custom')

    def test_new_config_uses_28_gib_with_reserve_and_100_gib_ssd(self):
        lim=plan.limites_catalogo()
        self.assertEqual(lim['ram_total'],28*plan.GIB)
        self.assertEqual(lim['ram'],int(28*plan.GIB*.9))
        self.assertEqual(lim['ssd'],100*plan.GIB)


if __name__ == '__main__':
    unittest.main()
