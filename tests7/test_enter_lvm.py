# Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Exercise scoped LVM discovery, lifecycle and refusal paths without real block writes."""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from auxlib import enter,lvm

VG='A'*32
LV='B'*32
PV1='C'*32
PV2='D'*32


def grupo():
    return {'name':'rescue','uuid':VG,'devices':['/dev/vda2','/dev/vdb1'],
        'volumes':[{'name':'root','uuid':LV,'path':'/dev/rescue/root','size':'2147483648',
                    'active':False,'segments':['linear']}]}


def informes():
    return {
        'pvs':{'pv':[{'pv_name':'/dev/vda2','pv_uuid':PV1,'vg_name':'rescue','vg_uuid':VG},
                     {'pv_name':'/dev/vdb1','pv_uuid':PV2,'vg_name':'rescue','vg_uuid':VG},
                     {'pv_name':'/dev/vdc1','pv_uuid':'E'*32,'vg_name':'unrelated','vg_uuid':'F'*32}]},
        'vgs':{'vg':[{'vg_name':'rescue','vg_uuid':VG,'vg_missing_pv_count':'0'}]},
        'lvs':{'seg':[{'vg_name':'rescue','vg_uuid':VG,'lv_name':'root','lv_uuid':LV,
                      'lv_size':'2147483648','lv_active':'inactive','segtype':'linear'}]}}


class InformesLVM(unittest.TestCase):
    def test_multi_pv_group_excludes_unrelated_disks_and_does_not_activate(self):
        datos=informes();comandos=[]
        def run(cmd,**kwargs):
            comandos.append(cmd)
            return subprocess.CompletedProcess(cmd,0,json.dumps({'report':[datos[cmd[0]]]}),'')
        with patch.object(lvm.subprocess,'run',side_effect=run),patch.object(Path,'is_block_device',return_value=True):
            dat=lvm.grupo('/dev/vda2')
        self.assertEqual(dat['devices'],['/dev/vda2','/dev/vdb1'])
        self.assertEqual(dat['volumes'],grupo()['volumes'])
        self.assertEqual([cmd[0] for cmd in comandos],['pvs','vgs','lvs'])
        for cmd in comandos[1:]:
            self.assertEqual(cmd[cmd.index('--devices')+1],'/dev/vda2,/dev/vdb1')
            self.assertEqual(cmd[cmd.index('--select')+1],'vg_uuid='+VG)

    def test_duplicate_pv_uuid_and_missing_member_are_rejected(self):
        for caso in ('duplicate','missing'):
            datos=informes()
            if caso=='duplicate':datos['pvs']['pv'][1]['pv_uuid']=PV1
            else:datos['vgs']['vg'][0]['vg_missing_pv_count']='1'
            def run(cmd,**kwargs):return subprocess.CompletedProcess(cmd,0,json.dumps({'report':[datos[cmd[0]]]}),'')
            with self.subTest(case=caso),patch.object(lvm.subprocess,'run',side_effect=run), \
                 patch.object(Path,'is_block_device',return_value=True),self.assertRaises(ValueError):
                lvm.grupo('/dev/vda2')

    def test_lv_segments_are_merged_and_every_segment_is_retained(self):
        datos=informes();ent=copy.deepcopy(datos['lvs']['seg'][0]);ent['segtype']='striped';datos['lvs']['seg'].append(ent)
        def run(cmd,**kwargs):return subprocess.CompletedProcess(cmd,0,json.dumps({'report':[datos[cmd[0]]]}),'')
        with patch.object(lvm.subprocess,'run',side_effect=run),patch.object(Path,'is_block_device',return_value=True):
            dat=lvm.grupo('/dev/vda2')
        self.assertEqual(dat['volumes'][0]['segments'],['linear','striped'])
        self.assertEqual(len(dat['volumes']),1)

    def test_selection_is_bound_to_the_selected_group(self):
        dat=grupo()
        for valor in ('root','rescue/root',LV):
            self.assertEqual(lvm.elige_volumen(SimpleNamespace(lv=valor),dat)['uuid'],LV)
        with self.assertRaises(ValueError):lvm.elige_volumen(SimpleNamespace(lv='unrelated/root'),dat)
        with self.assertRaises(ValueError):lvm.identidad('anything; vgchange -ay')
        with self.assertRaises(ValueError):lvm.nombre('other/root')


class ActivacionLVM(unittest.TestCase):
    def ciclo(self,activo=False,ro='1',dm=None):
        dat=grupo();ent=dat['volumes'][0];ent['active']=activo;cmds=[]
        def orden(cmd):
            cmds.append(cmd)
            if cmd[0]=='dmsetup':return dm if dm is not None else 'LVM-'+VG+LV+'\n'
            if cmd[0]=='blockdev':return ro+'\n'
            return ''
        return dat,ent,cmds,orden

    def test_read_only_activation_and_cleanup_are_scoped_to_one_uuid(self):
        dat,ent,cmds,orden=self.ciclo()
        with patch.object(lvm,'orden',side_effect=orden),patch.object(Path,'is_block_device',return_value=True), \
             patch.object(Path,'exists',return_value=False):
            with lvm.activa(dat,ent) as pth:self.assertEqual(str(pth),ent['path'])
        cambios=[cmd for cmd in cmds if cmd[0]=='lvchange']
        self.assertEqual([cmd[2] for cmd in cambios],['y','n'])
        self.assertIn('read_only_volume_list=["rescue/root"]',cambios[0][cambios[0].index('--config')+1])
        for cmd in cambios:
            self.assertEqual(cmd[cmd.index('--select')+1],'lv_uuid='+LV)
            self.assertEqual(cmd[cmd.index('--devices')+1],'/dev/vda2,/dev/vdb1')
            self.assertNotIn('--permission',cmd)
            self.assertNotIn('--readonly',cmd)

    def test_existing_activation_is_verified_and_never_closed(self):
        dat,ent,cmds,orden=self.ciclo(activo=True)
        with patch.object(lvm,'orden',side_effect=orden),patch.object(Path,'is_block_device',return_value=True):
            with lvm.activa(dat,ent):pass
        self.assertEqual([cmd[0] for cmd in cmds],['dmsetup'])

    def test_incorrect_mapping_uuid_and_incorrect_read_only_mode_fail_and_cleanup(self):
        for opts in ({'dm':'LVM-wrong'},{'ro':'0'}):
            dat,ent,cmds,orden=self.ciclo(**opts)
            with self.subTest(options=opts),patch.object(lvm,'orden',side_effect=orden), \
                 patch.object(Path,'is_block_device',return_value=True),patch.object(Path,'exists',return_value=False):
                with self.assertRaises(RuntimeError):
                    with lvm.activa(dat,ent):self.fail('An invalid device became available to the caller')
            self.assertEqual([cmd[2] for cmd in cmds if cmd[0]=='lvchange'],['y','n'])

    def test_caller_failure_still_closes_only_the_new_lv(self):
        dat,ent,cmds,orden=self.ciclo()
        with patch.object(lvm,'orden',side_effect=orden),patch.object(Path,'is_block_device',return_value=True), \
             patch.object(Path,'exists',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'fixture failure'):
                with lvm.activa(dat,ent):raise RuntimeError('fixture failure')
        self.assertEqual([cmd[2] for cmd in cmds if cmd[0]=='lvchange'],['y','n'])

    def test_inactive_complex_layouts_are_not_silently_activated(self):
        for tipo in ('thin','thin-pool','raid1','snapshot','cache'):
            dat,ent,_,_=self.ciclo();ent['segments']=[tipo]
            with self.subTest(layout=tipo),patch.object(lvm,'orden') as orden,patch.object(Path,'exists',return_value=False):
                with self.assertRaisesRegex(ValueError,'linear/striped'):
                    with lvm.activa(dat,ent):pass
                orden.assert_not_called()

    def test_repair_activation_does_not_change_persistent_lv_permissions(self):
        dat,ent,cmds,orden=self.ciclo(ro='0')
        with patch.object(lvm,'orden',side_effect=orden),patch.object(Path,'is_block_device',return_value=True), \
             patch.object(Path,'exists',return_value=False):
            with lvm.activa(dat,ent,True):pass
        cmd=next(c for c in cmds if c[0]=='lvchange')
        self.assertNotIn('read_only_volume_list',' '.join(cmd))
        self.assertNotIn('--permission',cmd)


class EntradaLVM(unittest.TestCase):
    def cfg(self,apply=False,repair=False):
        return SimpleNamespace(device=Path('/dev/vda2'),apply=apply,repair=repair,lv=None,
            interactive=False,unlock=False,namespace=False,confirmed_device=None,subvolume=None)

    def test_plan_discovers_and_remembers_a_logical_volume_without_activation(self):
        cfg=self.cfg()
        with patch.object(Path,'is_block_device',return_value=True),patch.object(enter,'es_raiz_activa',return_value=False), \
             patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LVM2_member\n','')), \
             patch.object(lvm,'grupo',return_value=grupo()),patch.object(lvm,'activa') as activa:
            enter.entra(cfg)
        self.assertEqual(cfg.lv,LV);activa.assert_not_called()

    def test_apply_passes_the_selected_logical_device_to_the_existing_mount_flow(self):
        cfg=self.cfg(True);real=enter.entra;hijos=[]
        @contextmanager
        def activa(*args):yield Path('/dev/rescue/root')
        with patch.object(Path,'is_block_device',return_value=True),patch.object(enter,'es_raiz_activa',return_value=False), \
             patch.object(enter.os,'geteuid',return_value=0), \
             patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LVM2_member\n','')), \
             patch.object(lvm,'grupo',return_value=grupo()),patch.object(lvm,'activa',side_effect=activa), \
             patch.object(enter,'entra',side_effect=lambda sig:hijos.append(sig)):
            real(cfg)
        self.assertEqual(hijos[0].device,Path('/dev/rescue/root'))
        self.assertIsNone(hijos[0].lv)

    def test_cancelled_repair_does_not_activate_the_lv(self):
        cfg=self.cfg(True,True)
        with patch.object(Path,'is_block_device',return_value=True),patch.object(enter,'es_raiz_activa',return_value=False), \
             patch.object(enter.os,'geteuid',return_value=0),patch('builtins.input',return_value=''), \
             patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'LVM2_member\n','')), \
             patch.object(lvm,'grupo',return_value=grupo()),patch.object(lvm,'activa') as activa:
            with self.assertRaisesRegex(ValueError,'no autorizada'):enter.entra(cfg)
        activa.assert_not_called()

    def test_active_root_is_rejected_before_a_filesystem_probe(self):
        with patch.object(Path,'is_block_device',return_value=True),patch.object(enter,'es_raiz_activa',return_value=True), \
             patch.object(enter.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'entorno activo'):enter.entra(self.cfg())
        run.assert_not_called()

    def test_logical_volume_selection_cannot_be_ignored_for_an_unrelated_filesystem(self):
        cfg=self.cfg();cfg.lv='root'
        with patch.object(Path,'is_block_device',return_value=True),patch.object(enter,'es_raiz_activa',return_value=False), \
             patch.object(enter.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'ext4\n','')):
            with self.assertRaisesRegex(ValueError,'--lv requiere'):enter.entra(cfg)


if __name__=='__main__':unittest.main()
