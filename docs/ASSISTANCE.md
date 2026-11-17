# Asistencia y sistemas

Timestamp: 2026-11-17 | Version: 7.0.1-beta.4
Author & Credits: https://www.alawise.es/1-s

`aux-enter --interactive` inspecciona raíces y contenedores detectados. Elegir
primero el destino y después inspección de lectura o reparación mediante
chroot. La reparación modifica el sistema de destino y exige el plan y la
confirmación indicados. No seleccionar el sistema anfitrión por suposición.

`aux-assist` conserva los controles de asistencia del equipo. La intervención
requiere consentimiento, identidad y contacto verificable del técnico,
huella de clave y posibilidad de observar la sesión. El usuario mantiene sus
propias terminales y puede interrumpir la intervención.

TEC es opcional y utiliza su propio servicio, cuentas y configuración. Las
rutas públicas AUX/PXE no contienen sus claves ni registros privados. El
foro y las aportaciones requieren moderación antes de convertir una receta
en parte del catálogo verificado.

`aux-observe` añade inspección osquery y consulta osctrl a esta área. Los
resultados pueden contener inventario del equipo; no se incorporan a la web
ni al paquete fuente. Ver OBSERVABILITY.md para configuración y alcance.

## Llaves de asistencia propias

Las llaves USB, los soportes SSD y el entorno Live de asistencia pertenecen a este capítulo. El generador usb/portable/build.py prepara un archivo de imagen; no escribe un dispositivo físico. Revisar el medio, su suma, la capacidad y la salida, y probar después el arranque en el destino.
