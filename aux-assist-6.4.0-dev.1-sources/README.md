# AUX Assist · 6.4.0-dev.1

Timestamp: 2026-10-17 | Version: 6.4.0-dev.1
Author & Credits: https://www.alawise.es/1-s

La terminal humana se abre desde CLI en una pestaña nueva con Terminal 1 y Terminal 2.
Cada una incorpora Paste y ^C / Ctrl+C. Esta versión requiere recompilar la ISO
para anunciar ambos canales al gateway. F7 observa la primera terminal.

Fuentes completas de la nueva ISO Fedora 44 x86_64; no es una ISO compilada.
Incluye las correcciones de TTY, puerto 4242 y aux-exec. RELEASE-6.4.md y
AGENT-6.3.md son las guías vigentes. G/M abren las API sin root en F4/F5;
F6/E permite revisar planes físicamente. aux-exec.service recibe propuestas
por /run/aux-exec/control.sock; solo la revisión física las aplica.

La clave API se introduce con V visible (por defecto) u O oculta. El modo visible
deja la clave en la terminal y su desplazamiento. La clave no se guarda en archivos
ni se añade a mensajes del chat. No se incluyen credenciales ni modelos universales.
Las API se consultan directamente por HTTPS; el CLI de Excalibur transporta SSH humano.

## Utilidades

La revisión 6.4 incorpora la corrección de red para el arranque local por USB: `payload/network_setup.py` limpia únicamente el estado
del constructor y entrega DNS a NetworkManager durante `%post`. El menú espera
como máximo 15 segundos a una conexión; N/nmtui sigue disponible sin red. Ejecutar
también `python3 test_network.py` antes de compilar. La receta se debe compilar antes de actualizar la ISO de la llave.

`packages.txt` contiene 95 paquetes solicitados, editables uno por línea. RPM
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

SSH abre el puerto 4242 solo tras AUTORIZO, con la clave pública elegida y terminal
forzada. El listener no permite SFTP ni túneles; sí existen clientes de
transferencia saliente en la shell del técnico. La opción P carga perfiles públicos
de https://tec.1-s.es/profiles.php; TEC debe estar desplegado con perfiles aprobados.
También se admite pegar una clave pública o su URL HTTPS.

La opción W usa una terminal xterm.js en TEC por HTTPS/WSS (puerto 443). Para probar
el agente GPT desde esa terminal, ya autorizada localmente la asistencia web, ejecutar
`systemctl start aux-exec.service` y después
`runuser -u aux-ai -- /usr/bin/python3 /usr/share/aux-assist/ai.py --provider openai --agent`.
xterm.js permite usar «Pegar desde el portapapeles» cuando la terminal está autorizada;
elegir V u O y pegar la clave solo en la petición de clave API.
El texto cruza el servidor CLI/TEC que mantiene la sesión, aunque la pasarela no graba
las entradas de terminal en sus logs.
El puerto 4242 sirve para SSH directo; el canal web usa WSS saliente por HTTPS.

Se requiere ruta directa o VPN ya configurada. La ISO no crea peers VPN ni abre SSH automáticamente. W realiza la solicitud
a la pasarela; el técnico acepta y el cliente escribe AUTORIZO antes de abrir SSH.

## Compilar en Fedora 44 x86_64

Lorax se ejecuta en modo virtual, instalando en un disco virtual de construcción.
No usar esta receta como Kickstart de un equipo real: contiene clearpart para ese
disco virtual. No usar --no-virt en Excalibur. Dependencias del constructor:

```bash
sudo dnf install lorax lorax-lmc-virt pykickstart openssl xorriso squashfs-tools isomd5sum
```

Utilizar Fedora Server netinst 44 x86_64 oficial, verificado con su CHECKSUM
firmado. Sirve de instalador de construcción; su runtime no entra en el Live.
Desde el ZIP descomprimido, preparación independiente:

```bash
python3 test_exec.py
python3 test_ai.py
python3 test_sources.py
python3 prepare.py --output work-6.4.0-dev.1 --config fast-boot.json.example
ksvalidator -v F44 work-6.4.0-dev.1/assist.ks
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
  --ks="$PWD/work-6.4.0-dev.1/assist.ks" \
  --releasever=44 \
  --project="AUX Assist 6.3" \
  --volid=AUX_ASSIST_62 \
  --rootfs-type=squashfs \
  --dracut-conf="$PWD/dracut.conf" \
  --extra-boot-args="aux.assist aux.ai.available=1 rd.live.overlay.overlayfs=1 rd.luks=0 rd.lvm=0 rd.md=0" \
  --ram=4096 --vcpus=2 \
  --iso-only \
  --iso-name=aux-assist-6.4.0-dev.1-raw-x86_64.iso \
  --resultdir="$PWD/results-6.4.0-dev.1" \
  --logfile="$PWD/compile-6.4.0-dev.1.log"
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

## Terminar la ISO y aceptación

Usar una salida NUEVA: finish.py conserva el arranque híbrido mediante xorriso
replay y genera el SHA-256. No grabar la imagen raw sin terminar.

```bash
python3 finish.py \
  --input results-6.4.0-dev.1/aux-assist-6.4.0-dev.1-raw-x86_64.iso \
  --output aux-assist-6.4.0-dev.1-x86_64.iso
```

Tras arrancar dentro del Live, comprobar:

```bash
systemctl cat aux-exec.service aux-gpt.service aux-gemini.service
getenforce
ss -lnt
free -h
df -h / /work
cat /usr/share/aux-assist/packages-requested.txt
```

aux-exec se inicia al abrir G/M/E; puede estar inactivo antes de usarlos.
Probar BIOS/UEFI, F4/F5 y retorno a F6, Wi-Fi, ausencia de listener hasta AUTORIZO,
cierre y visores sin entrada. E debe revisar/simular/aplicar/deshacer solo planes
acotados; ver AGENT-6.3.md. Las pruebas fuente no sustituyen el Live con SELinux.

W permite seleccionar excalibur y escribir SOLICITO. TEC recibe el código AUX-…;
el técnico completa TOTP y acepta. El cliente verifica identidad/huella y escribe
AUTORIZO. Solo entonces escucha 127.0.0.1:4242, transportado por WSS 443.
Ctrl-C en F6 cancela. Una ISO antigua no cambia al actualizar la web.

## Publicación posterior en Excalibur

Copiar ISO y SHA al caché conservando versiones probadas. Desde AUX/PXE:

```bash
sudo bash deploy.sh ram --only aux-assist-6.4.0-dev.1 --verbose
sudo bash generate.sh --verbose
```

Comprobar rutas HTTP y arranque iPXE antes de anunciar la entrada funcional.
Publicar copias físicas completas en Bastion con ovh/assemble.py. El creador USB
mantiene sus restricciones GPT; no forzar una tabla híbrida rechazada.

## USB persistente y reanudación 6.3

La ISO genérica conserva su ejecución en RAM. El kit portable crea el perfil USB
con sistema, paquetes, /work y /storage persistentes, actualización de kernel y
precarga opcional de claves GPT/Gemini. Las herramientas están en portable/ del
ZIP de fuentes, o usb/portable/ en el repositorio completo.

El perfil persistente puede restaurar un caso web o C de ocho horas autorizado
inicialmente, con el mismo equipo y técnico. La clave de host del caso se conserva.
El permiso caducado o revocado no se restaura. Se abre una shell nueva después de
reiniciar; los procesos anteriores terminaron. El modo limpio no lee ese permiso.
G/M permiten L para la clave API preparada y K gestiona los archivos guardados.
La ISO pública no incluye claves personales. Véanse portable/RESUME.md y API-KEYS.md.
