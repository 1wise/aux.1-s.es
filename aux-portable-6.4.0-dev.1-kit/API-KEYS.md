# Preparar GPT y Gemini antes de empezar

Timestamp: 2026-10-17 | Version: 6.3.0-dev.1
Author & Credits: https://www.alawise.es/1-s

El perfil USB personalizable admite dos claves opcionales. Cada proveedor puede
tener su propia clave guardada, usar una manual o quedarse sin configurar.
Este kit contiene el soporte y las pruebas con fixtures; la aceptación real en
una ISO arrancada con SELinux enforcing sigue pendiente.

## Preparación desde el equipo de trabajo

Construir y grabar primero la llave combinada. Montar su partición ext4 en un
equipo Linux y abrir con un editor local, como root, los archivos siguientes:

| Proveedor | Ruta relativa a la raíz de la partición ext4 |
| --- | --- |
| GPT / OpenAI | `AUX/private/api/openai.key` |
| Gemini | `AUX/private/api/gemini.key` |

El constructor crea `AUX/private/api` vacío. Cada archivo contiene únicamente la
clave, en una línea, sin comillas, JSON ni `export`. Un salto de línea final es
válido. No hace falta crear el archivo del proveedor que no se vaya a usar.

Los directorios `AUX/private` y `AUX/private/api` deben pertenecer a root y tener
permisos 0700; los archivos, propietario root y permisos 0600. Después de editar,
cerrar el editor y desmontar correctamente la partición antes de retirar la llave.
Las claves quedan en archivos privados sin cifrado en esta versión. La copia de
la llave que contenga claves debe mantenerse privada.

Las claves se añaden después de grabar cada llave personal. La ISO pública, el
ZIP de fuentes, ai.json, GRUB y los menús de red se distribuyen sin ellas.

## Uso en el cliente

1. Arrancar la primera entrada de GRUB, el perfil USB personalizable.
2. Abrir G para GPT o M para Gemini e indicar el modelo habilitado, si no estaba
   fijado ya en la configuración pública.
3. Cuando exista una clave preparada, aparece `L llave / V visible / O oculta [L]`.
   Enter selecciona la guardada sin mostrarla ni volver a escribirla. V/O permiten
   introducir otra para esa sesión, sin sustituir el archivo de la llave.
4. Si no existe una clave válida, se conserva la entrada manual V/O. Un archivo
   inválido no se ejecuta ni se envía al proveedor.

Guardar una clave no realiza consultas ni inicia G/M por sí solo. El modo limpio
y el arranque por red mantienen la entrada manual; esta versión no importa las
claves privadas del USB en esos perfiles.

## Guardar, sustituir y borrar desde F6

La opción K del perfil personalizable abre el gestor local. G/M seleccionan el
proveedor; S guarda o sustituye su clave y B la borra. La entrada admite V visible
u O oculta, con visible por defecto para claves largas. Sustituir o borrar detiene
primero la sesión de ese proveedor; G/M permiten abrirla después con la nueva selección.

La opción I detiene ambos asistentes y elimina las copias de preparación en /run.
Los archivos guardados en la llave permanecen hasta borrarlos con K. `/salir` cierra
la conversación y no borra la clave persistente. No se garantiza borrado criptográfico
de RAM ni de bloques flash al borrar un archivo.

## Entrega al servicio

El control local root comprueba UUID del medio, perfil de persistencia y permisos.
Lee solo el proveedor elegido, con un tamaño acotado, y prepara una copia 0600 en
`/run/aux-api-source`. systemd la entrega a la unidad correspondiente con
`LoadCredential=`. El cliente sin root la lee desde `CREDENTIALS_DIRECTORY`.
La variable contiene una ruta; la clave no se incluye en variables de entorno,
argumentos de proceso, registros ni mensajes de estado.

El parche público de `live-patch` contiene ai.py, ai_agent.py, assist.py, agent.py y support_case.py. Dentro
del repositorio completo, el constructor puede usar directamente esos archivos
desde iso-assist/payload. Se instalan solo en el overlay personalizable y sus
drop-ins. La base limpia de la ISO no cambia.

Pruebas con claves ficticias: selección por proveedor, clave de 165 caracteres,
entrada manual alternativa, archivos ausentes y malformados, rechazo de symlinks,
hardlinks, FIFOs y permisos públicos, eliminación de copias antiguas, sustitución
y borrado desde K y ausencia del secreto en la salida. Faltan arranque real y
comprobación de la entrega de credenciales bajo SELinux enforcing.

Referencias primarias:

- https://developers.openai.com/api/reference/overview#authentication
- https://systemd.io/CREDENTIALS/
