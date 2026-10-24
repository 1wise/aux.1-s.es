#!/usr/bin/env python3
# Timestamp: 2026-10-24 | Version: 6.4.0-dev.1
# Author & Credits: https://www.alawise.es/1-s
"""Build a new regular disk-image file; never select or write a physical USB."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
import portable_menu as menu

ROOT=Path(__file__).resolve().parent
PAR_LIV = ('ai.py', 'ai_agent.py', 'assist.py', 'agent.py', 'support_case.py', 'remote-shell.sh')
MIB=1024**2


def orden(*args, **kwargs):return subprocess.run(list(map(str,args)),check=True,**kwargs)


def sha(pth):
    with Path(pth).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def comando(*noms):
    for nom in noms:
        pth=shutil.which(nom)
        if pth:return pth
    raise ValueError('Falta dependencia: '+' / '.join(noms))


def comprueba_archivo(pth):
    pth=Path(pth)
    if pth.is_symlink() or not pth.is_file() or not stat.S_ISREG(pth.stat().st_mode):
        raise ValueError('Se requiere un archivo regular: '+str(pth))
    return pth.resolve()


def plan(iso,digest,capacity,keep):
    iso=comprueba_archivo(iso)
    if not re.fullmatch('[a-fA-F0-9]{64}',digest) or sha(iso)!=digest.lower():
        raise ValueError('SHA-256 de la ISO incorrecto.')
    if capacity<iso.stat().st_size*(2 if keep else 1)+768*MIB:
        raise ValueError('Capacidad insuficiente para ISO, arranque y espacio de trabajo.')
    if capacity%512:raise ValueError('La capacidad debe ser múltiplo de 512 bytes.')
    return {'schema':menu.SCHEMA,'version':menu.VERSION,'capacity_bytes':capacity,
            'iso_sha256':digest.lower(),'iso_size_bytes':iso.stat().st_size,
            'keep_iso_file':keep,'firmware':['BIOS','UEFI x86_64'],'secure_boot_verified':False,
            'default_boot':'aux-persistent','boot_timeout_seconds':5,
            'support_resume':{'required_for_release':True,'implemented':True,'live_verified':False},
            'api_key_preload':{'directory':'AUX/private/api','profile':'persistent USB','keys_in_build':False},
            'layout':[{'partition':1,'type':'BIOS boot','size_mib':1},
                      {'partition':2,'type':'EFI FAT32','size_mib':64},
                      {'partition':3,'type':'ext4','use':'compressed base, persistent root, work and storage; remaining space'}],
            'free_space':'measured after building; no fixed 30 GB promise'}


def verifica_loop(loop,archivo):
    if not re.fullmatch(r'/dev/loop\d+',loop):raise ValueError('No se ha obtenido un dispositivo loop seguro.')
    dat=json.loads(orden('losetup','--json','--list','--output','NAME,BACK-FILE',loop,
                         capture_output=True,text=True).stdout)['loopdevices']
    if len(dat)!=1 or Path(dat[0]['back-file']).resolve()!=archivo.resolve():
        raise ValueError('El loop no corresponde al archivo nuevo; se detiene antes de formatear.')


def escribe(pth,txt,modo=0o644):
    pth.parent.mkdir(parents=True,exist_ok=True)
    pth.write_text(txt)
    pth.chmod(modo)


def instala_api(upper, mnt):
    # The standalone kit carries the same reviewed public payload as the source tree.
    patch = ROOT / 'live-patch'
    if not patch.is_dir():
        patch = ROOT.parent / 'payload'
    if not patch.is_dir():
        patch = ROOT.parent.parent / 'iso-assist/payload'
    for nom in PAR_LIV:
        src = comprueba_archivo(patch / nom)
        dst = upper / 'usr/share/aux-assist' / nom
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for prov, uni in (('openai', 'aux-gpt'), ('gemini', 'aux-gemini')):
        escribe(upper / ('etc/systemd/system/' + uni + '.service.d/api-keys.conf'),
                '# Timestamp: 2026-10-17 | Version: '+menu.VERSION+'\n'
                '# Author & Credits: https://www.alawise.es/1-s\n'
                '[Service]\nLoadCredential='+prov+'.key:/run/aux-api-source/'+prov+'.key\n')
    for rel in ('AUX/private', 'AUX/private/api'):
        (mnt / rel).mkdir(mode=0o700, exist_ok=True)
        (mnt / rel).chmod(0o700)


def construye(iso,ipxe,suma_ipxe,out,datos):
    if os.geteuid()!=0:raise ValueError('--build requiere root en el constructor Fedora; el plan no.')
    if out.exists() or out.is_symlink() or out.with_suffix(out.suffix+'.partial').exists():
        raise ValueError('Elegir una salida NUEVA; no se reemplazan imágenes previas.')
    for nom in ('xorriso','losetup','sgdisk','mkfs.ext4','mkfs.vfat','mount','umount','blkid','udevadm','setfiles'):
        comando(nom)
    grub_install=comando('grub2-install','grub-install')
    grub_standalone=comando('grub2-mkstandalone','grub-mkstandalone')
    politica=Path('/etc/selinux/targeted/contexts/files/file_contexts')
    if not politica.is_file():raise ValueError('Construir en Fedora con la política SELinux targeted instalada.')
    ipxe=comprueba_archivo(ipxe)
    if not re.fullmatch('[a-fA-F0-9]{64}',suma_ipxe) or sha(ipxe)!=suma_ipxe.lower():
        raise ValueError('SHA-256 del cargador iPXE incorrecto.')
    uid=str(uuid.uuid4());datos=datos|{'filesystem_uuid':uid,'ipxe_image_sha256':suma_ipxe.lower()}
    out.parent.mkdir(parents=True,exist_ok=True)
    parcial=out.with_suffix(out.suffix+'.partial')
    loop=None;montados=[];pth_tmp=None
    try:
        with parcial.open('xb') as stream:stream.truncate(datos['capacity_bytes'])
        orden('sgdisk','--clear','--new=1:2048:+1M','--typecode=1:ef02','--change-name=1:AUX-BIOS',
              '--new=2:4096:+64M','--typecode=2:ef00','--change-name=2:AUX-EFI',
              '--new=3:0:0','--typecode=3:8300','--change-name=3:AUX-PORTABLE',parcial)
        loop=orden('losetup','--find','--show','--partscan',parcial,capture_output=True,text=True).stdout.strip()
        verifica_loop(loop,parcial)
        orden('udevadm','settle','--timeout=15')
        efi,base=Path(loop+'p2'),Path(loop+'p3')
        if not efi.is_block_device() or not base.is_block_device():
            raise ValueError('No aparecen las particiones del loop; no se formatea otra ruta.')
        verifica_loop(loop,parcial)
        orden('mkfs.vfat','-F','32','-n','AUX-EFI',efi)
        orden('mkfs.ext4','-F','-m','0','-i','65536','-J','size=64','-U',uid,'-L','AUX-PORTABLE',base)
        pth_tmp=Path(tempfile.mkdtemp(prefix='aux-portable-'))
        with contextlib.nullcontext(pth_tmp) as tmp:
            tmp=Path(tmp);mnt=tmp/'root';esp=tmp/'efi';mnt.mkdir();esp.mkdir()
            orden('mount',base,mnt);montados.append(mnt)
            orden('mount',efi,esp);montados.append(esp)
            cfg_iso=tmp/'source-grub.cfg'
            orden('xorriso','-osirrox','on','-indev',iso,'-extract','/boot/grub2/grub.cfg',cfg_iso)
            if 'aux.assist' not in cfg_iso.read_text():
                raise ValueError('La ISO no declara aux.assist; no se anuncia un menú de asistencia compatible.')
            for nom in ('AUX/base','AUX/ipxe','AUX/boot','AUX/data/work','AUX/data/storage',
                        'AUX/persist/upper','AUX/persist/ovlwork','LiveOS/base','LiveOS/clean'):
                (mnt/nom).mkdir(parents=True,exist_ok=True)
            for src,dst in (('/images/pxeboot/vmlinuz','AUX/base/vmlinuz'),
                            ('/images/pxeboot/initrd.img','AUX/base/initrd.img'),
                            ('/LiveOS/squashfs.img','LiveOS/base/squashfs.img')):
                orden('xorriso','-osirrox','on','-indev',iso,'-extract',src,mnt/dst)
                if (mnt/dst).stat().st_size<1024:raise ValueError('Componente Live vacío: '+src)
            # The clean and persistent profiles share one compressed inode, not two copies.
            os.link(mnt/'LiveOS/base/squashfs.img',mnt/'LiveOS/clean/squashfs.img')
            for nom in ('ipxe.lkrn','ipxe.efi'):
                orden('xorriso','-osirrox','on','-indev',ipxe,'-extract','/ipxe/'+nom,mnt/'AUX/ipxe'/nom)
            upper=mnt/'AUX/persist/upper'
            for src,rel in (('runtime.py','usr/share/aux-assist/portable_usb.py'),
                            ('portable_menu.py','usr/share/aux-assist/portable_menu.py')):
                dst=upper/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/src,dst)
            instala_api(upper, mnt)
            escribe(upper/'etc/systemd/system/tech-work.service.d/portable.conf',
                    '# Timestamp: 2026-10-17 | Version: '+menu.VERSION+'\n# Author & Credits: https://www.alawise.es/1-s\n'
                    '[Service]\nExecStart=\nExecStart=/usr/bin/python3 /usr/share/aux-assist/portable_usb.py work\n')
            escribe(upper/'etc/dracut.conf.d/90-aux-portable.conf',
                    '# Timestamp: 2026-10-17 | Version: '+menu.VERSION+'\n# Author & Credits: https://www.alawise.es/1-s\n'
                    'hostonly="no"\nhostonly_cmdline="no"\nadd_dracutmodules+=" dmsquash-live livenet network-manager "\n')
            orden('setfiles','-F','-r',upper,politica,upper)
            (mnt/'AUX/persist/upper').chmod(0o700);(mnt/'AUX/persist/ovlwork').chmod(0o700)
            for nom in ('AUX/data','AUX/data/work','AUX/data/storage'):(mnt/nom).chmod(0o700)
            if datos['keep_iso_file']:shutil.copyfile(iso,mnt/'AUX/base.iso')
            escribe(mnt/'AUX/menu.cfg',menu.menu(uid))
            stub=menu.stub(uid)
            for rel in ('boot/grub/grub.cfg','boot/grub2/grub.cfg'):escribe(mnt/rel,stub)
            cfg_emb=tmp/'grub.cfg';cfg_emb.write_text(stub)
            (esp/'EFI/BOOT').mkdir(parents=True)
            orden(grub_standalone,'--format=x86_64-efi','--locales=','--fonts=',
                  '--modules=part_gpt fat ext2 normal linux chain search search_fs_uuid configfile reboot halt fwsetup',
                  '--output='+str(esp/'EFI/BOOT/BOOTX64.EFI'),'boot/grub/grub.cfg='+str(cfg_emb))
            verifica_loop(loop,parcial)
            orden(grub_install,'--target=i386-pc','--boot-directory='+str(mnt/'boot'),'--recheck',loop)
            # Some distributions name the BIOS prefix grub2; keep both stubs identical.
            for rel in ('boot/grub/grub.cfg','boot/grub2/grub.cfg'):escribe(mnt/rel,stub)
            fs=os.statvfs(mnt)
            datos['initial_available_bytes']=fs.f_bavail*fs.f_frsize
            datos['status']='experimental image; real BIOS/UEFI/persistence/kernel acceptance pending'
            escribe(mnt/'AUX/manifest.json',json.dumps(datos,indent=2)+'\n')
            orden('sync')
            for pth in reversed(montados):orden('umount',pth)
            montados.clear()
        orden('losetup','--detach',loop);loop=None
        parcial.rename(out)
        escribe(out.with_suffix(out.suffix+'.json'),json.dumps(datos,indent=2)+'\n')
        escribe(out.with_suffix(out.suffix+'.sha256'),sha(out)+'  '+out.name+'\n')
        print('Imagen construida:',out,'· espacio libre inicial:',datos['initial_available_bytes'],'bytes')
    finally:
        quedan=[]
        for pth in reversed(montados):
            if subprocess.run(['umount',str(pth)],check=False).returncode:quedan.append(pth)
        if loop:subprocess.run(['losetup','--detach',loop],check=False)
        # Never recursively remove a directory containing a mount that failed to detach.
        if pth_tmp and not quedan:shutil.rmtree(pth_tmp)
        if quedan:print('Quedaron montajes de la imagen por revisar:',','.join(map(str,quedan)))


def main():
    par=argparse.ArgumentParser(description=__doc__)
    par.add_argument('--iso',type=Path,required=True)
    par.add_argument('--sha256',required=True)
    par.add_argument('--ipxe-image',type=Path)
    par.add_argument('--ipxe-sha256')
    par.add_argument('--output',type=Path,required=True)
    par.add_argument('--capacity-bytes',type=int,required=True,help='Actual target capacity; multiple of 512; image-file size only')
    par.add_argument('--keep-iso',action='store_true',help='Also keep the original .iso file, in addition to the deployed Live payload')
    par.add_argument('--build',action='store_true')
    cfg=par.parse_args()
    try:
        if str(cfg.output.absolute()).startswith('/dev/'):
            raise ValueError('La salida debe ser un archivo nuevo fuera de /dev, nunca un dispositivo.')
        dat=plan(cfg.iso,cfg.sha256,cfg.capacity_bytes,cfg.keep_iso)
        print(json.dumps(dat,indent=2))
        if not cfg.build:
            print('Solo plan. --build crea un archivo de imagen nuevo; nunca graba una llave física.')
            return 0
        if not cfg.ipxe_image or not cfg.ipxe_sha256:raise ValueError('--build requiere imagen iPXE y su SHA-256.')
        construye(cfg.iso.resolve(),cfg.ipxe_image,cfg.ipxe_sha256,cfg.output.absolute(),dat)
        return 0
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        print('Construcción detenida:',exc)
        return 1


if __name__=='__main__':raise SystemExit(main())
