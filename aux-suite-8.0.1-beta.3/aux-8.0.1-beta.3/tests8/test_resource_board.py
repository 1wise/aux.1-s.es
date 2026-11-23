# Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
# Author & Credits: https://www.alawise.es/1-s
"""Verify shared board edits, independent phases and operational capacity guards."""
import contextlib,copy,io,json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from auxlib import resource_board as b,precautions as p,profiles,checkstatus,catalog_v8,branding,localtools,software
from types import SimpleNamespace


class ResourceBoard(unittest.TestCase):
 def setUp(self):self.e=catalog_v8.valida({'id':'fixture','family':'debian','release':'test','architecture':'amd64','kind':'installer','original_url':'https://example.test/file.iso','policy':'004','priority':'1'})
 def test_policy_and_priority_preserve_artifact(self):
  e=b.conmuta(b.conmuta(self.e,22),0);self.assertEqual((e['policy'],e['priority']),('005','5'));self.assertEqual(e['identity'],self.e['identity'])
 def test_observations_are_readonly(self):
  for bit in range(12,20):
   with self.assertRaises(ValueError):b.conmuta(self.e,bit)
 def test_remote_destinations_stay_constrained(self):
  for bit in (0,1,3):
   with self.assertRaises(ValueError):b.conmuta({**self.e,'remote_only':True},bit)
 def test_unknown_is_not_absence(self):
  cells=b.celdas(self.e,{});self.assertEqual(len(cells),24);self.assertEqual(cells[4:12],['?']*8)
 def test_snapshot_does_not_override_policy(self):self.assertEqual(b.palabra(self.e,{'word24':'F880FF'}),'188004')
 def test_filter_does_not_mutate_catalogue(self):
  old=copy.deepcopy(self.e);self.assertEqual(b.filtra([self.e],'AMD64'),[self.e]);self.assertEqual(self.e,old)
 def test_operations_start_as_independent_plans(self):
  for name in ('download','deploy','generate'):
   self.assertIn('--dry-run',b.comandos(name));self.assertIn('--apply',b.comandos(name,apply=True))
  self.assertNotIn('--apply',b.comandos('checkstatus'))
 def test_confirmation_rejects_wrong_word(self):
  with self.assertRaises(ValueError):b.exige('APLICAR')('yes')
 def test_80_column_screen_keeps_24_cells_and_edits_last_bit(self):
  class Screen:
   def __init__(self):self.keys=iter([b.curses.KEY_RIGHT]*23+[' ','s']);self.draws=[]
   def keypad(self,x):pass
   def erase(self):pass
   def getmaxyx(self):return 24,80
   def addnstr(self,y,x,s,n,a):self.draws.append((y,x,s[:n]))
   def refresh(self):pass
   def get_wch(self):return next(self.keys)
  scr=Screen();styles={k:0 for k in ('normal','titulo','activo','detalle','ayuda')}
  with patch.object(b,'paleta',return_value=styles):action,cat=b.pantalla(scr,{'entries':[self.e]},{'entries':{}})
  self.assertEqual(action,'save');self.assertEqual(cat['entries'][0]['policy'],'005');self.assertTrue(all(x+len(s)<80 for y,x,s in scr.draws));self.assertEqual(len({x for y,x,s in scr.draws if y==4 and s.startswith('[')}),6)
 def test_checkstatus_routes_to_board(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cat=root/'catalog.json';cfg=root/'settings.json';cat.write_text(json.dumps({'schema':'aux-catalog-v8','entries':[self.e]}));cfg.write_text(json.dumps({'catalog_file':str(cat)}))
   with patch.object(b,'interactivo',return_value=0) as run:self.assertEqual(checkstatus.main(['--config',str(cfg),'-i']),0);run.assert_called_once_with(str(cfg),None)
 def test_serial_console_prints_one_resource_line(self):
  out=io.StringIO()
  with contextlib.redirect_stdout(out),patch.object(b,'campo',return_value='back'):b.consola({'entries':[self.e]},{'entries':{}})
  self.assertEqual(out.getvalue().splitlines()[0].count('['),6)
 def test_remote_controls_are_opt_in(self):
  self.assertNotIn('aux-assist',profiles.DEFAULT_ROLES);self.assertNotIn('admin',profiles.DEFAULT_ROLES)
  self.assertNotIn('ssh-server',software.defecto('debian')['tasks'])
  for dis in ('debian','fedora'):self.assertNotIn('openssh-server',profiles.ROLES['base'][dis].split())
  self.assertIn('openssh-client-default',profiles.ROLES['base']['alpine'].split())
 def test_disk_guard_retains_system_reserve(self):
  with patch.object(p,'espacio',return_value=2*p.GIB):
   self.assertEqual(p.protege('/tmp',p.GIB)['reserve_bytes'],p.GIB)
   with self.assertRaises(ValueError):p.protege('/tmp',p.GIB+1)
 def test_ram_guard_uses_available_memory(self):
  with patch.object(p,'meminfo',return_value={'MemTotal':8*p.GIB,'MemAvailable':3*p.GIB}):
   self.assertEqual(p.protege('/tmp',p.GIB,True)['available_bytes'],3*p.GIB)
   with self.assertRaises(ValueError):p.protege('/tmp',2*p.GIB,True)
 def test_cockpit_does_not_start_after_a_generic_yes(self):
  with patch('builtins.input',side_effect=['s','']),patch.object(localtools.subprocess,'run',return_value=SimpleNamespace(stdout='127.0.0.1')) as run,contextlib.redirect_stdout(io.StringIO()):localtools.abre('cockpit')
  self.assertFalse(any(call.args[0][:2]==['systemctl','start'] for call in run.call_args_list))
 def test_cockpit_requires_the_explicit_start_phrase(self):
  with patch('builtins.input',side_effect=['INICIAR COCKPIT','']),patch.object(localtools.subprocess,'run',return_value=SimpleNamespace(stdout='127.0.0.1')) as run,contextlib.redirect_stdout(io.StringIO()):localtools.abre('cockpit')
  self.assertTrue(any(call.args[0]==['systemctl','start','cockpit.socket'] for call in run.call_args_list))
 def test_new_featured_and_markers_are_present(self):
  self.assertEqual(branding.dimensiones(),(1254,1254));self.assertIn('RED TEAM',p.html('remote'));self.assertIn('Blue Hibou',p.guia())


if __name__=='__main__':unittest.main()
