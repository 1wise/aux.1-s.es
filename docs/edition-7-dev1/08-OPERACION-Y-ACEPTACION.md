# Actualización semanal y aceptación

Timestamp: 2026-11-05 | Version: 7.0.0-dev.1  
Author and Credits: https://www.alawise.es/1-s

## Trabajo semanal en Excalibur

El requisito es ejecutar la actualización los sábados a las 03:00. La zona
horaria no está confirmada. `templates/aux-catalog-update.timer.in` propone UTC
de forma visible; cambiarla si se acuerdan las 03:00 de Andorra o del servidor.
No deducir la zona horaria del lugar físico del centro de datos.

El crawler nuevo aún no existe y el `.service.in` contiene marcadores de ruta,
cuenta y ejecutable. Es una plantilla de contrato, no una unidad lista para
copiar y habilitar. Cuando exista el ejecutable:

1. Configurar una cuenta de servicio y sus directorios de staging/publicación.
2. Rellenar el servicio y el temporizador; comprobar el calendario con
   `systemd-analyze calendar 'Sat *-*-* 03:00:00 UTC'` o la zona acordada.
3. Ejecutar manualmente la actualización y revisar sus resultados antes de
   habilitar la periodicidad.
4. Impedir ejecuciones simultáneas y conservar el resultado anterior si falla
   una descarga, verificación, receta o publicación.
5. Revisar timer y registros. No enviar automáticamente correo a terceros.

El trabajo actualiza enlaces y descargas oficiales según la selección. La
reconstrucción de las imágenes propias Fedora/Debian es una tarea distinta,
que debe registrar versiones de repositorios, paquetes y cargadores.
La actualización de una llave personalizada en uso utiliza su gestor de
paquetes; no se regraba una imagen completa encima de sus datos sin migración.

## Comprobaciones de la edición instalada

Esta lista registra trabajo pendiente y resultados reales. No marca como
superado lo que solo se verificó mediante sintaxis o inspección de archivos.

| Comprobación | Resultado inicial |
|---|---|
| Firma del medio oficial y hash de la ISO personalizada | Pendiente |
| Lista de paquetes disponible en la rama elegida | Pendiente |
| ISO arranca el instalador en BIOS | Pendiente |
| ISO arranca el instalador en UEFI | Pendiente |
| Instalación estándar en disco virtual nuevo | Pendiente |
| Disco instalado arranca sin la ISO | Pendiente |
| USB arranca en otra máquina y conserva datos tras reiniciar | Pendiente |
| Kernel, módulos, firmware e initramfs corresponden | Pendiente |
| XFCE, terminal local y suite funcionan sin red | Pendiente |
| DHCP, DNS, Wi-Fi y red cableada | Pendiente |
| Cockpit y SSH por las vías elegidas | Pendiente |
| AUX Assist portado y revocación de la intervención | Pendiente |
| Dos terminales independientes y reconexión autorizada | Pendiente |
| Rueda de tmux e historial nuevo de 20.000 líneas | Ajuste incluido; pendiente en imagen 7 |
| Barra web y Shift+RePág | Pendiente; no resuelto por mouse on |
| API GPT/Gemini, claves privadas y cierre de sesiones | Pendiente |
| QR TOTP en el alta técnica | Pendiente de implementación |
| Entrada/salida automática de una instalación | Pendiente de implementación |
| iPXE BIOS/UEFI y rutas publicadas | Pendiente |
| Secure Boot de cada artefacto | Sin declarar; pendiente |

Para la adquisición forense, añadir una prueba con disco sintético y evidencia
de que el modo de inspección no escribió en el origen. No usar un disco de un
caso real como primer ensayo de un asistente nuevo.

## Registro de construcción

Guardar para cada intento fecha, rama/codename, medio y hashes, perfil utilizado,
versiones de las herramientas, lista de paquetes instalada, firmware de la VM,
kernel arrancado, hardware de destino y errores completos sin secretos.
Reutilizar un perfil permite repetir la selección; obtener exactamente los
mismos paquetes exige conservar la instantánea del repositorio. Una rama
rolling por sí sola no garantiza reconstrucciones idénticas byte a byte.
Una captura del escritorio demuestra ese arranque concreto; no sustituye las
comprobaciones de persistencia, asistencia y otros firmwares.

Si la instalación no progresa, conservar los logs antes de reconstruir. En
Fedora revisar los logs Anaconda dentro del entorno de instalación; en Debian
los logs de Debian Installer. No asumir que el error de D-Bus del USB persistente
6.4 está explicado por una supuesta restricción general contra la persistencia:
la causa concreta de aquel fallo no quedó demostrada.

