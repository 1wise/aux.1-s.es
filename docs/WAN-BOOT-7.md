# W.A.N Arsenal iPXE · Excalibur

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

Los medios generados incluyen la entrada GRUB `W.A.N Arsenal iPXE - Excalibur`.
El destino predeterminado es `http://pxe.1-s.es/menu.ipxe`. iPXE va dentro del
medio, obtiene red por DHCP y ejecuta su bootstrap incorporado. El menú remoto
se mantiene en Excalibur; actualizar sus recetas no exige reconstruir la llave.
La entrada se añade al final y conserva la opción y espera predeterminadas.

| Medio | Integración |
|---|---|
| AUX Live Fedora 45 | `iso-assist/build.py` ejecuta el finalizador automáticamente. |
| Instaladores Debian y Fedora personalizados | `aux-setup --mode iso` añade los ejecutables y la entrada al crear la ISO. |
| USB persistente | `usb/portable/build.py` incluye el acceso junto a los perfiles local y limpio. |
| Llave iPXE | `usb/build.sh` y la imagen híbrida incluida usan el mismo título y destino. |
| Recetas anteriores | `iso/finish.py` y `assist/finish.py` reutilizan el finalizador compartido. |

El generador soporta BIOS x86 y UEFI x86_64. La rama UEFI comprueba la
arquitectura antes de cargar el ejecutable. El binario EFI incluido no está
firmado; esta entrega no declara aceptación con Secure Boot.

## Contenido y comprobaciones

En las ISO, `/aux/wan` contiene `ipxe.lkrn`, `ipxe.efi`, `wan.json` y un
identificador del medio. Los SHA-256 se cotejan con `usb/build-info.json` y el
bootstrap de origen. Los dos binarios conservan el mismo script incorporado.
El finalizador no genera ni descarga binarios alternativos silenciosamente.

Los menús GRUB reales se actualizan; los stubs que delegan con `configfile` se
conservan. En Debian se añade además la entrada BIOS a ISOLINUX. Si la partición
EFI lleva otra copia de `grub.cfg`, se sustituye por un enlace al menú actualizado
del mismo medio. Se contempla la partición EFI añadida fuera del árbol ISO.
`mcopy` y `mdir`, del paquete `mtools`, permiten hacerlo sin montar dispositivos.

La ISO se escribe en una ruta temporal y se releen los menús, binarios y la
partición EFI modificada antes de publicarla. Las fuentes e ISO de entrada se
conservan. Un medio sin menú GRUB reconocible detiene la generación.

## Uso con una ISO ya compilada

El constructor Live aplica el paso automáticamente. Para finalizar manualmente
una ISO Live anterior, con una ruta de salida nueva:

```bash
python3 iso-assist/finish.py --input /ruta/aux-live-raw.iso --output /ruta/aux-live-wan.iso
```

En una construcción nueva, el constructor pasa además `--source-manifest` para
comprobar `tmux.conf` y declarar las capacidades reales de esa preparación.
Una ISO que ya está grabada conserva su menú hasta regenerar y grabar el medio.

Los forks pueden reconstruir `usb/build.sh --menu-url URL --output-dir usb` con
su propio destino. Un cargador alternativo requiere su `build-info.json`,
`bootstrap.ipxe` y las sumas correspondientes. El USB persistente usa el cargador
incluido cuando no se indican `--ipxe-image` y `--ipxe-sha256`.

## Alcance de las pruebas

Trece regresiones comprueban menús y defaults, idempotencia, contenedores y
ejecutables, ISO Debian/ISOLINUX, configuración EFI añadida, lectura posterior,
rechazos y conservación del origen. La prueba completa ejecuta xorriso, mtools,
implantisomd5 y checkisomd5 sobre un medio de ensayo arrancable.

Ese medio se ha arrancado en QEMU/TCG con SeaBIOS y OVMF: ambas rutas llegan a
iPXE y muestran el destino correcto. Se ejecutó sin tarjeta de red; no certifica
la descarga del menú remoto, el arranque de una Live beta.17 completa, Secure Boot
ni una llave física. Esas comprobaciones siguen siendo independientes.

Referencias técnicas: https://ipxe.org/embed y https://ipxe.org/howto/chainloading.
