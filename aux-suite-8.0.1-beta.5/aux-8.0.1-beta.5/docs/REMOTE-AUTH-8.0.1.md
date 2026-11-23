# AUX 8.0.1-beta.5 — contraseñas y raíz visible de Bastion

Timestamp: 2026-11-23 | Version: 8.0.1-beta.5
Author & Credits: https://www.alawise.es/1-s

La beta.4 permitía el aviso nativo de SSH, pero no tenía un campo para guardar su contraseña. Además, el error FTP agrupaba login, TLS y directorios en un mensaje único. La beta.5 corrige ambos puntos y permite revisar el directorio FTP sin adivinar equivalencias con SSH.

Desde ./aux checkstatus --interactive, B abre Bastion con estas opciones:

1. Contraseña SSH / rsync: entrada oculta, guardada como ssh_password. Selecciona mirror.ssh_auth=password.
2. Contraseña FTP / FTPS: entrada oculta e independiente, guardada como ftp_password.
3. Editar conexión: host, usuario, puerto y raíz propios de SSH o FTP. SSH incluye autenticación, identidad y known_hosts opcionales.
4. Probar SSH / rsync: confirma autenticación y un comando de lectura. No comprueba todavía todos los permisos de rsync ni arranque.
5. Probar FTP / FTPS: muestra PWD tras login, carpetas visibles y si la raíz configurada es accesible.
6. Explorar FTP: navegar por las carpetas que muestra la cuenta, elegir la raíz pública y revisar sus equivalencias antes de APLICAR.

Una ruta como /home/cuenta/bastion puede existir en SSH y no ser visible en FTP. El servidor FTP puede mostrar / como inicio y bastion como subcarpeta. Este es solo un ejemplo: la selección se basa en el listado real. El explorador corrige ftp_root y la equivalencia ftp_path del inventario; no cambia la raíz SSH. Al terminar, activar el inventario con la conexión revisada y ejecutar C.

Comandos equivalentes, desde las fuentes de la suite:

    ./aux-config secret ssh_password
    ./aux-config secret ftp_password
    ./aux-config test-connection rsync
    ./aux-config test-connection ftp

Usar --config y --secrets antes del subcomando si se utilizan rutas personalizadas. El almacén privado tiene modo 0600 y su carpeta 0700, fuera del código y la web. Se utiliza el almacén del usuario que ejecuta AUX: una ejecución como root no lee automáticamente el de otra cuenta. No poner las contraseñas en fast-boot.json, config.json, el catálogo, una URL ni los argumentos del comando.

SSH usa SSH_ASKPASS_REQUIRE=force cuando hay contraseña guardada. Un helper temporal lee una tubería privada 0600 dentro de una carpeta 0700. La contraseña permanece en memoria y en la tubería; no se escribe en el helper, en un archivo de texto temporal, en argumentos o en variables de entorno. La carpeta y la tubería se eliminan al finalizar. Checkstatus, deploy y las transferencias/verificaciones rsync utilizan el mismo mecanismo. Sin contraseña guardada, el modo password puede solicitar entrada oculta en una terminal. El modo key conserva claves/agente y no utiliza ssh_password.

StrictHostKeyChecking=yes permanece activo. Un fallo de known_hosts se comunica antes de tratarlo como un problema de contraseña. Verificar la huella desde la misma cuenta que ejecuta AUX; no se aceptan huellas nuevas automáticamente. Referencia: [OpenSSH ssh](https://man.openbsd.org/ssh), SSH_ASKPASS_REQUIRE.

FTP informa la fase: conexión, TLS, login, protección de datos, PWD, directorio o listado/datos. Un directorio rechazado incluye la raíz solicitada y el PWD observado después del login. Los errores de autenticación eliminan contraseñas conocidas del texto. La conexión FTPS valida el certificado y mantiene protegida la conexión de datos. La conexión FTP usa siempre ftp_root aunque el transporte principal del mirror sea rsync.

Las pruebas de conexión y exploración no suben ni descargan imágenes. Listados y tamaños no acreditan un hash remoto ni llegada al login. Las credenciales reales de Bastion no se han utilizado durante la validación: se comprueban autenticación OpenSSH y FTP/FTPS en servidores de prueba locales, con contraseña, raíz aislada y certificado de prueba de confianza explícita.

Validación: dieciocho pruebas nuevas; 549 casos Python, 530 ejecutados correctamente y 19 omitidos. SSH y FTP/FTPS se prueban contra servidores locales reales. El acceso concreto al alojamiento y sus permisos de rsync quedan pendientes de repetir con las credenciales de la instalación.
