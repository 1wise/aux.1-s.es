# AUX 8.0.1-beta.3 — lotes, capacidad y réplicas

Timestamp: 2026-11-23 | Version: 8.0.1-beta.3  
Author & Credits: https://www.alawise.es/1-s

Download continúa después de un fallo individual de resolución, HTTP, transferencia o integridad. Muestra líneas completas por recurso: RESOLVE, SKIP, DOWNLOAD, VERIFY y DONE/ERROR. Durante la transferencia muestra bytes, porcentaje cuando hay tamaño y velocidad media. Al finalizar presenta los errores y guarda `download-report.json` junto al status configurado; devuelve código 1 si hubo fallos, sin cancelar los recursos válidos restantes. `--json` conserva un informe procesable y el progreso se escribe en stderr.

NixOS minimal utiliza la tabla del canal oficial para resolver revisión, tamaño y SHA-256. Agama obtiene el tamaño del Metalink del proveedor y exige el SHA-256 de su sidecar oficial; si Metalink aporta también hash deben coincidir. No es necesario autorizar un mirror arbitrario para consultar esos metadatos. Las dos imágenes se descargaron completas y se verificaron. Esa integridad no acredita un arranque hasta login.

## Presupuesto y presets

| Selección | RAM | SSD | Bastion |
| --- | ---: | ---: | ---: |
| Un preset | 10 GiB | 75 GiB | 75 GiB |
| Tres presets | 30 GiB | 225 GiB | 225 GiB |

Se usan GiB explícitos en ambas interfaces. `fast-boot.json` nuevo declara 30/225 GiB, reserva RAM 0 y cuotas 10/75 por preset; una instalación conserva sus límites físicos personalizados. La reserva RAM sigue disponible. Bastion deriva siempre su límite del SSD. El presupuesto del paquete de fuentes sigue siendo 24.000.000 bytes.

La web ofrece una tabla viva y ajustes en Catálogo; el diálogo muestra la previsión en el panel de detalle antes de ejecutar y permite ajustar presupuestos o selección en esa pantalla. `aux-config -i` incluye presupuestos por preset. La exportación web incluye `planning`, y `catalog import --input catalog.json --apply` conserva esa previsión; nunca eleva los límites físicos del equipo por encima de su configuración.

El fondo común es la suma de los presets seleccionados. Cada ID compartido se cuenta una sola vez; el ahorro y margen quedan visibles para ampliar manualmente la selección. Las propuestas de preset dan prioridad a chroot, recetas, medios ligeros y x86, e incorporan solo lo que cabe por tamaño conocido. Conservan como origen los excesos; una elección manual tiene prioridad y puede producir una advertencia de exceso. Los recursos sin tamaño aparecen pendientes y no permiten asegurar que el conjunto cabe. Download vuelve a resolver los metadatos permitidos antes de transferir y admite solo las imágenes que caben en el fondo SSD; la previsión de deploy puede requerir ajustes posteriores.

Las columnas distinguen imágenes y deploys. SSD incluye la caché de adquisición y las copias públicas físicas; una ISO extraída puede ocupar caché + copia ISO + árbol. El árbol se estima igual al tamaño ISO hasta disponer de `deployment_size_bytes`, que permite fijar una medida. Los montajes RAM no duplican un árbol ISO. El montaje SSD reutiliza la caché. Bastion recibe archivos de imagen en el deploy actual. No se promete un tamaño exacto de extracción ni se elimina caché antigua automáticamente.

## Enlaces de las réplicas

Checkstatus reconoce tanto rutas versionadas como copias anteriores en subdirectorios, cuando nombre y tamaño identifican un único archivo. Dos candidatos se consideran ambiguos. Presencia no equivale a integridad ni a arranque comprobado. El generador conserva enlaces observados RAM/SSD/Bastion en el portal, catálogo de trabajo y JSON público, además del origen. También conserva la evidencia del descubrimiento local y no pierde una copia por existir el mismo nombre en dos ubicaciones.

La ruta personalizada de status se transmite a las páginas de estado. En `aux-config -i` se añaden activación, transporte y directorios del inventario Bastion. Cada directorio declara una ruta remota y la URL pública de esa misma raíz. No se adivina disponibilidad desde los bits E.

Después de actualizar: revisar configuración y selección, Download, deploy, checkstatus y generate. Si ya existen los medios, repetir checkstatus y generate es suficiente para regenerar enlaces; el resumen indica cuántas copias de Bastion se reconocieron. Esta entrega no instala ni configura Excalibur/Bastion a distancia.

## Prioridad: los 24 bits en uso

El formato pasa de RASCDE a **PASCDE**. El dígito antes reservado es P: usuario `1`, tendencia del sector `2`, obligatorio `4`, sugerido por IA para el sector `8`. Son indicadores independientes, combinables, no niveles 0–15. `priority` mantiene ese hexadecimal; `priority_sectors` puede limitar las sugerencias de tendencia/IA a Fedora, Debian o Alpine. El defecto `0` conserva los catálogos anteriores.

La web de estado muestra 24 casillas, bits 23 a 0: P/CDE editables y A/S observados. El catálogo, CLI y dialog permiten editar P. La prioridad no activa acciones, no salta verificaciones y no acredita login. Los obligatorios conservan la selección ante excesos y se informa del conflicto; siguen sujetos a límites físicos. Las propuestas IA aprobadas se señalan con bit 8, conservando las preferencias usuario/obligatorio existentes. La importación de estado no modifica P ni CDE manuales.
