# USB AUX 6.3

Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
Author & Credits: https://www.alawise.es/1-s

El cargador pequeño BIOS/UEFI es usb/aux-ipxe-usb.img, con negro de fondo, verde
normal y azul oscuro de selección. SHA-256 y tamaño están en usb/build-info.json.
No contiene una ISO AUX ni persistencia de sistema: carga el menú de red.

Para la llave combinada, usar aux-portable-6.3.0-dev.1-kit.zip con la ISO AUX 6.3
compilada y verificada. Su README.md describe la construcción de un archivo nuevo,
el perfil persistente predeterminado, arranque limpio y red, sistema actualizable,
claves API precargadas y reanudación de asistencia. No se incluye una imagen
combinada ya construida ni se modifica ningún dispositivo físico en la preparación.
