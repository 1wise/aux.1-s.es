# AUX 8.0.1-beta.4 — inventario Bastion y conexiones existentes

Timestamp: 2026-11-23 | Version: 8.0.1-beta.4
Author & Credits: https://www.alawise.es/1-s

Guardar la conexión FTP no activaba el inventario de checkstatus. Si checkstatus.bastion.enabled era false, la beta.3 terminaba sin intentar Bastion y sin explicar ese motivo. La beta.4 muestra el estado remoto, la configuración utilizada, los intentos, la alternativa elegida y el número de archivos observados.

En el tablero de 24 casillas, B abre Bastion. «Activar con el FTP/FTPS ya configurado» reutiliza host, usuario, puerto, ftp_root y la contraseña del almacén privado; muestra la raíz y su URL pública antes de APLICAR. No exige volver a introducir la contraseña. Después, C ejecuta checkstatus incluyendo Bastion. El mismo acceso está en AUX Config → Inventario Bastion.

Para una comprobación puntual desde consola, con el FTP configurado:

    ./aux checkstatus --bastion ftps

El parámetro incluye Bastion en esa ejecución, utilizando ftp_root y la URL pública de targets.bastion.base_url o download_url. No modifica la configuración guardada. El status conserva la huella de la configuración original y se puede utilizar después con generate. Añadir --dry-run muestra el alcance sin conexiones ni escrituras. --show solo muestra el informe guardado.

SSH admite contraseña sin clave privada ni certificado de cliente. mirror.ssh_auth acepta auto, key o password. Auto permite el diálogo de contraseña de OpenSSH cuando hay una terminal y utiliza modo por lotes cuando no la hay. Password necesita terminal; key mantiene la autenticación por claves/agente. La contraseña SSH no se guarda en el catálogo, argumentos ni variables de entorno, y no se reutiliza la contraseña FTP como contraseña SSH.

Se conserva StrictHostKeyChecking=yes. La identidad del servidor debe estar validada en known_hosts. No se desactiva esa comprobación para facilitar el acceso. Referencia técnica: [OpenSSH ssh_config](https://man.openbsd.org/ssh_config), BatchMode y NumberOfPasswordPrompts.

Si falla rsync y checkstatus.bastion.fallback_ftp está activado, el inventario usa la conexión FTP/FTPS ya configurada. Las raíces pueden ser distintas: SSH puede mostrar /home/cuenta/www y FTP /site. Cada directorio admite ftp_path para declarar la equivalencia. Si no se indica, solo se deriva una ruta cuando path pertenece a mirror.remote_root y existe ftp_root. No se utiliza una raíz SSH desconocida como raíz FTP.

El transporte alternativo respeta ftp_tls. FTPS sigue validando el certificado del servidor; un fallo no se convierte automáticamente en FTP sin TLS. El inventario solo lista nombres y tamaños: no sube ni descarga imágenes ni acredita hashes remotos o arranque hasta login. Si una conexión falla, las observaciones quedan desconocidas, conservando el antecedente de la última comprobación correcta; no se declaran ausentes por un error de acceso.

La activación sigue siendo explícita: desactivar Bastion se respeta y produce un aviso visible. Los perfiles sin conexión configurada no intentan acceder a servidores de ejemplo. La raíz y la URL pública deben corresponder al mismo contenido para generar enlaces correctos.

Validación: 21 pruebas nuevas; 531 casos Python, 512 ejecutados correctamente y 19 omitidos. Se validan las opciones de OpenSSH sin conectar. Las pruebas usan conexiones simuladas para autenticación y alternativa de inventario; falta repetir la conexión real desde el equipo con sus credenciales.
