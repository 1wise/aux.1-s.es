# Construir pxe.iso e instalar Fedora

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Resultado y máquina de construcción

El objetivo inmediato es una ISO **del instalador Anaconda** con un Kickstart
incorporado. Al ejecutarlo, instala Fedora de forma normal en el disco elegido.
Se puede realizar la instalación dentro de una VM para obtener una imagen de
disco transferible a USB. No usar el antiguo comando `livemedia-creator --make-iso`
para este objetivo: ese modo construye una ISO Live.

En Bebe/Fedora x86_64, preparar herramientas:

```bash
sudo dnf install lorax pykickstart xorriso isomd5sum
mkdir -p input work output
mkksiso --help
ksvalidator --listversions
```

Para construir una instalación en un disco virtual, preparar también las
herramientas KVM/libvirt y un visor de la consola de la VM. Hacerlo dentro de
una VM desechable permite separar el disco de instalación de los discos reales.

## Elegir y verificar el medio oficial

Descargar un `boot.iso`/netinst de la rama de Fedora elegida, su CHECKSUM y la
clave de firma oficial correspondiente. Obtenerlos desde las páginas oficiales
de Fedora, no desde una URL propuesta por la IA sin comprobar. La ruta de
desarrollo puede cambiar de composición diariamente.

Verificar primero la firma del CHECKSUM y después la suma de la ISO. Registrar
URL final, fecha, arquitectura, identificador de composición y huella de la clave.
Mantener juntos el medio verificado y la evidencia de verificación.

Si se usa Rawhide, el Kickstart incluido propone su árbol Everything. No mezclar
un instalador antiguo con repositorios de desarrollo arbitrarios: el instalador,
el árbol de instalación y la sintaxis Kickstart deben corresponder a la misma
rama. Si se elige Branched, modificar la fuente y anotar su versión exacta.

## Revisar la selección

`profiles/fedora/installed.ks` contiene el perfil editable. La instalación de
almacenamiento y las credenciales se dejan sin automatizar. No incluye
`clearpart`, `zerombr` ni contraseñas universales.

`profiles/fedora/packages.txt` es la lista completa propuesta de paquetes
individuales. El grupo `xfce-desktop` y `base-x` debe existir en los metadatos
comps del repositorio elegido; comprobar los grupos con las herramientas DNF
de esa rama. Los nombres de paquetes también deben comprobarse contra ese
repositorio antes de construir. Una máquina Fedora estable no sirve como
prueba de disponibilidad en Rawhide.

Desde un entorno de construcción que ya use la rama elegida, una comprobación
manual sin instalar es:

```bash
dnf group list
dnf repoquery --available kernel linux-firmware tmux cockpit
```

Revisar también el resto de la lista. El selector futuro deberá verificar todos
los nombres y generar el bloque `%packages`; en esta entrega hay que mantener
sincronizados manualmente la lista y el Kickstart. No utilizar `--ignoremissing`
para ocultar ausencias de herramientas requeridas.

Validar el perfil usando la versión que corresponde al instalador:

```bash
ksvalidator profiles/fedora/installed.ks
```

Si el parser del host tiene otra versión, usar el de una VM de la rama elegida
o seleccionar el handler correcto mediante `-v`, después de consultar
`ksvalidator --listversions`.

## Generar la ISO de instalación

Renombrar una copia del medio verificado como `input/fedora-netinst.iso` y ejecutar
desde la raíz de esta edición:

```bash
sudo mkksiso --ks profiles/fedora/installed.ks \
  input/fedora-netinst.iso output/pxe.iso
sha256sum output/pxe.iso > output/pxe.iso.sha256
xorriso -indev output/pxe.iso -report_el_torito plain
```

`mkksiso` adapta las entradas del medio oficial para cargar el Kickstart.
La conservación de UEFI depende del medio original y de la versión de Lorax;
no usar `--skip-mkefiboot` para declarar soporte UEFI de una USB sin comprobarlo.
El paso anterior no instala Fedora ni escribe una llave física.

Esta receta usa repositorios de red: **no es una ISO de instalación offline**.
La llave, una vez instalada con los paquetes, podrá usar sus herramientas sin
red. Para una edición instaladora offline hay que incluir los RPM requeridos y
sus dependencias en un repositorio con `repodata`, incorporarlo mediante
`mkksiso --add` y cambiar la fuente Kickstart para utilizar ese repositorio.
La guía oficial de mkksiso explica esa variante; no basta añadir archivos RPM
sueltos o elegir `cdrom` sobre un netinst sin contenido.

## Instalar y preparar portabilidad

Arrancar `pxe.iso` en la VM del disco de trabajo descrita en la guía 04. Elegir
el disco virtual, crear usuario y revisar el particionado. Mantener una partición
EFI propia cuando se construya para UEFI. Instalar todos los cargadores en el
disco de destino, no en el disco del host.

Una vez iniciado el sistema instalado, consultar la versión y regenerar el
initramfs para portabilidad:

```bash
uname -r
rpm -q kernel kernel-modules kernel-modules-extra linux-firmware
sudo install -m 0644 config/fedora/90-aux-generic.conf /etc/dracut.conf.d/90-aux-generic.conf
sudo dracut --regenerate-all --force --no-hostonly
```

Copiar primero la edición al sistema instalado para disponer de `config/`.
Comprobar que todos los kernels instalados tengan módulos en `/usr/lib/modules`
y su initramfs. No seleccionar una versión con `uname -r` desde fuera del
sistema: en un chroot, ese comando sigue mostrando el kernel del anfitrión.

Registrar los paquetes exactos:

```bash
rpm -qa --qf '%{NAME} %{VERSION}-%{RELEASE} %{ARCH}\n' | sort > installed-packages-fedora.txt
```

Después seguir las guías 04 y 05. Esta entrega no ha compilado ni arrancado la
ISO generada; BIOS, UEFI, red y hardware deben comprobarse con la composición real.

