# Construir aux.iso e instalar Debian Testing

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Resultado

Se personaliza un **instalador oficial Debian Testing** con el perfil de paquetes
y una preconfiguración. El sistema resultante se instala normalmente en el disco.
La receta no utiliza live-build, `boot=live` ni persistencia mediante overlay.

Realizar esta construcción en una VM Debian Testing amd64. En Bebe puede
prepararse esa VM con las herramientas de virtualización. Tener separada la
construcción Debian evita mezclar RPM y DEB en el mismo sistema raíz.

## Herramientas y medio de entrada

```bash
sudo apt update
sudo apt install xorriso debconf-utils
mkdir -p input work output
```

Obtener desde Debian el netinst de Testing/daily apropiado para amd64 y su
manifiesto firmado de sumas. Verificar la firma, la huella oficial y la suma del
archivo antes de renombrar una copia como `input/debian-testing-netinst.iso`.
Registrar la fecha de construcción. No mezclar el kernel del instalador de
una composición con los udebs de otra: en Testing puede aparecer ese desfase.

## Selección e interacción

El archivo `profiles/debian/preseed.cfg` configura red automática y paquetes,
pero conserva las preguntas sobre cuentas, disco, particiones y cargador.
No contiene confirmaciones automáticas de borrado ni un disco seleccionado.
`profiles/debian/packages.txt` es la misma selección individual utilizada en
`pkgsel/include`. Revisar ambos si se edita la suite.

En la VM Testing, comprobar los candidatos de los paquetes, por ejemplo:

```bash
apt-cache policy linux-image-amd64 task-xfce-desktop cockpit gddrescue testdisk
```

La validación se debe extender a todos los nombres de la lista. El perfil añade
un conjunto amplio inicial de firmware y habilita `non-free-firmware` y
`non-free`. Revisar esa elección de componentes y licencias. Los microcódigos
y cabeceras de `packages-optional.txt` requieren selección según arquitectura.
No añadir repositorios de Kali
al sistema Debian para resolver un nombre de paquete.

Comprobar la sintaxis de la preconfiguración:

```bash
debconf-set-selections --checkonly profiles/debian/preseed.cfg
```

Ese comando comprueba formato debconf; no demuestra que todas las opciones
correspondan al instalador de la composición ni que los paquetes existan.

## Incluir el perfil en la ISO

Se ofrece un remaster sencillo que conserva las entradas originales del
instalador. El perfil se seleccionará manualmente al arrancar:

```bash
xorriso -indev input/debian-testing-netinst.iso \
  -outdev output/aux.iso \
  -map profiles/debian/preseed.cfg /aux/preseed.cfg \
  -boot_image any replay
sha256sum output/aux.iso > output/aux.iso.sha256
xorriso -indev output/aux.iso -report_el_torito plain
```

Usar una salida nueva; no modificar la única copia del medio oficial. Verificar
en la imagen generada que exista `/aux/preseed.cfg`. El parámetro `replay`
recupera la configuración de arranque detectada en la entrada; no sustituye las
pruebas reales BIOS/UEFI ni convierte una entrada sin soporte USB en híbrida.

Al arrancar, editar la entrada del instalador y añadir a su línea de kernel:

```text
auto=true priority=high file=/cdrom/aux/preseed.cfg
```

En GRUB se edita la línea del kernel antes de arrancar; en ISOLINUX se utiliza
el editor de parámetros de la entrada. Conservar los argumentos originales y
el separador `---` si existe; situar los argumentos del instalador antes de él.
Confirmar en la consola del instalador que se ha leído el perfil. En esta receta
la selección de disco y las confirmaciones de particionado siguen siendo manuales.

Al añadir archivos, el manifiesto interno de comprobación del medio oficial no
incluye necesariamente los archivos nuevos. No anunciar su firma como firma de
la ISO personalizada. La SHA-256 publicada junto a `aux.iso` debe corresponder
a los bytes de la salida final. Para producir un instalador de distribución
completo, con checksum interno y menú personalizado gestionados conjuntamente,
usar la variante simple-cdd descrita abajo.

## Instalar y preparar el disco completo

Instalar `aux.iso` en el disco virtual de la guía 04. Se necesita red para obtener
la suite de paquetes. El sistema instalado sí conserva sus herramientas para
trabajar offline. Crear usuario local y revisar cuidadosamente los destinos de
raíz, EFI y GRUB en el instalador.

Dentro de Debian instalado, copiar la edición y preparar un initramfs amplio:

```bash
sudo install -m 0644 config/debian/aux-generic /etc/initramfs-tools/conf.d/aux-generic
sudo update-initramfs -u -k all
sudo update-grub
dpkg-query -W -f='${Package} ${Version} ${Architecture}\n' | sort > installed-packages-debian.txt
```

Confirmar que `linux-image-amd64` sigue instalado para recibir los kernels de la
rama y que los módulos coinciden con cada kernel. El valor `MODULES=most` amplía
la selección del initramfs, pero no proporciona controladores inexistentes o
firmware que no se haya instalado.

## Variante para una ISO offline más completa

`simple-cdd` construye instaladores personalizados mediante perfiles de paquetes
y preseed. Es preferible a ampliar indefinidamente el remaster manual cuando se
quiera distribuir el conjunto offline. En una VM Debian de construcción:

```bash
sudo apt install simple-cdd debian-cd
build-simple-cdd --help
```

Crear un directorio de construcción independiente con `profiles/aux.packages`
y `profiles/aux.preseed` a partir de los archivos de esta edición. Elegir el
codename que corresponde a Testing en ese momento y revisar los perfiles
incluidos por simple-cdd. Después, un punto de entrada documentado es:

```bash
build-simple-cdd --dist CODENAME_TESTING --profiles aux --auto-profiles aux --dvd
```

`CODENAME_TESTING` es un marcador que debe sustituirse. Revisar el mirror, los
componentes y la compatibilidad de debian-cd con esa rama. La salida de esta
variante también requiere comprobación de paquetes, arranque y funcionamiento
offline. No usar `--force-preseed` para esconder errores de configuración.

