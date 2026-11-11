# AUX Assist · 7.0.0-beta.15

Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
Author & Credits: https://www.alawise.es/1-s

La terminal humana se abre desde CLI en una pestaña nueva con Terminal 1 y Terminal 2.
Cada una incorpora Paste y ^C / Ctrl+C. Esta versión requiere recompilar la ISO
para anunciar ambos canales al gateway. F7 observa la primera terminal.

Fuentes de la nueva ISO Fedora 45 x86_64; no es una ISO compilada.
Usar la entrega completa de AUX Suite, con su SHA256SUMS. La preparación incorpora
las siete aplicaciones AUX desde archivos declarados y verificados; excluye el
estado local y no incorpora credenciales de servidor. El menú B/L/S/O permite abrir
instalación, catálogo, sistemas y Cockpit. Las aplicaciones conservan sus requisitos
externos: por ejemplo, debootstrap debe instalarse para construir una base Debian.
Incluye las correcciones de TTY, puerto 4242 y aux-exec. RELEASE-6.4.md y
AGENT-6.3.md son las guías vigentes. G/M abren las API sin root en F4/F5;
F6/E permite revisar planes físicamente. aux-exec.service recibe propuestas
por /run/aux-exec/control.sock; solo la revisión física las aplica.

La clave API se introduce con V visible (por defecto) u O oculta. El modo visible
deja la clave en la terminal y su desplazamiento. La clave no se guarda en archivos
ni se añade a mensajes del chat. No se incluyen credenciales ni modelos universales.
Las API se consultan directamente por HTTPS; el CLI de Excalibur transporta SSH humano.

## tmux y volúmenes LVM

tmux.conf se instala junto al cliente en /usr/share/aux-assist. AUX Enter incluye
el recorrido PV, grupo y LV, con activación temporal para volúmenes lineales o
striped y modo de inspección de solo lectura. Los LV complejos requieren activación
manual. Véase docs/ENTER-LVM-7.md en la entrega completa. La prueba LVM en la VM
necesita una imagen de disco adicional; arrancar solo la ISO no aporta discos LVM.

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

Con --excludedocs, el RPM links de Fedora 45 no registra su alternativa links:
su script de instalación condiciona ese registro a la existencia del manual.
La receta conserva el ahorro de documentación y usa update-alternatives para
registrar /usr/bin/links2 como links, sin manual asociado, únicamente si falta
un comando links ejecutable. Después se mantiene la comprobación de utilidades.

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

## Compilar en Fedora 45 x86_64

El constructor funciona dentro de una VM KVM. El Kickstart contiene clearpart
para el disco virtual y nunca debe usarse como instalador del equipo físico.
No existe una alternativa automática de instalación sobre el anfitrión.

Dependencias del constructor:

```bash
sudo dnf install lorax lorax-lmc-virt pykickstart openssl xorriso squashfs-tools isomd5sum
```

Usar el netinst oficial Fedora Server 45 x86_64 y comprobar su CHECKSUM firmado,
según https://fedoraproject.org/server/download/ . El SHA-256 pasado al constructor
se compara con el archivo completo, pero no sustituye esa verificación de origen.
La ISO Workstation Live no es el instalador de construcción.

Desde la raíz de la entrega completa, revisar el plan:

```bash
python3 iso-assist/build.py --interactive
```

El diálogo cyan pide ISO, SHA-256 y un directorio NUEVO fuera de las fuentes.
Solo escribir COMPILAR inicia Lorax; requiere sudo para construir. Para trabajar
por argumentos, build.py --help muestra --iso, --sha256, --output y --apply.
Sin --apply se muestra únicamente el plan. No se abre una VM ni se crea la salida.

Valores iniciales: 8192 MiB RAM, hasta cuatro CPU, raíz virtual ext4 de 16384 MiB
con reqpart para las particiones de arranque. Se exige KVM, 50 GiB libres y que
la RAM de la VM no supere el 75 % de MemAvailable. El constructor comprueba
versión 45 y arquitectura x86_64 en .discinfo o .treeinfo antes de arrancar el
instalador. El netinst oficial usa .discinfo; su arquitectura y versión se
contrastan con la etiqueta ISO cuando está disponible. Los fallos de lectura
conservan el diagnóstico de xorriso.
Los recursos del constructor no son un mínimo medido para el cliente Live.

El proceso genera recipe/assist.ks y source-manifest.json, valida con
ksvalidator -v F45, ejecuta Lorax y termina el medio con finish.py. El archivo
final aux-assist-7.0.0-beta.15-x86_64.iso y su .iso.sha256 quedan en la salida.
El raw intermedio permanece en results/ y no es el medio para publicar.
compile.log contiene el registro de Lorax.

Para preparar solo el Kickstart, sin compilar:

```bash
python3 iso-assist/prepare.py --output ../aux-live-recipe
ksvalidator -v F45 ../aux-live-recipe/assist.ks
```

Wi-Fi está incluido. --config admite configuración central y exporta solo las
URL públicas y las opciones de modelos API. --profiles admite perfiles públicos
sin claves privadas. No se incluye una configuración personal en la ISO pública.
El contenido usa repositorios de actualización: no es reproducible bit a bit
sin fijar un snapshot y las versiones RPM. La receta necesita el paquete completo;
el antiguo ZIP de fuentes rescue 5.x corresponde a otro medio.

La construcción exige gcdx64.efi, shimx64.efi, mmx64.efi y unicode.pf2. Si faltan
bajo /boot/efi, boot_check.py obtiene las copias versionadas de los RPM. Lorax
crea EFI/BOOT e images/efiboot.img. No se omite la comprobación de estos archivos.

## Aceptación del medio

El constructor termina GRUB con xorriso replay, conserva la ISO raw y escribe
/aux-live.json en la ISO final. El manifiesto declara dos terminales y registra
boot_verified=false: ninguna prueba fuente equivale a probar una ISO.

Después de arrancar la nueva Live, comprobar:

```bash
systemctl cat aux-exec.service aux-gpt.service aux-gemini.service
getenforce
ss -lnt
free -h
df -h / /work
cat /usr/share/aux-assist/packages-requested.txt
command -v aux-setup aux-profile aux-catalog aux-enter aux-assist aux-tools aux-images
```

Probar BIOS/UEFI, red y Wi-Fi, F4/F5 y retorno a F6, visores sin entrada,
consentimiento, cierre y dos terminales independientes. Las pruebas de aux-exec
están descritas en AGENT-6.3.md; también requieren SELinux en la Live.

W permite seleccionar excalibur y escribir SOLICITO. TEC recibe el código AUX;
el técnico completa TOTP y acepta. La autorización local AUTORIZO abre el canal
SSH de loopback por 4242, transportado mediante WSS por CLI en el puerto 443.
Terminal 1 y Terminal 2 deben funcionar de forma independiente. Actualizar la web
no cambia el cliente contenido dentro de una ISO antigua.

## Publicación posterior en Excalibur

Copiar ISO final y .iso.sha256 al caché, conservando los medios probados. Revisar
las opciones locales antes de desplegar: el despliegue en disco evita sumar el
nuevo rootfs a los medios que ya ocupan la RAM.

```bash
sudo bash deploy.sh disk --mode mount --only aux-assist-7.0.0-beta.15-x86_64.iso --verbose
sudo bash generate.sh --verbose
```

El árbol publicado debe contener aux-live.json, kernel, initrd y LiveOS. El menú
mantiene las ISO antiguas para elección manual; solo usa por defecto medios con
la declaración de dos terminales. Una declaración no certifica arranque ni firma.
Comprobar HTTP y el arranque iPXE antes de anunciar aceptación. Bastion requiere
su copia física posterior; no cambia automáticamente al actualizar Excalibur.

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
