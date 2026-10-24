# USB AUX 6.2 — espacio libre y límites de actualización

Timestamp: 2026-10-17 | Version: 6.2.0-dev.1
Author & Credits: https://www.alawise.es/1-s

`create-usb.sh` valida la ISO y, únicamente con `--apply` y confirmación explícita,
BORRA el USB, verifica lo grabado y añade ext4 `AUX-DATA` con el espacio restante.
No ha sido probado en un USB físico en esta entrega. Hacer copia del USB antes
de usarlo. El script rechaza discos internos, particiones, dispositivos montados,
swap/LVM/RAID y tamaños de sector distintos de 512 bytes. Solo admite ISO con GPT
nativa y MBR protector; MBR/híbrido desconocido se rechaza ANTES de escribir.
No convertir una ISO rechazada manualmente con fdisk para forzar la operación.

Dependencias en Fedora: `python3`, `util-linux`, `gdisk`, `parted`, `e2fsprogs`,
`systemd-udev`. La verificación SHA-256 debe proceder de una publicación confiable;
calcular el hash propio no autentica una descarga alterada.

Sin `--apply` solo se muestra el plan (sustituir dispositivo y digest tras `lsblk`):

```text
bash usb/create-usb.sh --iso ARCHIVO.iso --sha256 DIGEST_VERIFICADO --device DISPOSITIVO_USB
```

Repetir con sudo y `--apply` SOLO después de comprobar modelo, número de serie,
capacidad y particiones. Escribir la frase exacta que incluye dispositivo y tamaño.
Se pierde TODO el contenido previo, no existe deshacer del formateo. No se
desmonta ningún disco automáticamente ni se elige un dispositivo por su letra.

Desde T en la ISO, identificar explícitamente la partición AUX-DATA con `lsblk -f`
y ejecutar `python3 /usr/share/aux-assist/storage.py --partition RUTA_PARTICION_USB`.
Montaje privado en `/storage`, con `nosuid,nodev,noexec`. `/work` continúa siendo
RAM: no se monta almacenamiento automáticamente por coincidir una etiqueta.
No guardar claves ni historial de asistencia sin valorar privacidad y cifrado.

Guardar ISO nuevas bajo `/storage/isos` permite conservarlas, **pero no actualiza
el kernel arrancado ni GRUB de la ISO grabada**. `dnf update` en el Live no hace
persistente el kernel de arranque. Tampoco basta con añadir una partición ext4
o copiar `/etc`/`var`/`usr/local` a ella. La persistencia de todo el sistema y su
kernel necesita instalación USB real o un mecanismo validado de imágenes A/B.

Pendiente antes de publicación estable: elegir e implementar ese modo actualizable,
conservar la imagen anterior, comprobar arranque con kernel nuevo y anterior,
recuperación tras descarga/escritura interrumpida, Secure Boot si se anuncia,
BIOS/UEFI y copia/restauración de los datos. No se distribuye un `update-usb.sh`
que finja resolver esas garantías. Este USB dev.1 solo conserva datos.

Fundamento: https://fedoraproject.org/wiki/LiveOS_image (kernel updates for images
with a persistent overlay). La ISO Rescue fija y `usb/build.sh` iPXE no cambian.
