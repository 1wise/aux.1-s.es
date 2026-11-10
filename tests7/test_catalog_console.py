# Timestamp: 2026-11-10 | Version: 7.0.0-beta.0
# Author & Credits: https://www.alawise.es/1-s
"""Check keyboard selection, size accounting and source-only export."""
import curses
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from auxlib import localtools, webapps


def entrada(nom, clase, size=None, remote=False):
    return {'id':nom,'name':nom,'family':nom,'release':'45','architecture':'x86_64',
            'kind':'image','download_class':clase,'size_bytes':size,
            'original_url':'https://example.org/'+nom+'.iso','remote_only':remote}


class Pantalla:
    def __init__(self,teclas): self.teclas=iter(teclas);self.textos=[]
    def keypad(self,*args): pass
    def getmaxyx(self): return (24,100)
    def erase(self): pass
    def addnstr(self,y,x,txt,n,*args): self.textos.append(txt[:n])
    def refresh(self): pass
    def get_wch(self): return next(self.teclas)


class ConsolaCatalogo(unittest.TestCase):
    def test_checkbox_and_class_changes_preserve_selection(self):
        scr=Pantalla([curses.KEY_DOWN,curses.KEY_DOWN,'\n',' ',curses.KEY_DOWN,'h',' ','s'])
        sel=localtools.seleccion_catalogo(scr,[entrada('one','light',1024),entrada('two','light',2048)])
        self.assertEqual([(e['id'],e['download_class']) for e in sel],[('one','light'),('two','heavy')])
        self.assertTrue(any('[x]' in txt for txt in scr.textos))
        self.assertTrue(any('sin tamaño' in txt for txt in scr.textos))

    def test_groups_distributions_and_tools_without_losing_entries(self):
        datos=[entrada('fedora','light'),entrada('gparted','heavy'),entrada('other','light')]
        datos[1]['kind']='tool'
        dis,tools=localtools.arbol_catalogo(datos)
        self.assertEqual({e['id'] for values in dis.values() for e in values},{'fedora','other'})
        self.assertEqual([e['id'] for e in tools['Discos y recuperación']],['gparted'])

    def test_selection_persists_between_distribution_and_tool_menus(self):
        scr=Pantalla(['\n','\n',' ',curses.KEY_BACKSPACE,curses.KEY_BACKSPACE,
                     curses.KEY_DOWN,'\n','\n',' ','s'])
        datos=[entrada('fedora','light'),entrada('gparted','heavy')]
        datos[1]['kind']='tool'
        self.assertEqual({e['id'] for e in localtools.seleccion_catalogo(scr,datos)},
                         {'fedora','gparted'})

    def test_enter_chooses_origin_and_excludes_it_from_local_totals(self):
        scr=Pantalla([curses.KEY_DOWN,curses.KEY_DOWN,'\n',' ',
                     '\n',curses.KEY_DOWN,curses.KEY_DOWN,'\n','s'])
        sel=localtools.seleccion_catalogo(scr,[entrada('fedora','light',1024)])
        self.assertEqual(sel[0]['selection_mode'],'origin')
        self.assertEqual(localtools.resumen_catalogo(sel)['light']['count'],0)
        self.assertTrue(any('Solo origen' in txt for txt in scr.textos))

    def test_remote_only_cannot_be_changed_to_local(self):
        scr=Pantalla([curses.KEY_DOWN,curses.KEY_DOWN,'\n','l',' ', 's'])
        sel=localtools.seleccion_catalogo(scr,[entrada('menu','light',remote=True)])
        self.assertTrue(sel[0]['remote_only'])
        self.assertEqual(sel[0]['selection_mode'],'origin')

    def test_totals_do_not_invent_unknown_sizes_or_cache_remote_menus(self):
        dat=localtools.resumen_catalogo([entrada('a','light',1024),entrada('b','light'),entrada('c','heavy',2048),entrada('menu','light',remote=True)])
        self.assertEqual(dat['light'],{'bytes':1024,'unknown':1,'count':2})
        self.assertEqual(dat['heavy'],{'bytes':2048,'unknown':0,'count':1})

    def test_export_contains_json_and_separate_origin_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst=Path(tmp)/'selection'
            sel=[entrada('a','light',1024),entrada('b','heavy',2048),entrada('menu','light',remote=True)]
            with patch.object(localtools.sys.stdin,'isatty',return_value=True), \
                 patch.object(localtools.sys.stdout,'isatty',return_value=True), \
                 patch.object(localtools.curses,'wrapper',return_value=sel), \
                 patch('builtins.input',return_value=str(dst)), \
                 patch.object(localtools.Path,'is_file',return_value=False), \
                 patch.object(webapps,'modelo',return_value={'entries':sel}):
                localtools.catalogo()
            self.assertEqual(len(json.loads((dst/'aux-catalog-selection.json').read_text())['entries']),3)
            self.assertEqual((dst/'light-url.txt').read_text(),'https://example.org/a.iso\n')
            self.assertEqual((dst/'heavy-url.txt').read_text(),'https://example.org/b.iso\n')
            self.assertEqual((dst/'origin-url.txt').read_text(),'https://example.org/menu.iso\n')


if __name__=='__main__': unittest.main()
