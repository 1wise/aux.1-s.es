# AUX / PXE / TEC 6.0.0-dev.3 · CLI
Timestamp: 2026-10-16 · Author & Credits: https://www.alawise.es/1-s

Primera implementación para pruebas. La condición de versión estable todavía NO se cumple.
No se ha cambiado Excalibur, Bastion, Kamala, DNS, certificados ni cuentas reales.

## Entrega

- `aux-pxe-6.0.0-dev.3.zip`: scripts independientes, configuración y documentación.
- `tec-platform-6.0.0-dev.3.zip`: plataforma PHP, panel de sesiones y terminal xterm.js.
- `aux-cli-6.0.0-dev.3.zip`: servicio de pasarela, requisitos, unidad y plantilla Nginx.
- `aux-assist-6.0.0-dev.3-sources.zip`: nueva receta Fedora 44 con Wi-Fi y cliente WSS.
- ISO existente conservada: `aux-rescue-5.0.1-dev.5-x86_64.iso`, 489816064 bytes,
  SHA-256 `89516a77e73c40b3b3dd5392e940a658da5732904c11dad2291127e6b15f2383`.
  El binario no se incluye en el ZIP de código ni se renombra como una ISO 6.0.

## Operación

`--user` y `--group` seleccionan propietario y grupo local; sin grupo se usa el principal
del usuario elegido. `--owner` produce un error de argumento, sin alias silencioso.
Cada fase es ejecutable y revisable por separado. Los fallos detallan recurso, etapa,
ruta, fuente y causa. Los logs quedan bajo `cache/logs`, directorio 0700 y archivos 0600.

El presupuesto light es 22 GiB con 10 % de margen, de modo que la selección efectiva
es de hasta 19.8 GiB antes de la reserva. Si una imagen lo excede, se publica en disco
con aviso explícito; el espacio tmpfs real también se comprueba. No se borra la caché.

TEC es opcional: `generate.tec` acepta auto/on/off y `generate.sh --tec auto|on|off` lo
sobrescribe. Auto inspecciona `tec.web_dir`; on exige index.php y lib.php; off oculta enlaces.
No instala PHP-FPM ni copia datos o aplicaciones privadas al árbol de ISO.
La página /work expone la fuente versionada y su SHA, accesible también en Links.

Perfiles URL: excalibur (aux/pxe/tec), bastion (b/p/t), contingency (mismos dominios
públicos cuando se reasignan los DNS). El perfil no ejecuta otra fase ni cambia DNS.
El hosting compartido utiliza una raíz para AUX/PXE y un .htaccess; no duplica imágenes.
Consultar `ovh/README.md` para preparar por separado el árbol persistente antes de FTP.

La publicación local y FTPS conserva reemplazos atómicos POR ARCHIVO, con validación
previa y copia de seguridad de archivos generados. El intercambio atómico de TODO el
árbol sigue pendiente; no se presenta como implementado. El caché bloqueado evita
dos fases locales mutando el mismo inventario simultáneamente.

## Asistencia

Consultar `cli/README.md`. El técnico accede desde TEC con contraseña y TOTP,
el cliente confirma localmente al técnico, y SSH va encapsulado en WSS saliente por 443.
La pasarela se distribuye deshabilitada. Kamala es un alternativo manual, no un balanceo
de sesiones vivas. La autoridad de usuarios/JSON debe ser única.

La receta `iso-assist` añade W (web), C (URL de clave HTTPS) y T (bash local), 95 paquetes
solicitados, /work tmpfs y las correcciones de dominio SELinux del daemon SSH. La ISO fija
5.0.1 conserva exactamente su interfaz original: C pide nombre/contacto y no tiene opción T.

Dev.3 prepara G (GPT Assist / tty4), M (Gemini Assist / tty5) e I (cerrar los dos).
Son terminales de consulta por API HTTPS, iniciadas a petición, sin ejecución automática
de comandos ni recogida de datos. T conserva la shell root para intervención manual.
Solo se añaden fuentes Python y dos unidades systemd; la lista sigue en 95 paquetes.
`ai` en fast-boot.json centraliza modelos y límites públicos; las claves se introducen
sin eco al abrir cada sesión y quedan en memoria del proceso. Ver `iso-assist/AI-ASSIST.md`.

El usuario ha compilado una receta 6.0 previa y confirmado en Cari el arranque hasta
el menú y el uso de T con tethering USB de Hammer por GSM. No se ha comunicado versión
exacta, hash ni firmware. No se da por probada la asistencia remota por esa conexión.
Gentoo y Memtest86+ x86_64 fallaron en esa prueba; se requiere el error exacto. El catálogo
Gentoo ofrece descarga/chroot; aún no dispone de receta completa para netboot directo.
Memtest requiere revisar qué binario nativo y qué firmware BIOS/UEFI se seleccionaron.

## Compilar la nueva ISO en Fedora 44

Instalar dependencias y usar un directorio nuevo de trabajo y resultados. Livemedia-creator
con QEMU utiliza un disco de construcción desechable; no usar --no-virt en el servidor real.

```bash
sudo dnf install lorax lorax-lmc-virt pykickstart openssl xorriso squashfs-tools isomd5sum
cd iso-assist
python3 test_sources.py
python3 test_ai.py
python3 prepare.py --output work-6.0.0-dev.3 --config ../fast-boot.json
ksvalidator -v F44 work-6.0.0-dev.3/assist.ks
sudo livemedia-creator --make-iso \
  --iso=../Fedora-Server-netinst-x86_64-44-1.7.iso \
  --ks="$PWD/work-6.0.0-dev.3/assist.ks" --releasever=44 \
  --project="AUX Assist" --volid=AUX_ASSIST_600 \
  --rootfs-type=squashfs --dracut-conf="$PWD/dracut.conf" \
  --extra-boot-args="aux.assist aux.ai.available=1 rd.live.overlay.overlayfs=1 rd.luks=0 rd.lvm=0 rd.md=0" \
  --ram=4096 --vcpus=2 --iso-only \
  --iso-name=aux-assist-6.0.0-dev.3-x86_64.iso \
  --resultdir="$PWD/results-6.0.0-dev.3" \
  --logfile="$PWD/compile-6.0.0-dev.3.log"
python3 finish.py --input results-6.0.0-dev.3/aux-assist-6.0.0-dev.3-x86_64.iso \
  --output aux-assist-6.0.0-dev.3-final-x86_64.iso
```

La entrada local conserva los parámetros Live de Fedora y no exige red en Dracut.
El generador PXE añade los parámetros de red que necesita el arranque HTTP.
El servicio de menú deja de esperar network-online.target. Esto reduce una espera posible,
pero la causa de la lentitud observada en la ISO fija sigue sin medirse.

El paso finish conserva el arranque híbrido y prepara GRUB de cinco segundos y acceso al firmware UEFI. La siguiente imagen
necesita nueva compilación y pruebas: los resultados de la ISO fija no se heredan por etiqueta.
El marcador `aux.ai.available=1` permite añadir selecciones manuales GPT/Gemini en GRUB
y, tras desplegar/generar, en el apartado 0.A de iPXE. Usan la misma imagen y no duplican
RAM ni disco. El autoarranque iPXE de 60 segundos conserva la asistencia normal.

## Condiciones aún pendientes

Prueba exterior de la nueva ISO; BIOS/UEFI y SELinux; cobertura TLS de ambos clis;
visibilidad de avisos y teclado en navegador real; continuidad B/P/T con Excalibur apagado;
recepción de solicitudes en Kamala; límites de cuota y PHP del hosting; medición de Dracut.
Ver `CHECKLIST-6.json`. No declarar estable mientras falten esas comprobaciones.

Contenidos propios: CC BY-NC-SA 4.0. Cada componente de terceros conserva su licencia;
xterm.js se distribuye con su licencia MIT. No se atribuye esta licencia de contenidos
a Fedora, OpenSSH, aiohttp, AsyncSSH ni a sus dependencias.
