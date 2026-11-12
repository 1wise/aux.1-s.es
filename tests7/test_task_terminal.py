# Timestamp: 2026-11-10 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
"""Catch lost terminal input in the Bash/Python wrappers using a real PTY."""
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest


class TerminalTareas(unittest.TestCase):
    def test_enter_selects_device_and_lv_dicts_then_cancels_review_in_real_pty(self):
        raiz=Path(__file__).resolve().parents[1]
        # Only the storage operation is replaced; curses and both selection menus are real.
        codigo='''# Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
# Author & Credits: https://www.alawise.es/1-s
import json,sys
from pathlib import Path
from auxlib import enter,lvm
enter.detecta=lambda:[{'name':'/dev/vda','fstype':'LVM2_member','label':None,'size':'4G','mountpoints':[]}]
def revisa(cfg):
    dat={'name':'aux_test','volumes':[{'name':'raiz','uuid':'B'*32,'size':'2147483648','active':False,'segments':['linear']}]}
    ent=lvm.elige_volumen(cfg,dat)
    Path(sys.argv[1]).write_text(json.dumps({'device':str(cfg.device),'lv':ent['uuid'],'repair':cfg.repair,'apply':cfg.apply}))
enter.entra=revisa
enter.main(['-i'])
'''
        with tempfile.TemporaryDirectory() as tmp:
            registro=Path(tmp)/'review.json'
            master,slave=pty.openpty()
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0))
            proc=subprocess.Popen([sys.executable,'-c',codigo,str(registro)],stdin=slave,stdout=slave,stderr=slave,
                cwd=raiz,env={**os.environ,'TERM':'xterm-256color','LANG':'C.UTF-8'},start_new_session=True)
            os.close(slave);dat=b'';paso=0;limite=time.monotonic()+8
            hitos=[b'Elegir el sistema de destino',b'Modo de entrada',b'Grupo LVM aux_test',b'Escribir ABRIR']
            try:
                while time.monotonic()<limite:
                    if select.select([master],[],[],0.1)[0]:
                        try:trozo=os.read(master,65536)
                        except OSError:break
                        if not trozo:break
                        dat+=trozo
                    if paso<len(hitos) and hitos[paso] in dat:
                        os.write(master,b'\n');paso+=1
                    if proc.poll() is not None:break
                if proc.poll() is None:proc.kill()
                proc.wait()
            finally:
                if proc.poll() is None:proc.kill();proc.wait()
                os.close(master)
            self.assertEqual(paso,4,dat.decode(errors='replace'))
            self.assertEqual(proc.returncode,0,dat.decode(errors='replace'))
            self.assertNotIn(b'Traceback',dat)
            self.assertEqual(json.loads(registro.read_text()),{'device':'/dev/vda','lv':'B'*32,'repair':False,'apply':False})

    def test_interactive_wrappers_show_their_identity_and_cancel(self):
        raiz=Path(__file__).resolve().parents[1]
        for nom in ('download','deploy','generate'):
            with self.subTest(application=nom):
                master,slave=pty.openpty()
                fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,120,0,0))
                proc=subprocess.Popen(['bash',str(raiz/(nom+'.sh')),'-i'],stdin=slave,stdout=slave,stderr=slave,
                                      cwd=raiz,env={**os.environ,'TERM':'xterm-256color'},start_new_session=True)
                os.close(slave);dat=b'';enviado=False;limite=time.monotonic()+8
                try:
                    while time.monotonic()<limite:
                        if select.select([master],[],[],0.1)[0]:
                            try:trozo=os.read(master,65536)
                            except OSError:break
                            if not trozo:break
                            dat+=trozo
                        if ('AUX '+nom.upper()).encode() in dat and not enviado:
                            os.write(master,b'q');enviado=True
                        if proc.poll() is not None:break
                    if proc.poll() is None:proc.kill()
                    proc.wait()
                finally:
                    if proc.poll() is None:proc.kill();proc.wait()
                    os.close(master)
                self.assertTrue(enviado,dat.decode(errors='replace'))
                self.assertEqual(proc.returncode,130,dat.decode(errors='replace'))
                self.assertNotIn(b'Traceback',dat)


if __name__=='__main__':unittest.main()
