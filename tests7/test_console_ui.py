# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Check visual semantics, retained choices and cancellation before execution."""
import contextlib
import curses
import io
import subprocess
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from auxlib import console_ui as ui, images, setup, interactive
from test_catalog_console import Pantalla


class InterfazCompartida(unittest.TestCase):
    def elige_pantalla(self,opciones,teclas,defecto=1):
        scr=Pantalla(teclas)
        def wrapper(func,*args):return func(scr,*args)
        with patch.object(interactive.sys.stdin,'isatty',return_value=True), \
             patch.object(interactive.sys.stdout,'isatty',return_value=True), \
             patch.object(ui.curses,'wrapper',side_effect=wrapper):
            return interactive.elige('Dispositivos',opciones,defecto)

    def test_single_choice_returns_the_original_device_dict(self):
        a={'name':'/dev/vda','fstype':'LVM2_member'}
        b={'name':'/dev/vdb','children':[{'name':'nested'}]}
        self.assertIs(self.elige_pantalla([('Disco A',a),('Disco B',b)],['\n'],2),b)

    def test_equal_dicts_remain_distinct_options(self):
        a={'name':'root'};b={'name':'root'}
        self.assertIs(self.elige_pantalla([('Primero',a),('Segundo',b)],[curses.KEY_DOWN,'\n']),b)

    def test_lists_and_none_can_be_returned_without_becoming_widget_ids(self):
        val=['one',{'two':2}]
        self.assertIs(self.elige_pantalla([('Lista',val),('Nada',None)],['\n']),val)
        self.assertIsNone(self.elige_pantalla([('Lista',val),('Nada',None)],['\n'],2))

    def test_false_zero_and_true_retain_their_exact_types(self):
        for n,val in enumerate((False,0,True),1):
            with self.subTest(option=n):
                res=self.elige_pantalla([('No',False),('Cero',0),('Sí',True)],['\n'],n)
                self.assertIs(type(res),type(val));self.assertEqual(res,val)

    def test_search_uses_the_labels_for_dict_backed_options(self):
        val={'name':'/dev/vdb'}
        res=self.elige_pantalla([('Otro',{}),('Raiz elegida',val)],['/','R','a','i','z','\n','\n'])
        self.assertIs(res,val)

    def test_empty_menu_and_invalid_default_are_rejected_before_curses(self):
        for opciones,defecto in (([],1),([('Uno',{})],2)):
            with self.subTest(default=defecto),patch.object(ui.curses,'wrapper') as wrapper:
                with self.assertRaises(ValueError):interactive.elige('Vacío',opciones,defecto)
                wrapper.assert_not_called()

    def test_named_application_versions_and_generator_help(self):
        for nom in ('aux','aux-setup','aux-profile','aux-catalog','aux-images'):
            res=subprocess.run(['python3',str(setup.DIR_APP/nom),'--version'],capture_output=True,text=True)
            self.assertEqual(res.returncode,0,res.stderr)
            self.assertIn('7.0.0-beta.19',res.stdout)
        for nom in ('iso/prepare.py','iso-assist/prepare.py','usb/portable/build.py'):
            res=subprocess.run(['python3',str(setup.DIR_APP/nom),'--help'],capture_output=True,text=True)
            self.assertEqual(res.returncode,0,res.stderr)
            self.assertIn('--interactive',res.stdout)

    def test_theme_background_distinguishes_configuration_from_generation(self):
        scr=Mock()
        with patch.object(curses,'has_colors',return_value=True), \
             patch.object(curses,'start_color'), \
             patch.object(curses,'COLORS',256,create=True), \
             patch.object(curses,'init_pair') as pares, \
             patch.object(curses,'color_pair',side_effect=lambda n:n*256):
            ui.paleta(scr,'configuracion')
            self.assertEqual(pares.call_args_list[0].args,(1,curses.COLOR_WHITE,54))
            pares.reset_mock()
            ui.paleta(scr,'ejecucion')
            self.assertEqual(pares.call_args_list[0].args,(1,54,51))

    def test_application_identity_and_theme_restore_after_cancellation(self):
        antes=ui.CONTEXTO.get()
        with self.assertRaises(KeyboardInterrupt):
            with ui.aplicacion('AUX SETUP','ejecucion'):
                scr=Pantalla(['q'])
                ui.pantalla(scr,'Destino',[('iso','ISO'),('existing','SISTEMA ACTUAL')])
        self.assertEqual(ui.CONTEXTO.get(),antes)
        self.assertTrue(any('AUX SETUP' in t and 'INSTALAR / GENERAR' in t for t in scr.textos))

    def test_checkbox_selection_can_be_removed_from_right_panel(self):
        scr=Pantalla([' ',curses.KEY_DOWN,' ','\t',' ','s'])
        self.assertEqual(ui.pantalla(scr,'Paquetes',[('a','Alpha'),('b','Beta')],multiple=True),['b'])

    def test_group_navigation_keeps_selected_options(self):
        scr=Pantalla([curses.KEY_DOWN,'\n',' ',curses.KEY_BACKSPACE,
                      curses.KEY_DOWN,curses.KEY_DOWN,'\n',' ','s'])
        res=ui.pantalla(scr,'Grupos',[('a','Alpha'),('b','Beta')],multiple=True,
                       categorias={'a':'A','b':'B'})
        self.assertEqual(res,['a','b'])

    def test_field_edit_and_accept(self):
        scr=Pantalla(['\x15','/','t','m','p','\n'])
        self.assertEqual(ui.campo_pantalla(scr,'Salida','/old'),'/tmp')

    def test_setup_cancelled_review_does_not_execute(self):
        def prepara(cfg):
            cfg.mode='tools';cfg.apply=False;return cfg
        with patch('auxlib.interactive.prepara',side_effect=prepara), \
             patch.object(setup,'ejecuta_seleccion') as ejecuta, \
             patch.object(ui,'campo',return_value=''), contextlib.redirect_stdout(io.StringIO()):
            setup.main(['--interactive'])
        self.assertEqual(ejecuta.call_count,1)
        self.assertFalse(ejecuta.call_args.args[0].apply)

    def test_live_cancel_does_not_start_a_generator(self):
        cfg=SimpleNamespace(output=Path('/tmp/new-live'))
        with patch.object(images,'campo',return_value=''),self.assertRaises(KeyboardInterrupt):
            images.parametros_live(cfg)

    def test_usb_plan_is_the_default_action(self):
        cfg=SimpleNamespace(iso=Path('/tmp/in.iso'),sha256='a'*64,
                            output=Path('/tmp/out.img'),capacity_bytes=8*1024**3,
                            build=True,ipxe_image=None,ipxe_sha256=None)
        with patch.object(images,'elige',return_value=False):
            images.parametros_usb(cfg)
        self.assertFalse(cfg.build)


if __name__=='__main__':
    unittest.main()
