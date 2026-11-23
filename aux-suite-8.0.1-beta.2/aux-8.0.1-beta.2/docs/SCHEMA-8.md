# Contrato de datos y palabra de 24 bits

Timestamp: 2026-11-23 | Version: 8.0.1-beta.2  
Author & Credits: https://www.alawise.es/1-s

El formato de esta beta se fija como **PASCDE**, seis hexadecimales. La política
editable es CDE y P; A y S proceden de observaciones. Se utilizan los 24 bits.
`policy24.py` comprueba el ancho de cada campo y mantiene sus funciones separadas.

| Campo | Bits | Codificación |
| --- | --- | --- |
| P | 23–20 | Usuario `1`, tendencia del sector `2`, obligatorio `4`, sugerido por IA para el sector `8`. |
| A | 19–16 | RAM `1`, SSD `2`, origen `4`, Bastion `8`; disponibilidad observada. |
| S | 15–12 | Fuente `1`, desplegada `2`, receta `4`, comprobada hasta login `8`. |
| C | 11–8 | Nivel en bits 9–8; candidato PXE `4`, resolver `8` dentro del dígito. |
| D | 7–4 | Descargar `1`, actualizar `2`, preservar `4`, archivar `8`. |
| E | 3–0 | RAM `1`, SSD `2`, origen `4`, Bastion `8`; ubicaciones deseadas. |

Un cero observado significa que no existe evidencia positiva vigente. El detalle
JSON distingue ausencia, error, desconocido, ambigüedad y datos históricos. Los
bits compactos no sustituyen esa información.

## Reglas de combinación

| Combinación | Comportamiento |
| --- | --- |
| Descargar o actualizar, sin destino local | Adquirir en caché; no desplegar. |
| Destino local, sin descargar/actualizar | Usar caché existente; si falta, detener la fase con explicación. |
| RAM y SSD | Dos destinos solicitados; se evalúan por separado. |
| Bastion | Respaldo para balancear descargas; presupuesto igual al SSD, uso independiente. |
| Origen | Mantener procedencia y enlace; no implica transferencia propia. |
| Preservar y actualizar | Conservar el artefacto anterior y adquirir el nuevo con identidad separada. |
| Archivar | Implica preservación efectiva, sin reescribir la política introducida. No activa borrados. |
| Receta existente | Activa su presencia; su prueba de arranque se registra aparte. |
| Candidato PXE | Solicitud de investigación, sin aprobación automática de receta. |
| Resolver | Permite sustituir una referencia dinámica por un artefacto concreto dentro de su regla. |

Niveles C: `0` desactivado; `1` consulta de fuente declarada; `2` versión,
arquitectura, mirror y checksum según adaptador; `3` habilita el alcance profundo
que ofrezca el adaptador. Los límites y hosts de confianza se conservan. La
cobertura efectiva depende de los adaptadores incluidos; no se afirma que todos
los índices y procedimientos de todas las distribuciones estén soportados.

## Catálogo

`schema` es `aux-catalog-v8`; `entries` contiene recursos con `id`, `family`,
`release`, `architecture`, `kind`, `original_url` y `policy`. El ID es estable.
La identidad de artefacto depende de procedencia, versión, arquitectura y hash.
La identidad de prueba incluye además componentes y receta.

`artifact_type` distingue ISO, componente, sistema raíz o manifiesto. Los recursos
chroot declaran `deploy_method` y `procedure_url`. `paths` permite fijar rutas
relativas por destino. Sin ellas, la publicación usa un prefijo de destino,
recurso, versión y pin que conserva copias separadas en RAM y SSD, y archivos
distintos con el mismo nombre. El pin de
los archivos no cambia el identificador de las páginas.

Los checksums oficiales conservan `checksum_source`; una suma local no acredita
la firma del editor. Los metadatos anteriores siguen siendo históricos hasta
resolver y comprobar sus fuentes.

Las recetas utilizan datos estructurados: Linux o menú de proveedor admitido,
firmware, arquitectura, kernel, initrd y argumentos. No se ejecuta shell recibida
como dato de receta. Solo las recetas aprobadas entran en el menú de componentes;
la aprobación no activa S:8.

## Estado

`status.json` utiliza `aux-status-v1`: fecha, huellas del catálogo/configuración,
observaciones por ubicación y máscara por recurso. `generate` exige una
instantánea vigente para el mismo catálogo/configuración.

La prueba usa `aux-boot-evidence-v1`: recurso, identidad, resultado `login-reached`,
fecha, entorno, firmware y hash del log. El log permanece privado. Modificar el
artefacto/receta o perder la evidencia invalida la afirmación para esa combinación.
Los informes públicos no incluyen rutas privadas de logs.

Los 69 perfiles aportados por Ei se incorporan en beta.3 como referencias de origen, sin capability_mask. Sus arquitecturas declaradas, artefactos y procedencia se conservan como metadatos; no se convierten en pruebas de descarga, firma ni login.

## Prioridad P

`priority` es un hexadecimal independiente de `policy` CDE; su defecto es `0`, compatible con catálogos anteriores. Los indicadores se combinan: `5` significa usuario y obligatorio; no es una escala numérica. `priority_sectors` delimita las preferencias de tendencia/IA a Fedora, Debian o Alpine; sin ámbito explícito se usa la afinidad del recurso. P no activa download, deploy, checksum, disponibilidad ni login.

La propuesta ordena primero obligatorio, después usuario, tendencia y sugerencia IA dentro de su sector, y finalmente los criterios técnicos. Obligatorio conserva su selección si excede el presupuesto y muestra el conflicto; no elude los límites de ejecución ni permite bytes sin integridad. Una sugerencia IA no equivale a una receta aprobada. Las preferencias manuales se conservan.

    ./aux catalog set-priority --resource ID --priority 5 --apply
    ./aux catalog set-priority --resource ID --priority A --sector fedora --apply

El dígito anterior R queda sustituido por P. Los A/S de instantáneas importadas no sobrescriben P ni CDE editados. Se conservan los ocho bits observados y se muestran 24 casillas en orden 23…0.
