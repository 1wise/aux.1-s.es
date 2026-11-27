# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Resource identity and narrow-terminal detail navigation."""
import curses
import json
import unittest
from unittest.mock import patch
from auxlib.common import DIR_APP
from auxlib import console_ui as ui, interactive
from auxlib.catalog_details import rotulo,detalles
from test_catalog_console import Pantalla


class CatalogDetails(unittest.TestCase):
    def setUp(self): self.config=json.loads((DIR_APP/'config/catalog.sources.json').read_text())

    def test_workstation_x86_is_identified_from_older_report(self):
        fila={'slot_id':'d32-fedora-downloads','previous_url':'https://example/Fedora-Workstation-Live-44-1.7.x86_64.iso',
              'release':'45-1.4','original_url':'https://example/Fedora-Workstation-Live-45-1.4.x86_64.iso'}
        self.assertIn('Fedora Workstation Live | x86_64 | 45-1.4',rotulo(fila,self.config))
        self.assertIn('Archivo actual: Fedora-Workstation-Live-45-1.4.x86_64.iso',detalles(fila,self.config))

    def test_unresolved_row_does_not_claim_old_seed_version_is_current(self):
        fila={'slot_id':'d32-fedora-downloads','previous_url':'https://example/Fedora-Workstation-Live-44-1.7.x86_64.iso'}
        self.assertIn('por resolver',rotulo(fila,self.config))
        self.assertIn('Archivo de la lista anterior:', '\n'.join(detalles(fila,self.config)))

    def test_right_panel_accepts_focused_resource_after_scrolling(self):
        scr=Pantalla([curses.KEY_DOWN,'\t',curses.KEY_NPAGE,'\n'])
        res=ui.pantalla(scr,'Recuperar',[('a','Primero'),('b','Fedora Workstation')],['a'],
                        detalles={'a':['A'],'b':['long line '+str(i) for i in range(80)]})
        self.assertEqual(res,'b')

    def test_detail_widget_keeps_dict_values_outside_curses_ids(self):
        val={'slot_id':'d32-fedora-downloads'}
        with patch.object(interactive.sys.stdin,'isatty',return_value=True), \
             patch.object(interactive.sys.stdout,'isatty',return_value=True), \
             patch.object(interactive,'selecciona',return_value='0') as widget:
            self.assertIs(interactive.elige('Imagen',[('Fedora',val)],detalles=[['Full filename']]),val)
        self.assertEqual(widget.call_args.kwargs['detalles'],{'0':['Full filename']})


if __name__=='__main__': unittest.main()
