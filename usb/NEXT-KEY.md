<!-- Timestamp: 2026-10-13 | Version: 1.2.0-dev.0 | Author & Credits: https://www.alawise.es/1-s -->

# Próxima llave y SSD de asistencia

Especificación pendiente de implementar y probar. La imagen USB publicada sigue en 1.1.1; esta nota no cambia su particionado ni escribe dispositivos.

La próxima llave de 32 GB tendrá GRUB con espera de 5 segundos, iPXE, arranque local de AUX Rescue y acceso a firmware mediante fwsetup cuando UEFI lo soporte. En BIOS clásico no hay un comando GRUB universal para abrir su configuración: indicar la tecla del fabricante. Mantener teclado del cliente activo y la autorización explícita para SSH.

Propuesta ligera: partición EFI de 512 MiB, área de rescate de 6 GiB para kernel/initramfs/SquashFS y herramientas de copia, y partición ext4 de trabajo con el resto. El rescate puede montar la unidad persistente de trabajo solo después de identificarla por UUID y verificar que corresponde al dispositivo preparado. Las colas de correo, credenciales y datos de un sistema instalado no pertenecen al Live temporal.

La copia recuperable debe ser una plantilla de la zona de arranque/rescate o un paquete de sus componentes, no una imagen completa de 32 GB almacenada dentro de la misma llave de 32 GB. Así se evita una copia que se incluya a sí misma. La herramienta de clonación seleccionará otro USB por modelo, serie y capacidad, pedirá confirmar la escritura y creará su partición de trabajo con el espacio restante. Nunca copiar el disco del cliente ni incluir claves privadas en la plantilla pública. Las llaves nominales de 32 GB no tienen necesariamente idéntico número de sectores.

Para un SSD de 500 GB se aplica la misma zona de rescate; el técnico prepara después las particiones del sistema operativo y del trabajo. Al instalar el sistema debe conservar una entrada de rescate en su GRUB y validar arranque BIOS/UEFI, UUIDs y actualizaciones de kernel. Reservar o reutilizar espacio requiere una decisión explícita sobre los datos existentes; no instalar ni repartir automáticamente un SSD conectado.

Fases pendientes: diseño de imagen; construcción mínima y manifiesto; herramienta de clonación; identificación/montaje de trabajo; integración GRUB/OS; pruebas VM y hardware; recuperación y actualización. La sesión de asistencia puede usar teclado local y SSH; no se bloquea el dispositivo de entrada del cliente.
