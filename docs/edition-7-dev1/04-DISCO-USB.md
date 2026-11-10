# Del instalador al disco completo y la llave

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Primera construcción dentro de una VM

La ruta manual recomendada instala el sistema en un **disco virtual nuevo** y
después permite copiar sus bytes a una llave. El host no se instala ni se
particiona durante la creación de la ISO.

Preparar KVM/libvirt, `virt-install`, `virsh` y un visor de la consola. Consultar
las variantes de paquetes de la distribución constructora. La memoria de 8 GiB
y el disco de 40 GiB del ejemplo son valores iniciales de laboratorio; aumentar
el disco si la suite lo necesita y comprobar que la llave de destino sea al menos
igual de grande en bytes.

Ejemplo para Fedora, desde una conexión libvirt ya configurada:

```bash
virt-install --name aux7-fedora --memory 8192 --vcpus 4 \
  --disk path="$(pwd)/output/aux-fedora-7.0.0-dev.1.raw",size=40,format=raw \
  --cdrom "$(pwd)/output/pxe.iso" \
  --boot uefi --osinfo detect=on,require=off --graphics spice
```

Para Debian usar otro nombre de VM, otro disco nuevo y `output/aux.iso`. No
conectar discos físicos al invitado para la primera instalación. Si faltan
permisos sobre la ruta, elegir una ruta de almacenamiento de libvirt autorizada;
no ampliar indiscriminadamente los permisos de directorios personales.

Este ejemplo genera una instalación UEFI. La instalación BIOS se construye y
prueba arrancando otra VM en BIOS. Un disco instalado en UEFI no queda probado
para BIOS por copiarlo a una USB. Para un medio universal hay que añadir ambos
cargadores y sus particiones/estructuras, y validar ambos firmwares.

En el instalador seleccionar el disco virtual, revisar el particionado y crear
una cuenta administrativa propia. Confirmar dentro del invitado que se ha
instalado en ese disco y reiniciar sin el medio instalador.

## Preparar una instalación portable

- Mantener kernel, módulos y firmware instalados como paquetes normales.
- Usar UUID en el montaje de la raíz y demás particiones del sistema instalado.
- Regenerar initramfs con el perfil genérico de la guía de cada distribución.
- Instalar el cargador en la EFI de la propia llave/imagen.
- Comprobar el mecanismo de arranque UEFI para medios extraíbles. La presencia
  de una entrada NVRAM de la VM no garantiza arranque en otro equipo.
- No transportar las MAC o nombres de interfaz fijos del constructor en los
  perfiles de red. Conservar los perfiles creados después por el propietario.
- No incorporar claves privadas de técnicos, contraseñas de API ni datos reales
  de asistencia en una imagen distribuida.

La personalización final requiere comprobar identidad de máquina y regeneración
de claves SSH por cada copia. Hacerlo en una copia de publicación, nunca sobre
la única instalación personalizada con trabajo del usuario. No borrar perfiles
Wi-Fi de una llave ya en uso como si siguiera siendo el constructor.

## RAM y rendimiento

La raíz, los programas y el estado del gestor de paquetes permanecen en disco.
El kernel utiliza RAM como caché normalmente. Medir los accesos de lectura y
escritura antes de ajustar más cosas. `/run` es temporal; si se quiere ampliar
el uso de tmpfs a `/tmp`, hacerlo con un límite y medir la presión de memoria.
Los volcados de discos, informes grandes y `/storage` deben ir a almacenamiento
con capacidad suficiente. No usar la RAM como destino accidental de una imagen
forense completa.

## Apagar y conservar la imagen

Cerrar la sesión del invitado y apagarlo. Confirmar su estado con la misma
conexión libvirt utilizada para crearlo:

```bash
virsh domstate aux7-fedora
```

Debe indicar apagada antes de copiar o calcular la suma final. Si el disco se
creó en qcow2, convertir una copia apagada a raw:

```bash
qemu-img convert -p -O raw output/original.qcow2 output/aux-fedora-7.0.0-dev.1.raw
```

Si ya es raw, no necesita conversión. Registrar tamaño virtual y suma de la
imagen publicada. La compresión del archivo de descarga no convierte la raíz
instalada en un sistema Live.

## Copiar a una USB física

Este paso reemplaza el contenido completo del dispositivo elegido. Usar la
ruta estable `by-id` de **esa USB**, comprobar modelo, serie y tamaño, y desmontar
sus particiones antes de escribir. No utilizar un nombre `/dev/sdX` copiado de
una sesión anterior. Ejemplo de inspección:

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN,FSTYPE,MOUNTPOINTS
ls -l /dev/disk/by-id/usb-*
```

Después de identificar la llave y respaldar sus datos, sustituir los marcadores:

```bash
sudo blockdev --getsize64 /dev/disk/by-id/usb-ID_REAL_DE_LA_LLAVE
stat -c '%s' output/aux-fedora-7.0.0-dev.1.raw
sudo dd if=output/aux-fedora-7.0.0-dev.1.raw \
  of=/dev/disk/by-id/usb-ID_REAL_DE_LA_LLAVE \
  bs=16M status=progress conv=fsync
```

El primer tamaño debe ser igual o mayor al segundo. Escribir en el dispositivo
completo, no en una partición. La copia en bruto replica UUID y particiones:
no utilizar varias copias conectadas simultáneamente sin resolver identidades
duplicadas. Ampliar la partición y el sistema de archivos para ocupar espacio
extra se hace como una operación separada según el formato elegido.

El particionado estándar del instalador puede adaptarse a USB, SSD externo o
disco interno. No se ha fijado todavía un diseño único para todos los tamaños
de llave ni un constructor automático del medio multiboot.

