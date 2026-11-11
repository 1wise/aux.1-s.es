#!/usr/bin/env python3
# Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
# Author & Credits: https://www.alawise.es/1-s
"""Plan or build AUX Live in a KVM guest; no host block device is an input."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile

DIR_APP=Path(__file__).resolve().parent
VERSION='7.0.0-beta.15'
HERRAMIENTAS=('livemedia-creator','ksvalidator','xorriso','implantisomd5','checkisomd5','openssl')


def valida_kvm():
    pth=Path('/dev/kvm')
    if not pth.exists() or not stat.S_ISCHR(pth.stat().st_mode) or not os.access(pth,os.R_OK|os.W_OK):
        raise ValueError('KVM no está disponible para este usuario. La compilación exige una VM KVM.')


def ram_disponible():
    dat=dict(lin.split(':',1) for lin in Path('/proc/meminfo').read_text().splitlines())
    return int(dat['MemAvailable'].split()[0])*1024


def lee_iso(args):
    res=subprocess.run(['xorriso',*args],capture_output=True,text=True)
    if res.returncode:
        detalle='\n'.join((res.stderr or res.stdout).splitlines()[-12:])
        raise ValueError('xorriso terminó con código '+str(res.returncode)+':\n'+detalle)
    return res


def datos_iso(pth):
    # A release tree can carry .treeinfo while its installer ISO carries only .discinfo.
    res=lee_iso(['-indev',str(pth),'-ls','/'])
    nombres={Path(nom).name for nom in shlex.split(res.stdout)}
    nom=next((nom for nom in ('.treeinfo','.discinfo') if nom in nombres),None)
    if not nom:raise ValueError('El instalador no contiene .discinfo ni .treeinfo.')
    with tempfile.TemporaryDirectory(prefix='aux-iso-info-') as tmp:
        dst=Path(tmp)/'metadata'
        lee_iso(['-osirrox','on','-indev',str(pth),'-extract','/'+nom,str(dst)])
        if not dst.is_file() or dst.stat().st_size>16384:raise ValueError('Metadatos del instalador inválidos.')
        txt=dst.read_text()
    if nom=='.treeinfo':
        cfg=configparser.ConfigParser(interpolation=None)
        try:cfg.read_string(txt)
        except configparser.Error as err:raise ValueError('.treeinfo inválido: '+str(err)) from err
        return cfg.get('general','version',fallback=''),cfg.get('general','arch',fallback='')
    lin=[val.strip() for val in txt.splitlines()]
    if len(lin)<3 or not re.fullmatch(r'\d+(?:\.\d+)?',lin[0]):
        raise ValueError('.discinfo incompleto o inválido.')
    # Lorax writes timestamp, release description and base architecture, in that order.
    # Format: https://github.com/weldr/lorax/blob/master/src/pylorax/discinfo.py
    ver=re.fullmatch(r'(?:Fedora(?:[- ][A-Za-z][A-Za-z0-9_]*)*[- ])?(\d+)',lin[1])
    etq=re.search(r"(?m)^Volume id\s*:\s*'([^']+)'\s*$",res.stderr+'\n'+res.stdout)
    vol=re.fullmatch(r'Fedora-[SE]-(?:dvd|netinst)-([a-z0-9_]+)-(\d+)',etq[1]) if etq else None
    if not ver and not vol:raise ValueError('No se reconoce la versión Fedora en .discinfo ni en la etiqueta ISO.')
    rel=ver[1] if ver else vol[2]
    arq=lin[2]
    if vol and (vol[1]!=arq or vol[2]!=rel):
        raise ValueError('.discinfo y la etiqueta ISO indican versiones o arquitecturas diferentes.')
    if not re.fullmatch(r'[a-z0-9_]+',arq):raise ValueError('Arquitectura inválida en .discinfo.')
    return rel,arq


def plan(cfg):
    iso=cfg.iso.expanduser().resolve(strict=True);sal=cfg.output.expanduser().resolve()
    if not iso.is_file() or iso.is_relative_to('/dev'):
        raise ValueError('El instalador debe ser un archivo ISO regular.')
    if not re.fullmatch(r'[a-fA-F0-9]{64}',cfg.sha256):raise ValueError('Indicar un SHA-256 verificado del instalador.')
    with iso.open('rb') as arc:sha=hashlib.file_digest(arc,'sha256').hexdigest()
    if sha!=cfg.sha256.lower():raise ValueError('El SHA-256 del instalador no coincide.')
    if sal.exists() or sal.is_relative_to(DIR_APP.parent) or sal.is_relative_to('/dev'):
        raise ValueError('Usar una salida NUEVA, fuera de las fuentes y de /dev.')
    if not sal.parent.is_dir():raise ValueError('El directorio padre de salida debe existir.')
    aus=[nom for nom in HERRAMIENTAS if shutil.which(nom) is None]
    if aus:raise ValueError('Faltan herramientas: '+', '.join(aus))
    valida_kvm()
    if not 4096<=cfg.ram<=65536 or cfg.ram*1024**2>ram_disponible()*.75:
        raise ValueError('RAM de VM fuera de límites o superior al 75% de MemAvailable.')
    if not 1<=cfg.vcpus<=max(1,os.cpu_count() or 1):raise ValueError('Número de CPU virtuales inválido.')
    if shutil.disk_usage(sal.parent).free<50*1024**3:raise ValueError('Reservar al menos 50 GiB libres para la construcción.')
    rel,arq=datos_iso(iso)
    if rel!='45' or arq!='x86_64':raise ValueError('Se requiere un netinst Fedora 45 x86_64; los metadatos indican '+rel+' / '+arq)
    raw=sal/('results/aux-assist-'+VERSION+'-raw-x86_64.iso')
    final=sal/('aux-assist-'+VERSION+'-x86_64.iso')
    cmd=['livemedia-creator','--make-iso','--iso='+str(iso),'--ks='+str(sal/'recipe/assist.ks'),
        '--releasever=45','--project=AUX Assist '+VERSION,'--volid=AUX_ASSIST_7',
        '--rootfs-type=squashfs','--dracut-conf='+str(DIR_APP/'dracut.conf'),
        '--extra-boot-args=aux.assist aux.ai.available=1 rd.live.overlay.overlayfs=1 rd.luks=0 rd.lvm=0 rd.md=0',
        '--ram='+str(cfg.ram),'--vcpus='+str(cfg.vcpus),'--tmp='+str(sal/'tmp'),
        '--iso-only','--iso-name='+raw.name,'--resultdir='+str(sal/'results'),
        '--logfile='+str(sal/'compile.log')]
    return {'version':VERSION,'installer':str(iso),'installer_sha256':sha,'output':str(sal),
            'virtualization':'KVM guest','guest_root_mib':16384,'ram_mib':cfg.ram,'vcpus':cfg.vcpus,
            'human_terminal_count':2,'raw_iso':str(raw),'final_iso':str(final),'command':cmd}


def ejecuta(cfg,dat):
    if os.geteuid()!=0:raise ValueError('La construcción necesita sudo. El plan puede revisarse sin root.')
    sal=Path(dat['output']);sal.mkdir(mode=0o700);(sal/'tmp').mkdir(mode=0o700)
    cmd=[sys.executable,str(DIR_APP/'prepare.py'),'--output',str(sal/'recipe')]
    if cfg.config:cmd+=['--config',str(cfg.config.resolve())]
    subprocess.run(cmd,check=True)
    subprocess.run(['ksvalidator','-v','F45',str(sal/'recipe/assist.ks')],check=True)
    # There is deliberately no path that selects Anaconda's host installation mode.
    subprocess.run(dat['command'],check=True)
    subprocess.run([sys.executable,str(DIR_APP/'finish.py'),'--input',dat['raw_iso'],
        '--output',dat['final_iso'],'--source-manifest',str(sal/'recipe/source-manifest.json')],check=True)
    print('ISO preparada:',dat['final_iso'])
    print('Probar BIOS/UEFI, consentimiento y ambas terminales antes de declararla validada.')


def main(argv=None):
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--iso',type=Path)
    par.add_argument('--sha256')
    par.add_argument('--output',type=Path)
    par.add_argument('--ram',type=int,default=8192,help='VM RAM in MiB')
    par.add_argument('--vcpus',type=int,default=min(4,os.cpu_count() or 1))
    par.add_argument('--config',type=Path,help='Public endpoint/model settings for the Live client')
    par.add_argument('--apply',action='store_true',help='Compile inside KVM after reviewing the default plan')
    par.add_argument('-i','--interactive',action='store_true')
    cfg=par.parse_args(argv)
    try:
        if cfg.interactive:
            sys.path.insert(0,str(DIR_APP.parent))
            from auxlib.console_ui import aplicacion,campo
            with aplicacion('AUX LIVE ISO / FEDORA 45','ejecucion'):
                cfg.iso=cfg.iso or Path(campo('ISO netinst Fedora 45 x86_64'))
                cfg.sha256=cfg.sha256 or campo('SHA-256 verificado del instalador')
                cfg.output=cfg.output or Path(campo('Directorio NUEVO de construcción, fuera de las fuentes'))
        if not cfg.iso or not cfg.sha256 or not cfg.output:par.error('Indicar --iso, --sha256 y --output, o usar --interactive.')
        dat=plan(cfg)
        print(json.dumps(dat,ensure_ascii=False,indent=2))
        if cfg.interactive:
            from auxlib.console_ui import aplicacion,campo
            with aplicacion('AUX LIVE ISO / FEDORA 45','ejecucion'):
                cfg.apply=campo('Escribir COMPILAR para construir en la VM; Enter conserva solo el plan',
                    resumen=['VM KVM: '+str(cfg.ram)+' MiB / '+str(cfg.vcpus)+' CPU',
                             'Disco virtual: 16384 MiB','Salida: '+dat['output']])=='COMPILAR'
        if cfg.apply:ejecuta(cfg,dat)
        else:print('Plan revisado. Añadir --apply para construir.\nComando VM: '+shlex.join(dat['command']))
        return 0
    except KeyboardInterrupt:return 130
    except (ValueError,OSError,subprocess.SubprocessError) as err:
        print('AUX LIVE ISO: '+str(err),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
