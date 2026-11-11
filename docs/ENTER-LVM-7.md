# AUX Enter / LVM

Timestamp: 2026-11-11 | Version: 7.0.0-beta.15
Author & Credits: https://www.alawise.es/1-s

`sudo aux-enter -i` incluye los PV LVM2_member además de los sistemas de archivos
y contenedores LUKS. Al elegir un PV, muestra el grupo y permite seleccionar un LV
por nombre, tamaño, estado y tipo de segmentos. Un LV ya activo también puede
seleccionarse directamente en la lista de sistemas de archivos.

Para inspeccionar el grupo sin activar volúmenes:

```bash
sudo aux-enter --device /dev/PV_ELEGIDO --list
```

Para revisar el plan de entrada a un LV:

```bash
sudo aux-enter --device /dev/PV_ELEGIDO --lv GRUPO/VOLUMEN
```

Los nombres del ejemplo se sustituyen por los del informe. `--apply` ejecuta el
plan. La inspección monta el sistema de archivos en solo lectura y sin replay de
journal cuando el formato lo admite. No constituye una adquisición forense.
`--repair` permite escritura y chroot después de confirmar el destino; no ejecuta
fsck, cambios de contraseña ni reparaciones automáticas.

La activación automática se limita a LV lineales o striped. Se selecciona por
UUID, se restringen los dispositivos a los PV del grupo elegido y se exige que
no falten PVs. En inspección, read_only_volume_list solicita un mapeo de solo
lectura sin cambiar el permiso persistente del LV. Device-mapper debe confirmar
el UUID esperado y blockdev debe confirmar el modo solicitado.

Al salir, se desactiva únicamente el LV que AUX encontró inactivo y activó para
esa operación. Un LV que ya estaba activo conserva su activación. Un volumen
ocupado no se fuerza a cerrar y no se desactiva un grupo completo.
El namespace aísla los montajes; la activación LVM sigue siendo estado compartido
del kernel del entorno de rescate.

Thin pools, snapshots, caché y RAID requieren activación y revisión manual con
las herramientas LVM. Una vez activo el LV que contiene el sistema de archivos,
se puede seleccionar ese dispositivo directamente. No se activa automáticamente
un LV complejo, un grupo incompleto, ni un mapeo con identidad incompatible.

El flujo admite un PV detrás de un contenedor LUKS abierto con `--unlock` y
contraseña local. Para Btrfs se conserva la selección explícita de subvolumen.
No se guardan contraseñas ni se crean grupos o volúmenes.

La VM de prueba iniciada solo con `-cdrom` no contiene discos LVM. La validación
funcional necesita una imagen de disco adicional preparada para la prueba.
Las pruebas de esta entrega simulan los informes y el estado de los dispositivos;
no sustituyen una prueba real de activación, montaje y cierre en la Live.
