# Validación de AUX 8

Timestamp: 2026-11-22 | Version: 8.0.0-beta.3  
Author & Credits: https://www.alawise.es/1-s

Resultados de la beta de fuentes del 22/11/2026:

| Comprobación | Resultado |
| --- | --- |
| Regresión de la suite | 298 casos, sin fallos, 12 omitidos. |
| Política, catálogo, checkstatus e integración AUX 8 | 42 casos, sin fallos. |
| Preparación y agentes de Rescue | 82 casos, sin fallos, 7 omitidos. |
| DOM del catálogo | Presets acumulables, chroot compartido, edición manual, destinos y exportación JSON correctos. |
| DOM del instalador y portal de orígenes | Ambas suites correctas. |
| PHP | 19 archivos con sintaxis correcta; cinco suites de foro, registro, CLI y enrolamiento correctas. |
| Generación web desde fuentes | 214 recursos, 140 orígenes comprobados por HTTP, aplicaciones y documentación generadas. |
| Manifiesto y paquete | SHA-256 por archivo y verificación integral del archivo comprimido. |

Son 422 casos Python: 403 ejecutados y 19 omitidos. Las omisiones corresponden
principalmente a herramientas de construcción de imágenes, integración de medios
y contratos que requieren privilegios del sistema o sockets AF_UNIX. No acreditan esas funciones
en este entorno. Los detalles de cada caso se obtienen con `unittest -v`.

Las pruebas usan directorios temporales, archivos de ejemplo y servicios locales
o simulados. La publicación desde inventario de Bastion se comprueba sin abrir
conexiones a Bastion. RAM y SSD mantienen copias distintas de un mismo recurso;
el catálogo público conserva una identidad y ofrece ambas ubicaciones observadas.
La prueba Git confirma solo catálogo y sidecar, conservando otros cambios preparados.
Los fallos de los trabajadores de descarga se propagan a la aplicación.

## Reproducción

Desde la raíz de fuentes, con Python 3.12 o posterior:

```bash
python3 -m unittest discover -s tests7 -p 'test_*.py'
python3 -m unittest discover -s tests8 -p 'test_*.py'
python3 -m unittest discover -s iso-assist -p 'test_*.py'
python3 build.py --output /ruta/nueva/preview
sha256sum -c SHA256SUMS
```

Las pruebas de agentes usan las dependencias declaradas en `cli/requirements.txt`;
la ejecución de esta entrega usó asyncssh 2.24.0 en un directorio de pruebas externo
a las fuentes. Las pruebas DOM requieren Node y jsdom:

```bash
node tests8/test_status_ui.cjs
node tests8/test_catalog_ui.cjs
node tests7/test_installer_ui.cjs
node tests7/test_origin_portal.cjs
```

Las cinco suites PHP son `tec/test_forum.php`, `tec/test_forums8.php`,
`tec/test_registry.php`, `tec/test_cli.php` y `tec/test_enroll.php`.
Cada una recibe un directorio temporal vacío como primer argumento. Se utilizó
PHP 8.4.27 con sus extensiones; no se enviaron correos ni se usaron cuentas reales.

## Límites de aceptación

El catálogo distribuido no contiene pruebas de login aprobadas. La generación
web no convierte ningún fixture en evidencia de un recurso del catálogo.

Quedan pendientes el inventario y despliegue real en Bastion, las descargas que
requieran resolver metadatos históricos, construir esta Rescue, arrancar por
BIOS/UEFI hasta login, probar procedimientos chroot y ejecutar el piloto CDN.
La publicación Sites se valida por separado; los timers systemd incluidos no se activan al extraer las fuentes. El nuevo alcance de API
para control y mantenimiento sigue pendiente de definición; el contrato previo
se conserva como borrador en `docs/api/`.

## Ampliaciones beta.2

Doce pruebas adicionales cubren identidad y perfiles nativos, escritura acotada al destino, límites de auditoría HTTP, bits observados, hash de revisión y adaptación en copia nueva sin estado privado. El DOM de estado comprueba orden de los 20 bits, ocho observados, ficha Info, edición CDE, exportación canónica e importación fijada al artefacto. El DOM de instalación compara también la identidad con los perfiles Python en las tres distribuciones. El foro Node prueba tableros, recetas base y aportaciones de políticas; las cinco suites PHP conservan sus contratos. No se han efectuado consultas pagadas GPT/Gemini, enrolamientos ni instalaciones reales.

Beta.3 añade cinco pruebas: despliegue offline por capas con fuentes opcionales, detección de corrupción antes de escribir, rechazo de escape de rutas ZIP, importación de los 69 perfiles sin máscara y copias self-assambler sin recursión ni trabajo privado. El paquete real se extrae en un directorio temporal y se comprueban sus fuentes e imagen por SHA-256.
