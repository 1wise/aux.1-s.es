#!/usr/bin/env python3
# Timestamp: 2026-11-17 | Version: 7.0.1-beta.4
# Author & Credits: https://www.alawise.es/1-s
"""Build independently extractable native service packages without runtime state."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile

PTH_SRC=Path(__file__).resolve().parent
VERSION=(PTH_SRC/'VERSION').read_text().strip()
EXCL={'.git','.openai','__pycache__','state','dist','.venv','node_modules'}


def archivos(modulo):
    todos=[p for p in sorted(PTH_SRC.rglob('*')) if p.is_file() and not p.is_symlink()
        and not set(p.relative_to(PTH_SRC).parts)&EXCL and p.suffix!='.pyc' and p!=PTH_SRC/'SHA256SUMS'
        and p.relative_to(PTH_SRC).parts[0] not in ('html','isos','public','packages','cache','logs')
        and not p.name.startswith('.env') and p.suffix not in ('.pem','.key')]
    if modulo=='aux-pxe':
        return [p for p in todos if p.relative_to(PTH_SRC).parts[0] not in ('tec','cli')]
    comunes={'install-web.py','fast-boot.json','VERSION','package-modules.py'}
    return [p for p in todos if p.relative_to(PTH_SRC).as_posix() in comunes
        or p.relative_to(PTH_SRC).parts[0]=='cli'
        or p.relative_to(PTH_SRC).parts[:2]==('tec','web')
        or (p.relative_to(PTH_SRC).parts[0]=='tec' and len(p.relative_to(PTH_SRC).parts)==2)
        or p.relative_to(PTH_SRC).as_posix() in ('docs/MODULES.md','nginx/tec-cli.conf.example')]


def empaqueta(destino):
    if (PTH_SRC/'web').is_dir() or (PTH_SRC/'html').is_dir() or (PTH_SRC/'isos').is_dir():
        raise ValueError('Empaquetar desde fuentes limpias, separadas de la instalación y sus medios.')
    destino=Path(destino);destino.mkdir(parents=True,exist_ok=True);sal=[]
    for modulo in ('aux-pxe','tec-cli'):
        payload={p.relative_to(PTH_SRC).as_posix():p.read_bytes() for p in archivos(modulo)}
        def publico(dat):
            if isinstance(dat,dict):
                return {k: None if ((re.search(r'(?:^|_)(?:password|passwd|token|api_key|secret|access_key)$',k,re.I) and not k.endswith(('_file','_env'))) or k in ('ftp_host','ftp_user')) else publico(v) for k,v in dat.items()}
            if isinstance(dat,list):return [publico(v) for v in dat]
            return dat
        payload['fast-boot.json']=(json.dumps(publico(json.loads(payload['fast-boot.json'])),ensure_ascii=False,indent=2)+'\n').encode()
        meta={'module':modulo,'version':VERSION,'requires_other_module':False,
            'runtime':'Python 3 + Bash' if modulo=='aux-pxe' else 'PHP 8.1+ + Python 3 gateway',
            'private_state_included':False,'installation':'python3 install-web.py --modules '+modulo}
        payload['modules/'+modulo+'.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
        payload['README-MODULE.md']=('# '+modulo+' · '+VERSION+'\n\nExtraer en un directorio vacío.\n\n'
            'Plan sin modificar el sistema:\n\n    python3 install-web.py --modules '+modulo+'\n\n'
            'Aplicar después de revisar rutas, dependencias y TLS:\n\n    sudo python3 install-web.py --modules '+modulo+' --apply\n\n'
            'Los vhosts son opcionales con --nginx. No se instala el otro módulo.\n'
            'Guía: docs/MODULES.md. Los paquetes no incluyen ISO, cuentas ni secretos.\n').encode()
        payload['SHA256SUMS']=''.join(hashlib.sha256(b).hexdigest()+'  '+n+'\n' for n,b in sorted(payload.items())).encode()
        arc=destino/(modulo+'-'+VERSION+'.zip')
        with zipfile.ZipFile(arc,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for nom,byt in sorted(payload.items()):
                ent=zipfile.ZipInfo(nom,date_time=(2026,11,17,0,0,0));ent.compress_type=zipfile.ZIP_DEFLATED
                ent.external_attr=(0o100755 if nom.endswith('.sh') or nom in ('aux','aux-setup','aux-profile','aux-catalog','aux-enter','aux-assist','aux-tools','aux-images','aux-config','aux-release','aux-observe') else 0o100644)<<16
                z.writestr(ent,byt)
        digest=hashlib.sha256(arc.read_bytes()).hexdigest()
        Path(str(arc)+'.sha256').write_text(digest+'  '+arc.name+'\n')
        sal.append({'module':modulo,'filename':arc.name,'size_bytes':arc.stat().st_size,'sha256':digest,'entries':len(payload)})
    (destino/'modules.json').write_text(json.dumps({'version':VERSION,'modules':sal},indent=2)+'\n')
    return sal


if __name__=='__main__':
    par=argparse.ArgumentParser(description=__doc__);par.add_argument('--output',type=Path,required=True)
    print(json.dumps(empaqueta(par.parse_args().output),ensure_ascii=False))
