# Despliegue de AUX 7

Timestamp: 2026-11-10 | Version: 7.0.0-dev.4  
Author & Credits: https://www.alawise.es/1-s

## Fuentes y Git

Extraer el ZIP en una carpeta nueva fuera de las raíces públicas de Nginx.
Comprobar `sha256sum -c SHA256SUMS`. El árbol ya contiene TEC, CLI, cliente y
generador; no requiere otros ZIP. El repositorio de referencia es
https://github.com/1wise/aux.1-s.es, rama `history`.

Esta entrega no se ha enviado a GitHub. Incorporar en una rama nueva y revisar
los cambios. No copiar cuentas, casos o almacenes privados dentro del árbol.
`SOURCE.json` distingue el archivo recuperado del commit observado en GitHub;
no afirma que ambos árboles sean idénticos.

## Selección nativa y web

El menú abre con preparación ISO. Instalar SOBRE EL SISTEMA ACTUAL queda al
final y muestra el equipo afectado. La línea de comandos exige --mode o
--selection: --apply por sí solo no elige el sistema actual.
aux-assist se selecciona junto al resto de herramientas; incluye dependencias,
lanzador, configuración y servicios con apertura manual. Desmarcarlo conserva
cualquier instalación anterior. La elección se propaga a los pasos de la ISO.


Construir la web con `python3 build.py --output dist --package-source`.
`dist/installer.html` incluye todas las tareas del catálogo tasksel de Debian
Testing y los entornos/grupos del catálogo comps de Fedora 45.
La selección exportada se consume con:

```bash
python3 aux-setup --selection aux-selection.json
sudo python3 aux-setup --selection aux-selection.json --apply
```

La elección queda ligada a la suma del catálogo para impedir que se apliquen
IDs bajo un catálogo diferente sin revisión. La web incorpora una instantánea;
APT o DNF resuelven los paquetes y las dependencias del repositorio configurado.
El selector de consola usa las mismas listas: `python3 aux-setup --interactive`.
Con `dialog` presenta casillas; sin él ofrece búsqueda y selección numérica.
Las tareas de idiomas y los grupos internos siguen disponibles en ambos casos.

Fedora permite elegir un entorno, los complementos opcionales y otros grupos.
Los grupos requeridos se incluyen automáticamente. Debian conserva tareas,
subtareas de escritorio y sus padres. Los perfiles AUX de discos, red,
administración, análisis y construcción se eligen aparte del escritorio nativo.
El perfil nativo descargado selecciona software; el modo ISO añade también las
fuentes y los pasos de instalación de las aplicaciones AUX.

Este árbol no contiene la identidad del Site anterior. El build genera la web
local; no sustituye una publicación remota ni envía código a GitHub.

## Sistema existente

El modo `existing` comprueba la distribución mediante `/etc/os-release` y usa
su gestor de paquetes. Un paquete no disponible detiene la operación.

```bash
python3 aux-setup --mode existing --distro debian --roles base,desktop,disks,forensics,network,admin,build
sudo python3 aux-setup --mode existing --distro debian --roles base,desktop,disks,forensics,network,admin,build --apply
```

En Fedora cambiar `--distro`. Este modo conserva la rama ya configurada; conserva los repositorios de la instalación existente. Las herramientas quedan bajo
`/usr/local/lib/aux` y `/usr/local/bin`. Los archivos existentes `ai.json`,
`cli.json` y `profiles.json` de `/etc/aux-assist` se conservan. `/work` y `/storage`
son directorios persistentes.

Abrir AUX Assist desde XFCE o con `sudo aux-assist`. Necesita VT6 libre. No
ocupa VT7/8 ni espera una conexión para ofrecer herramientas locales. La revisión
de propuestas API permanece en VT6, opción E. Las claves se solicitan localmente.

## Base nueva

Debian necesita debootstrap y el espejo oficial. Fedora necesita un constructor
Fedora 45 con DNF y sus repositorios oficiales fedora/updates configurados. Arquitectura
inicial: amd64/x86_64.

```bash
python3 aux-setup --mode root --distro debian --root /mnt/aux-root --roles base,desktop,disks,network,admin
sudo python3 aux-setup --mode root --distro debian --root /mnt/aux-root --roles base,desktop,disks,network,admin --apply
```

El destino debe ser una raíz vacía. La operación instala la base y AUX; para
obtener un disco arrancable aún hacen falta particiones, fstab, cuenta, initramfs
genérico y cargador. El recorrido con instalador ISO conserva la selección y
confirmación de discos del instalador.

## Composición e ISO

```bash
python3 aux-profile --distro debian --interactive --output /tmp/aux-profile
python3 aux-profile --distro fedora --roles base,desktop,disks,forensics,network,admin,build --check-packages --output /tmp/aux-profile-fedora
```

Comprobar paquetes en la distribución y rama elegidas. Si se omite la
comprobación, `selection.json` registra `not-run`. Los nombres pueden cambiar
en los repositorios de desarrollo.

El constructor ISO necesita xorriso y un medio oficial cuya suma y firma ya se
hayan comprobado. `--iso-sha256` compara bytes; no verifica la firma oficial.
La salida debe quedar fuera del directorio de fuentes.

```bash
python3 aux-setup --mode iso --distro debian --iso /srv/iso/debian-installer.iso --iso-sha256 SHA256_REAL_DEL_MEDIO --output /srv/build/aux.iso
```

Añadir `--apply --check-packages` para construir. Para Fedora cambiar
`--distro fedora` y usar como salida `/srv/build/pxe.iso`. El menú oficial se
conserva; en su entrada de instalación añadir:

| Instalador | Parámetro |
|---|---|
| Fedora | `inst.ks=cdrom:/aux/profile/installed.ks` |
| Debian | `preseed/file=/cdrom/aux/profile/preseed.cfg` |

Los perfiles generados para la ISO copian fuentes, verifican `SHA256SUMS` e
instalan las herramientas en el destino. Fedora busca el medio con un marcador
único; Debian utiliza `/cdrom`. Estos pasos están implementados y requieren
prueba real de instalación. El replay de xorriso tampoco declara BIOS/UEFI o
Secure Boot comprobados. No se incluye una ISO construida en esta entrega.

## Excalibur: portal y gateway

El instalador de servidor conservado tiene como objetivo Fedora, Nginx y
PHP-FPM; el soporte de clientes Debian no cambia esa disposición de servidor.

```bash
sudo dnf install python3 python3-pip python3-pyyaml nginx php-cli php-fpm openssl openssh-clients policycoreutils-python-utils postfix unzip qrencode
python3 aux-setup --mode server
```

Revisar dominios, certificados y rutas privadas de `fast-boot.json` y después:

```bash
sudo python3 aux-setup --mode server --apply --nginx
```

Los detalles de cuentas, correo, certificados y copias previas siguen en
`INSTALL-6.3.md` y `tec/MAIL.md`. Se conserva la información privada. El instalador
no es una transacción completa de todo el servidor. La salud del gateway muestra
la versión de su componente compatible. El QR de inscripción técnica se genera
localmente con qrencode; el cliente no necesita TOTP para pedir asistencia.

## Catálogo y actualización semanal

Las fuentes de ejemplo incluyen Debian, el índice oficial de versiones Fedora
y los metadatos e inventario completo de menús netboot.xyz. Por defecto sólo se
actualizan enlaces y versiones. La web ofrece el origen como primera descarga,
y funciona también desde Links con una tabla HTML de enlaces.
Ver CATALOG-7.md para la selección y los límites obligatorios de imágenes locales.


Adaptar `config/catalog.sources.example.json` y copiarlo a
`/etc/aux/catalog.json`. Los adaptadores usan índices HTML con patrones de
nombre completos o JSON con un objeto `entries`. Los hosts HTTPS y las
redirecciones se limitan a la lista declarada.

```bash
python3 aux-catalog --config /etc/aux/catalog.json --cache /tmp/aux-catalog-cache --output /tmp/aux-catalog-preview
```

La web está en `current/index.html`. Permite filtrar y exportar selección
light/heavy. `--select id1,id2` limita una publicación desde terminal.
`--download` exige SHA-256 fijado para cada archivo. La comprobación del hash y
la firma del origen se registran por separado; no se declara una firma verificada
por haber leído un manifiesto sin verificarla.

La publicación nueva se prepara completa antes de cambiar `current`; se
conservan las versiones anteriores. Si falla una fuente, descarga o hash, no se
retira la publicación previa. Los menús PXE requieren evidencia ligada a la
identidad de la receta, URL desplegadas y prueba de firmware. El formato está
en `config/boot-evidence.example.json`. Para publicar una receta, añadir a la
entrada `boot.kernel_url`, `boot.initrd_url` y `boot.kernel_args`, obtener su
`identity` y registrar los resultados reales en el archivo de evidencia.

```bash
sudo python3 aux-setup --mode catalog-service --apply
sudo systemctl start aux-catalog-update.service
```

La cuenta `aux-catalog` necesita lectura de `/etc/aux/catalog.json`. Exponer
únicamente `/srv/aux/catalog/current/` mediante el Nginx existente, comprobar la
primera publicación y después activar:

```bash
sudo systemctl enable --now aux-catalog-update.timer
systemctl list-timers aux-catalog-update.timer
```

La plantilla usa sábado a las 03:00, `Europe/Andorra`, siguiendo la zona de los
perfiles; se puede editar antes de activarla. Actualiza las fuentes elegidas.
No reconstruye ISO ni actualiza código Git automáticamente.

## Entrar en una instalación

```bash
python3 aux-enter --list
sudo python3 aux-enter --device /dev/mapper/RAIZ_ELEGIDA --apply
```

La inspección usa opciones de montaje específicas para ext2/3/4, XFS o Btrfs.
No se declara una adquisición forense. La shell comienza en el directorio
montado y utiliza las herramientas del entorno de rescate. Termina con `exit`.

`--unlock` abre temporalmente una raíz LUKS con contraseña local. Si contiene
LVM, activar y seleccionar su volumen lógico. `--subvolume @` elige un subvolumen
Btrfs. Para reparación añadir `--repair --apply`: el programa muestra el
dispositivo y pide la frase que lo identifica antes de montar con escritura.

La reparación prepara un namespace de montajes, comprueba arquitectura ELF y
abre chroot con un entorno mínimo. Al salir desmonta en orden inverso. Si un
montaje está ocupado se conserva el directorio y se comunica el fallo. Ensayar
este recorrido en VM con un disco sintético antes de declararlo aceptado.

## Referencias de las recetas

- https://dnf.readthedocs.io/en/latest/command_ref.html
- https://manpages.debian.org/unstable/xorriso/xorriso.1.en.html
- https://www.gnu.org/software/xorriso/
- https://www.debian.org/releases/testing/amd64/apbs02.en.html

El registro `CHECKS-7.md` identifica las comprobaciones ejecutadas y pendientes.
