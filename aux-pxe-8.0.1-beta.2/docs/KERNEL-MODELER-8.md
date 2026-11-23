# Kernel Modeler — banco de trabajo de núcleos

Timestamp: 2026-11-23 | Version: 8.0.1-beta.2  
Author & Credits: https://www.alawise.es/1-s

Kernel Modeler prepara las aplicaciones y la ficha de trabajo para configurar, compilar e inspeccionar un kernel Linux propio. Es un preset especializado, disponible para Fedora, Debian y Alpine. El destino es explícito: instalador ISO, raíz nueva o sistema existente. La selección inicial es una base de consola con base + kernel-modeler; los complementos pueden ajustarse antes de ejecutar.

La suite incluye el selector y las guías. Los paquetes, fuentes Linux, árboles de compilación e imágenes resultantes se obtienen o construyen fuera de sus 24 MB de fuentes. El espacio real depende del kernel, configuración, información de depuración, paquetes y paralelismo. Conviene conservar ese presupuesto separado de las imágenes publicadas y sus despliegues.

## Entradas y destinos

En web: Instalar → Operación → Kernel Modeler → elegir destino. Exportar la selección JSON y revisar el plan en el constructor. El botón de perfil nativo exporta la selección de paquetes para el instalador de la distribución; el JSON permite además incluir las fuentes y aplicaciones AUX mediante el constructor ISO.

En terminal: `./aux kernel-modeler --interactive` o la opción Kernel Modeler del submenú ISO y medios. La configuración y la ejecución mantienen el mismo preset. Antes de aplicar se revisa el plan y se escribe APLICAR. Instalar sobre el sistema actual es un destino explícito y está al final de los selectores.

Plan para una raíz nueva:

    ./aux kernel-modeler --target-mode root --distro debian --root /mnt/kernel-lab

Plan para preparar un instalador:

    ./aux-setup --mode kernel-modeler --target-mode iso --distro fedora --iso /srv/iso/oficial.iso --iso-sha256 SHA256 --output /srv/build/kernel-lab.iso

`--apply` ejecuta el plan revisado; ISO requiere además `--check-packages`. La raíz nueva requiere un directorio vacío distinto de /. Sigue pendiente completar su disco, cargador y cuenta mediante el procedimiento de instalación. En Alpine se conserva setup-alpine y se entrega un perfil para aplicar expresamente después de instalar.

## Herramientas del preset

| Labor | Herramientas y equivalentes nativos |
| --- | --- |
| Configurar | make, ncurses, GCC; menuconfig/nconfig pertenecen a las fuentes Linux. |
| Compilar | GCC/C++, make/binutils, bc, bison, flex, Perl y Python. |
| Inspeccionar | ELF/libelf, OpenSSL y pahole/dwarves para BTF; file y las herramientas de binutils. |
| Preparar el arranque | kmod, Device Tree Compiler, cpio y compresores; dracut, initramfs-tools o mkinitfs según la base. |
| Revisar procedencia y firmas | Git, patch/diff, GnuPG, OpenSSL, pesign o sbsigntool y mokutil. |
| Laboratorio x86 | QEMU y OVMF para pruebas BIOS/UEFI. |

El compilador es nativo del constructor; el laboratorio QEMU/OVMF incluido se orienta a x86. La compilación cruzada exige elegir explícitamente una toolchain adicional y su arquitectura.

LLVM/Clang y Rust son alternativas o requisitos de configuraciones concretas; deben seleccionarse según la versión Linux que se vaya a compilar. El preset GCC no afirma cubrir cualquier configuración futura. Las aplicaciones se comprueban contra los repositorios nativos del constructor antes de generar la ISO; una comprobación de nombres no equivale a haber instalado o arrancado el resultado.

## Secuencia de trabajo

1. Definir arquitectura, hardware, controladores y firmware necesarios, objetivo de arranque —disco, ISO o iPXE— y modelo de amenazas.
2. Elegir una versión exacta de Linux y verificar su procedencia. Kernel.org firma el tar sin comprimir: una firma de `.tar` no se verifica directamente contra `.tar.xz`. Conservar URL, checksum, firma, firmante y fecha.
3. Conservar la configuración inicial y usar Kconfig de esa misma versión para resolver sus dependencias. Revisar los símbolos nuevos y el diff; no asumir que una configuración antigua equivale a una nueva.
4. Revisar reducción de superficie, protecciones de memoria, módulos, depuración e interfaces disponibles. El conjunto soportado depende de arquitectura, compilador y versión. La guía de autoprotección del kernel es una referencia, no una certificación automática.
5. Compilar en un directorio separado y conservar versión del compilador, `.config`, logs y hashes. Preparar módulos de la misma versión, firmware e initramfs compatibles.
6. Revisar firma de módulos y cadena de arranque antes de aplicar una política de rechazo. Preparar claves en un espacio privado; su generación o enrolamiento no se ejecutan desde este preset.
7. Probar el conjunto en VM y en el hardware previsto, guardar evidencias y registrar la prueba real en checkstatus. Preparar una ISO o disponer de paquetes no acredita llegada al login.

Los perfiles generados incorporan `kernel-modeler/model.json`, paquetes y esta guía. Una instalación que elija el rol recibe las plantillas en `/usr/local/share/aux/kernel-modeler` y espacio privado en `/work/kernel-modeler`. El modelo empieza con fuente y configuración pendientes, kernel_build=not-run y boot_test=not-tested. Es un banco de trabajo; la compilación de un kernel propio y la aceptación de seguridad son labores posteriores verificables.

## Referencias de origen

- Requisitos de la versión Linux seleccionada: https://docs.kernel.org/process/changes.html
- Kconfig y editores: https://docs.kernel.org/kbuild/kconfig.html
- Autoprotección: https://docs.kernel.org/security/self-protection.html
- Procedencia y firmas: https://www.kernel.org/signature.html
- Firma de módulos: https://docs.kernel.org/admin-guide/module-signing.html
