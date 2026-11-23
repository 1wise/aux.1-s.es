# AUX 8.0.1-beta.5 — Kernel Modeler

Timestamp: 2026-11-23 | Version: 8.0.1-beta.5  
Author & Credits: https://www.alawise.es/1-s

Kernel Modeler añade un preset especializado al selector web, al submenú ISO y medios y a `./aux kernel-modeler`. Se elige expresamente instalador ISO, raíz nueva o sistema actual. El sistema actual permanece al final del selector. La base inicial es de consola, con base + kernel-modeler y complementos ajustables.

Debian, Fedora y Alpine reciben sus paquetes nativos para Kconfig, GCC, compilación, ELF/BTF, initramfs, procedencia, firmas y laboratorio QEMU/OVMF x86. Los índices oficiales contienen respectivamente los 30, 33 y 31 nombres del rol, con fuentes y hashes en `config/kernel-modeler.packages.json`. Antes de generar una ISO se exige resolver los paquetes en el constructor. El compilador es nativo; la compilación cruzada requiere una toolchain explícita.

Los perfiles contienen `kernel-modeler/model.json`, lista de paquetes y guía. El sistema preparado recibe plantillas en `/usr/local/share/aux/kernel-modeler` y un espacio privado en `/work/kernel-modeler`. No se sobrescribe una ficha existente. La fuente y configuración empiezan pendientes; kernel_build=not-run y boot_test=not-tested. La construcción del kernel, revisión de hardening, claves, enrolamiento y prueba real hasta login forman fases posteriores explícitas. La guía detalla procedencia, Kconfig de la versión elegida, hardware, módulos, firmware, compilación separada y aceptación.

Los paquetes y árboles de trabajo se contabilizan fuera de los 24.000.000 bytes de fuentes de AUX. No se genera una nueva Rescue ni se modifica el arranque de los equipos al descargar o extraer este paquete.

Validación: 472 casos Python, 453 ejecutados y 19 omitidos; diez pruebas nuevas. Paridad DOM Python/JavaScript y comprobación visual de los tres destinos y las tres distribuciones. Se prueba instalación de plantillas en una raíz temporal. No se ha compilado ni arrancado un kernel propio ni instalado paquetes en Excalibur/Bastion.
