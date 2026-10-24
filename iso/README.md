# TEC / Fedora 44 Rescue — 5.0.1-dev.5

Timestamp: 2026-10-12 | Version: 5.0.1-dev.5
Author & Credits: https://www.alawise.es/1-s

Receta Live x86_64 independiente de AUX/PXE y del backend TEC. Dev.5 prepara
la base de rescate y asistencia directa por SSH. Fuentes comprobadas; todavía
no se ha compilado ni arrancado esta ISO. Conservar la 0.1.0 probada.

## Utilidades

`packages.txt` contiene 94 paquetes solicitados, editables uno por línea. RPM
añadirá sus dependencias obligatorias. El ZIP incluye fuentes, no RPM ni una ISO.

| Uso | Utilidades / paquetes principales |
| --- | --- |
| Terminal | root /bin/bash, tmux, nano, less, htop, file, strace, lsof |
| Navegación y transferencias | links, wget (wget2-wget), curl, ftp, rsync, ssh/scp/sftp |
| Fedora | rpm, dnf5/dnf, fedora-repos, claves GPG, certificados CA |
| Red | nmcli/nmtui, ip/ss, ping, dig, ethtool, traceroute, tcpdump |
| VPN manual | wg/wg-quick; sin peers ni claves privadas incorporadas |
| Discos | lsblk, blkid, parted, gdisk, mount/umount |
| Sistemas de archivos | ext4, FAT, XFS, Btrfs, NTFS: montaje y reparación |
| Volúmenes | mdadm, lvm2, cryptsetup |
| Diagnóstico | smartctl, nvme, pciutils, usbutils |
| Recuperación | ddrescue con mapfile, TestDisk, PhotoRec |
| Arranque | efibootmgr, grub2-tools, grub2-efi-x64-cdboot, cargadores BIOS/UEFI |
| Trabajo y chroot | tar, gzip, bzip2, xz, zstd, unzip, chroot |

Ethernet y Wi-Fi incluidos por defecto: NetworkManager-wifi, wpa_supplicant y
linux-firmware están en `packages.txt`. El firmware aumenta el peso y también
cubre adaptadores Ethernet que lo necesitan. Revisar Cari con `lspci -nnk` y
`lsusb`. No hay compatibilidad universal probada. Sin escritorio ni Anaconda precargado. Dnf
permite instalar paquetes adicionales; un instalador requiere validación aparte.

## RAM y acceso

Rootfs comprimido con overlayfs en RAM. `/work` es tmpfs, con límite mínimo entre
25 % de RAM total, un tercio de RAM disponible al iniciar y 2 GiB. Es un techo,
no una reserva: rootfs descargado por PXE, overlay y /work comparten memoria.
Comprobar `free -h` y `df -h / /work` antes de extracciones grandes o un stage3.
El límite de /work puede ampliarse manualmente después de comprobar memoria.

No se configuran montajes de discos ni swap persistente. Cerrar conserva /work;
reiniciar pierde los cambios del Live. Las modificaciones manuales en discos
persisten. Las claves SSH efímeras y sesiones tmux se eliminan al cerrar.

Ctrl-Alt-F6: selección, autorización y cierre. Ctrl-Alt-F7: terminal del técnico,
tmux en solo lectura. Ctrl-Alt-F8: estado y RAM sin shell. El técnico autorizado
dispone de root: los visores no son una barrera frente a ese técnico. No hay
auto-login ni contraseña root compartida.

SSH abre el puerto 2222 solo tras AUTORIZO, con la clave pública elegida y terminal
forzada. El listener no permite SFTP ni túneles; sí existen clientes de
transferencia saliente en la shell del técnico. La opción P carga perfiles públicos
de https://tec.1-s.es/profiles.php; TEC debe estar desplegado con perfiles aprobados.
También se admite pegar una clave pública o su URL HTTPS.

Se requiere ruta directa o VPN ya configurada. Dev.5 no crea peers, no conecta
automáticamente a Excalibur ni envía solicitudes por correo. La importación
USB/VPN privada y API de sesiones siguen pendientes.

## Compilar en Fedora 44 x86_64

Lorax se ejecuta en modo virtual, instalando en un disco virtual de construcción.
No usar esta receta como Kickstart de un equipo real: contiene clearpart para ese
disco virtual. No usar --no-virt en Excalibur. Dependencias del constructor:

```bash
sudo dnf install lorax lorax-lmc-virt pykickstart openssl xorriso squashfs-tools
```

Utilizar Fedora Server netinst 44 x86_64 oficial, verificado con su CHECKSUM
firmado. Sirve de instalador de construcción; su runtime no entra en el Live.
Desde el ZIP descomprimido, preparación independiente:

```bash
python3 prepare.py --output work-5.0.1-dev.5
ksvalidator -v F44 work-5.0.1-dev.5/assist.ks
```

Wi-Fi ya se incorpora con ese comando. El antiguo argumento --wifi se acepta
por compatibilidad y no cambia la selección de paquetes.

Lorax controla el modo de pantalla del instalador de construcción. El Kickstart
no debe incluir text, cmdline ni graphical; ksvalidator solo comprueba la sintaxis
Kickstart y no detecta por sí mismo esta restricción de Lorax. prepare.py también
comprueba esta condición antes de generar los archivos.

El disco virtual utiliza una raíz ext4 de 8 GiB y reqpart para crear las
particiones que requiere el firmware del constructor: biosboot en BIOS/GPT o
EFI en UEFI. No añadir autopart: el resto del esquema sigue definido mediante
part. El particionado se ejecuta dentro de la VM de construcción, no al arrancar
la ISO de rescate.

Los archivos de arranque UEFI para medios requieren grub2-efi-x64-cdboot dentro
del Live, además de shim-x64 y grub2-tools. grub2-efi-x64 por sí solo no aporta
gcdx64.efi. Si los binarios no están bajo /boot/efi, el %post prepara las copias
desde los archivos versionados de los RPM en /usr/lib/efi/grub2 y /usr/lib/efi/shim.
La operación ocurre dentro de la imagen y conserva los binarios ya presentes.
Comprueba gcdx64.efi, shimx64.efi, mmx64.efi y unicode.pf2 antes de empaquetar.
Lorax crea EFI/BOOT e images/efiboot.img a partir de ellos;
no crear un directorio vacío para ocultar el error de xorriso.

Comando de compilación; sustituir --iso por la ruta real del netinst oficial:

```bash
sudo livemedia-creator \
  --make-iso \
  --iso=/ruta/Fedora-Server-netinst-x86_64-44-1.7.iso \
  --ks="$PWD/work-5.0.1-dev.5/assist.ks" \
  --releasever=44 \
  --project="1-s TEC Rescue" \
  --volid=TEC_RESCUE_501 \
  --rootfs-type=squashfs \
  --dracut-conf="$PWD/dracut.conf" \
  --extra-boot-args="aux.assist rd.live.overlay.overlayfs=1 rd.luks=0 rd.lvm=0 rd.md=0" \
  --ram=4096 --vcpus=2 \
  --iso-only \
  --iso-name=tec-fedora44-assist-5.0.1-dev.5-x86_64.iso \
  --resultdir="$PWD/results-5.0.1-dev.5" \
  --logfile="$PWD/compile-5.0.1-dev.5.log"
```

Resultados en una carpeta nueva; prever al menos 20 GiB libres. Los 4096 MiB son
para la VM del constructor, no un mínimo medido del cliente. Si falta KVM, revisar
`livemedia-creator --help` y añadir --no-kvm para emulación más lenta.

Para perfiles públicos fijos, añadir `--profiles perfiles-publicos.json` a
prepare.py. No incorporar claves privadas a una ISO de distribución general.
La receta falla si faltan paquetes o comandos prometidos; validar F44 con
ksvalidator antes de construir. Usa actualizaciones de release 44: no es
reproducible bit a bit sin fijar un mirror snapshot y versiones RPM. Cada
preparación genera una contraseña desconocida y guarda solo su hash para mantener
root disponible por clave SSH; autenticación por contraseña deshabilitada.

## Inventario real y aceptación

Después de compilar:

```bash
cd results-5.0.1-dev.5
sha256sum tec-fedora44-assist-5.0.1-dev.5-x86_64.iso > tec-fedora44-assist-5.0.1-dev.5-x86_64.iso.sha256
du -h tec-fedora44-assist-5.0.1-dev.5-x86_64.iso
```

Dentro del Live, desde SSH autorizado:

```bash
cat /usr/share/aux-assist/packages-requested.txt
sort /usr/share/aux-assist/packages-rpm.txt
free -h
df -h / /work
findmnt -t tmpfs,overlay,squashfs
getent passwd root
dnf repolist
dnf install -y tree
rpm -q tree
```

Medir peso ISO, RAM inicial y descarga PXE. Probar BIOS/UEFI en VM sin discos de
cliente. Comprobar listener cerrado antes/después, rechazo de otra clave, huellas,
SELinux enforcing y ausencia de efecto al escribir/pegar en ambos visores.
Validar DNS/TLS y una instalación dnf real en RAM. Antes de compilar, ejecutar
`python3 test_sources.py`. La prueba de cancelación comprueba SELinux activo e
inactivo, sin etiquetar archivos del equipo de prueba. Los tests de fuentes del ZIP
no sustituyen estas pruebas del sistema arrancado.

## Publicación posterior en Excalibur

Copiar ISO y SHA256 al cache conservando 0.1.0. Desde AUX/PXE, fases independientes:

```bash
sudo bash deploy.sh ram \
  --cache /var/www/aux.1-s.es/isos \
  --output /var/www/aux.1-s.es/html \
  --ram-dir /dev/shm/aux-pxe \
  --only tec-fedora44-assist-5.0.1-dev.5 --verbose

sudo bash generate.sh \
  --cache /var/www/aux.1-s.es/isos \
  --output /var/www/aux.1-s.es/html \
  --base-url https://aux.1-s.es \
  --pxe-url http://pxe.1-s.es --verbose
```

Usar generate actualizado: reconoce aux.assist con rd.live.image y publica bajo
Tools. Usa root=live:HTTP/.../LiveOS/squashfs.img y overlayfs, sin inst.stage2 ni
inst.rescue. Kernel/initrd se leen de la configuración real del medio. Comprobar
rutas HTTP y arrancar por iPXE sin ISO local antes de anunciar la entrada funcional.
Publicar la ISO completa en Bastion después.

## Referencias

- https://weldr.io/lorax/livemedia-creator.html
- https://pykickstart.readthedocs.io/en/latest/kickstart-docs.html
- https://packages.fedoraproject.org/pkgs/wget2/wget2-wget/
- https://packages.fedoraproject.org/pkgs/ddrescue/ddrescue/
- https://packages.fedoraproject.org/pkgs/ntfs-3g/ntfsprogs/
- https://man.openbsd.org/tmux.1
