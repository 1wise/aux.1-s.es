# Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
# Author & Credits: https://www.alawise.es/1-s
"""Emit complete progress lines so parallel transfers never corrupt the terminal."""
import hashlib
import subprocess
import sys
import tempfile
import threading
import time

LOCK=threading.Lock()


def evento(rec_id,stage,detail):
    with LOCK:print('['+rec_id+'] '+stage+' | '+str(detail),file=sys.stderr,flush=True)


def tamano(value):
    return f'{value/1024**3:.2f} GiB' if value>=1024**3 else f'{value/1024**2:.1f} MiB'


def verifica(path,ent):
    evento(ent['id'],'VERIFY','SHA-256 · '+tamano(path.stat().st_size))
    digest=hashlib.sha256();total=path.stat().st_size;done=0;start=last=time.monotonic()
    with path.open('rb') as stream:
        while chunk:=stream.read(4*1024**2):
            digest.update(chunk);done+=len(chunk);now=time.monotonic()
            if now-last>=2:
                evento(ent['id'],'VERIFY',f'{100*done/max(1,total):.0f}% · '+tamano(done));last=now
    result=digest.hexdigest();evento(ent['id'],'VERIFY','OK' if result==ent['sha256'] else 'ERROR · checksum distinto')
    return result


def transfiere(command,partial,ent):
    # Curl's progress is captured; periodic complete lines include the resource identity.
    start=last=time.monotonic();initial=partial.stat().st_size if partial.exists() else 0
    evento(ent['id'],'DOWNLOAD',('Reanudar desde '+tamano(initial) if initial else 'Iniciar')+' · '+ent['original_url'])
    with tempfile.TemporaryFile(mode='w+t') as errors:
        proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors,text=True)
        while True:
            try:out,_=proc.communicate(timeout=1);break
            except subprocess.TimeoutExpired:
                now=time.monotonic()
                if now-last<2:continue
                done=partial.stat().st_size if partial.exists() else 0;total=ent.get('size_bytes')
                percent=f'{100*done/total:.0f}% · ' if total else ''
                speed=max(0,done-initial)/max(.001,now-start)
                evento(ent['id'],'DOWNLOAD',percent+tamano(done)+' / '+(tamano(total) if total else 'tamaño pendiente')+' · '+tamano(speed)+'/s');last=now
        errors.seek(0);err=errors.read()
    return subprocess.CompletedProcess(command,proc.returncode,out,err)
