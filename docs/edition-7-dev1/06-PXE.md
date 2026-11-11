# Arranque PXE, rutas reales y tec.img

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Diferenciar las raíces de arranque

La decisión de instalación estándar afecta al arranque por red. Hay tres
resultados distintos que cada entrada debe declarar:

| Tipo | Qué se obtiene al arrancar |
|---|---|
| Instalador | Anaconda o Debian Installer que instala en un disco elegido. |
| Sistema instalado | Kernel/initramfs más una raíz normal local o de red preparada. |
| Live de terceros | Su raíz comprimida y parámetros oficiales, cuando esté en el catálogo. |

Una ISO instaladora propia no presenta por sí sola toda la suite XFCE sin
instalar. Para el escritorio de rescate inmediato se utiliza la llave ya
instalada. Arrancar ese mismo sistema estándar por red requiere elegir y
preparar un almacenamiento raíz de red, por ejemplo NFS o iSCSI, con diseño
específico. No se ha implementado en esta edición. No reutilizar sin revisión
una raíz de escritura única para varios clientes simultáneos.

Los kernels e initramfs PXE se publican junto con su receta. No se recomienda
tratar cualquier ISO como si iPXE pudiera arrancarla universalmente mediante
`sanboot` o un simple `chain`.

## Fedora Installer

Dentro del árbol de instalación Fedora suelen aparecer `images/pxeboot/vmlinuz`
y `images/pxeboot/initrd.img`. Comprobar su existencia en el árbol realmente
descargado y registrar exactamente qué composición los produjo.

La receta indica `inst.repo` hacia un **árbol de instalación** con su metadata
y contenido, no hacia una carpeta que solo contiene una ISO. Revisar `.treeinfo`
y la ubicación de `stage2`. El runtime del instalador puede tener un SquashFS:
eso no convierte la raíz instalada del producto en una instalación Live.

Si se utiliza `inst.ks`, la URL debe servir un Kickstart revisado. El perfil
incluido mantiene la elección del disco manual. No publicar un Kickstart que
borre discos automáticamente dentro de un menú público genérico.

## Debian Installer

Para instalar por red utilizar el conjunto **netboot** de Debian Installer
de la misma composición: `linux` e `initrd.gz`, no asumir que el initrd que
busca un CD en la ISO netinst es intercambiable con el de netboot.

La ruta oficial se determina a partir de la versión y arquitectura; para amd64
se consulta el árbol `dists/<suite>/main/installer-amd64/.../images/netboot/`.
El sufijo puede contener `debian-installer/amd64/`. Extraerlo desde el índice
real, conservar una copia y verificar que coincida con los udebs de instalación.

El preseed se publica en una URL accesible desde el instalador. Pasar
`auto=true priority=high url=<URL_PRESEED>` sin eliminar las preguntas de disco
que deliberadamente se han dejado manuales.

## Rutas SquashFS del catálogo

Para cada Live de terceros, localizar físicamente el SquashFS dentro de la ISO
y registrar ruta interna, tamaño, hash y parámetros oficiales de arranque.
No copiar por analogía `/LiveOS/squashfs.img`, `/live/filesystem.squashfs` o
`/casper/filesystem.squashfs` a distribuciones que usan otra disposición.

La receta diferencia:

- URL original de descarga.
- Ruta interna dentro de la ISO/árbol.
- Ruta desplegada local en el servidor.
- URL pública final de Excalibur o Bastion.
- Parámetros que relacionan kernel/initrd/raíz con esa URL.

Comprobar cada URL final desde fuera del servidor. Revisar nombre exacto y
mayúsculas, redirecciones, tipo de contenido, permisos, enlaces simbólicos,
Nginx y SELinux. Un 200 que contiene HTML de error no es un kernel. Si HEAD no
está admitido, usar una lectura acotada; si el servidor ignora Range, no descargar
una ISO entera solo para consultar un byte.

La validación de HTTP y de hash se registra separada de la prueba de arranque
BIOS/UEFI. El catálogo conserva `not-tested` hasta comprobar realmente el arranque.

## Construir el cargador pequeño

`tec.img` es el cargador; AUX Assist se ejecuta al cargar el sistema Linux al
que conduce su menú. Un cargador iPXE solo no puede ejecutar el servicio Python,
Cockpit o la suite forense.

La fuente de iPXE permite construir un cargador USB BIOS y un ejecutable UEFI.
Comprobar las dependencias de compilación en la documentación oficial. Fijar
y registrar el commit utilizado. Dentro de `ipxe/src`, tras preparar un script
de arranque embebido con la URL real del menú:

```bash
make bin/ipxe.usb EMBED=/RUTA/ABSOLUTA/bootstrap.ipxe
make bin-x86_64-efi/ipxe.efi EMBED=/RUTA/ABSOLUTA/bootstrap.ipxe
```

El primer resultado es una variante USB BIOS; el segundo es un ejecutable EFI.
No se convierte el primero en medio BIOS+UEFI simplemente renombrándolo.
El `tec.img` universal requiere un montaje de disco con su arranque BIOS y una
EFI FAT con el ejecutable en la ruta de medios extraíbles, o el constructor
GRUB/iPXE heredado debidamente revisado. Secure Boot queda pendiente de una
cadena de firma válida y comprobada.

La referencia 6.4 conserva `usb/` dentro de `aux-pxe-6.4.0-dev.1.zip`; contiene
su constructor y documentación. Antes de reutilizarlo, confirmar el URL del
menú, los targets BIOS/UEFI y su independencia del kit de overlay Live antiguo.
No ejecutar los constructores de persistencia 6.4 sobre una llave en uso.

## Menú multiboot combinado

Un medio combinado deberá tener entradas separadas para el sistema instalado
Fedora, el sistema instalado Debian y el menú iPXE. Cada raíz instalada tendrá
identidad y configuración propias; las imágenes de adquisición podrán guardarse
en un volumen de datos explícito. No concatenar `tec.img`, `aux.iso` y `pxe.iso`
con `cat` ni escribirlos consecutivamente con dd esperando un multiboot válido.
El constructor universal y su aceptación se mantienen como trabajo pendiente.

