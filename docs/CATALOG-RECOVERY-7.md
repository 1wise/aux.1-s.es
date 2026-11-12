# Recuperación de URL desde el informe de rastreo

Timestamp: 2026-11-11 | Version: 7.0.0-beta.19
Author & Credits: https://www.alawise.es/1-s

Al terminar el rastreo o abrir su informe, AUX Catalog ofrece revisar las
descargas pendientes y los recursos disponibles con avisos. Por ejemplo, un
Super Grub con `resolved / HTTP passed` y versiones posteriores que devuelven
404 conserva una opción válida; la intervención es opcional.

Cada recurso permite:

1. Conservar la versión disponible o dejar pendiente la incidencia.
2. Introducir una URL HTTPS del archivo y su página de referencia.
3. Pedir una propuesta a Gemini.
4. Pedir una propuesta a GPT / OpenAI.

Una URL manual vacía devuelve a estas opciones. Las propuestas API se presentan
para elegir una candidata; el proveedor no aplica cambios al catálogo. La URL
debe corresponder a la edición, arquitectura y canal de la regla. Se comprueban
el destino público HTTPS y sus cabeceras antes de ofrecer GUARDAR. Esta revisión
no descarga imágenes ni certifica checksums, firmas o arranque.

Si la URL anterior no tenía regla, una URL manual puede vincularla a una regla
existente que identifique el archivo de forma única. Para consultar la API en ese
caso se elige antes la regla adecuada. Una distribución o edición nueva necesita
configurar su propia fuente mediante las funciones existentes del catálogo.

## Versiones que cambian con frecuencia

Las candidatas se añaden a las opciones del rastreador, junto a las obtenidas de
los índices actuales. Cada rastreo vuelve a consultar esos índices y ordena las
versiones dentro del mismo canal. Una URL introducida para resolver una incidencia
no fija permanentemente esa versión. También se contemplan URL alternativas
del mismo nombre de archivo cuando la primera devuelve 404.

Si el índice falla y una candidata revisada sigue disponible, el informe conserva
el aviso del índice y registra el origen manual/GPT/Gemini de la URL utilizada.
Cuando la fuente vuelve a publicar una versión más nueva disponible, se utiliza
esa versión en el siguiente rastreo. Las reglas actuales siguen aplicándose a
las candidatas guardadas; cambiar arquitectura o canal no reutiliza una candidata
que haya dejado de coincidir.

## Persistencia y publicación

El registro está en `url-candidates.json`, dentro del directorio de estado elegido
para el rastreo, junto a `crawl-report.json`. No sustituye la configuración de
fuentes. Conserva hasta ocho candidatas por recurso y una copia anterior a cada
revisión. Registra URL, referencia, regla, origen y fecha; las claves API quedan
fuera del registro.

Después de guardar una o varias URL se puede elegir «Rastrear de nuevo con las
URL revisadas». Guardarlas también permite utilizarlas en el siguiente rastreo,
incluido el no interactivo. La sincronización de listas sigue mostrando el diff
y requiere APLICAR. Si las candidatas cambian después del informe, hay que volver
a rastrear antes de sincronizar las listas.

## Asistencia API

Se reutilizan los modelos y límites de `config/catalog.assist.json` y los ajustes
públicos de `fast-boot.json`. La consulta requiere elegir proveedor y modelo y
revisar la petición con CONSULTAR. La clave se obtiene del entorno o se introduce
sin eco en la terminal. Se realiza una llamada por solicitud, sin reintentos
automáticos ni llamadas API desde el servicio periódico.

El contexto incluye la incidencia concreta, su regla, la fecha de consulta y un
extracto acotado del índice público que acaba de rastrearse. La respuesta contiene
como máximo cuatro URL candidatas con referencia y explicación. Si la evidencia
es insuficiente, el modelo puede devolver una lista vacía. La propuesta no declara
disponibilidad actual hasta que la comprobación local haya pasado.

## Comprobaciones

Veintiuna regresiones cubren recuperación, conservación de HTTP/checksum/firma
como estados distintos, cambios posteriores de versión, espejos del mismo archivo,
fuentes inaccesibles, reglas y destinos rechazados, registro y copias, sincronización
de listas, esquemas de ambos proveedores y cancelación antes de llamar a la API.
Una PTY real prueba la navegación manual/Gemini y la cancelación de la consulta.
Las respuestas API y las cabeceras HTTP de estas pruebas son simuladas; no se
realizan llamadas facturables ni se certifican URL actuales de Super Grub.

Para actualizar el programa conservando un rastreo existente, usar el paquete
completo nuevo y abrir aux-catalog con --config, --output, --cache y --url-file
apuntando a los archivos de trabajo anteriores. El campo «Publicación de metadatos»
identifica el directorio de estado que contiene el informe y las candidatas.
