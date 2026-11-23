# Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
# Author & Credits: https://www.alawise.es/1-s
"""Prepare a kernel workbench through the existing ISO/root/native installers."""
from pathlib import Path
import shutil
from .common import DIR_APP,guarda_json,atomico
from . import VERSION

ROLE='kernel-modeler'
PACKAGES={
 'fedora':'file gcc gcc-c++ make binutils bc bison flex ncurses-devel openssl-devel elfutils-libelf-devel dwarves perl python3 cpio tar xz zstd lz4 git patch diffutils findutils pkgconf-pkg-config kmod dtc dracut openssl gnupg2 qemu-system-x86-core edk2-ovmf pesign mokutil',
 'debian':'file build-essential bc bison flex libncurses-dev libssl-dev libelf-dev dwarves perl python3 cpio tar xz-utils zstd lz4 git patch diffutils findutils pkg-config kmod device-tree-compiler initramfs-tools openssl gpg qemu-system-x86 ovmf sbsigntool mokutil',
 'alpine':'file build-base bash bc bison flex ncurses-dev openssl-dev elfutils-dev pahole perl python3 cpio tar xz zstd lz4 git patch diffutils findutils pkgconf kmod dtc mkinitfs openssl gnupg qemu-system-x86_64 ovmf sbsigntool mokutil',
}


def normaliza(cfg):
    """A workbench is a package preset; it never silently selects the running host."""
    if cfg.mode!=ROLE:return cfg
    target=getattr(cfg,'target_mode',None)
    if target not in ('iso','root','existing'):raise ValueError('Kernel Modeler requiere --target-mode iso, root o existing.')
    cfg.workbench=ROLE;cfg.mode=target
    requested=getattr(cfg,'roles',None)
    cfg.roles=','.join(dict.fromkeys(['base',ROLE]+(requested.split(',') if requested else [])))
    if not getattr(cfg,'native',None):
        from .software import minimo
        cfg.native=minimo(cfg.distro)
    return cfg


def manifest(dis,packages):
    return {'schema':'aux-kernel-modeler-v1','version':VERSION,'distribution':dis,
            'target_architecture':None,'toolchain_scope':'builder-native','vm_test_architecture':'x86_64','packages':list(packages),
            'kernel_source':{'version':None,'url':None,'sha256':None,'signature':'not-checked'},
            'model':{'base_config':None,'hardware_inventory':None,'modules':None,'firmware':None,'initramfs':None,'boot_method':None},
            'security_review':'pending','kernel_build':'not-run','module_signing':'not-run',
            'secure_boot_enrollment':'not-run','boot_test':'not-tested',
            'workflow':['verify-source','select-hardware-and-config','resolve-kconfig','review-hardening','build-outside-source','prepare-modules-and-initramfs','review-signing','test-in-vm','record-real-boot']}


def escribe(destino,dis,packages):
    dst=Path(destino);dst.mkdir(parents=True,exist_ok=True)
    guarda_json(dst/'model.json',manifest(dis,packages))
    shutil.copyfile(DIR_APP/'docs/KERNEL-MODELER-8.md',dst/'README.md')
    # This is a review record, not a claim that a kernel has already been built.
    atomico(dst/'packages.txt','\n'.join(packages)+'\n')


def instala(raiz,dis):
    from .profiles import seleccion
    packages=seleccion(dis,['base',ROLE])['packages']
    # Keep review templates public and private build work outside the web tree.
    dst=Path(raiz)/'usr/local/share/aux/kernel-modeler'
    if not (dst/'model.json').exists():escribe(dst,dis,packages)
    (Path(raiz)/'work/kernel-modeler').mkdir(parents=True,exist_ok=True,mode=0o700)


def resumen(dis):
    return ['Kernel Modeler · banco de trabajo para núcleos Linux',
            'Configurar: menuconfig/nconfig; compilar: GCC, make, binutils, flex/bison; inspeccionar: ELF/BTF.',
            'Preparar initramfs, revisar firmas y probar BIOS/UEFI con QEMU/OVMF.',
            'Paquetes específicos de '+dis+': '+PACKAGES[dis],
            'El preset prepara herramientas y fichas. Kernel y fuentes exactos, hardening y prueba hasta login se completan en el banco de trabajo.']
