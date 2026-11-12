# Probar las aplicaciones nuevas en una Live ya arrancada

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

La corrección del selector se puede probar sustituyendo las fuentes completas
de las aplicaciones en la RAM de la Live. La ISO conserva su versión original;
para incorporar el cambio al siguiente arranque se debe reconstruir el medio.

Usar el TAR completo y comprobar su SHA-256 antes de extraerlo. Preparar un
directorio temporal, extraer sin restaurar propietarios del equipo constructor
y comprobar todos los archivos con `sha256sum -c --quiet SHA256SUMS`.

La ubicación de las aplicaciones de esta Live es /usr/local/lib/aux. Conservar
una copia completa de ese directorio antes de copiar las fuentes verificadas.
Mantener propietario root y permisos de lectura/ejecución de la entrega. Después
de copiar, volver a comprobar SHA256SUMS y los contextos SELinux con restorecon.
El lanzador aux-enter ya apunta a esa ubicación y abre un proceso nuevo.

Este recorrido no instala paquetes, no inicia servicios, no escribe el marcador
/etc/aux-installed y no modifica /usr/share/aux-assist, /var/lib/aux-assist ni los
discos de prueba. El agente de asistencia que ya está conectado sigue usando
su cliente en /usr/share/aux-assist. La copia anterior permite revertir el código.

Para transferir el TAR desde el constructor, se puede servir únicamente ese
archivo en un directorio temporal mediante http.server, enlazado a 127.0.0.1.
La red user de QEMU permite acceder al host desde 10.0.2.2. Detener el servidor
temporal al terminar la transferencia. No se utiliza como servidor de producción.

La prueba de interfaz alcanza los menús de dispositivo y LV con curses real en
una PTY; la prueba de activación y montaje de LVM se realiza por separado sobre
el disco virtual elegido. Ver /work con findmnt no acredita un montaje del LV.
