# Checklist de entrega de la primera beta

Timestamp: 2026-11-23 | Version: 8.0.1-beta.3  
Author & Credits: https://www.alawise.es/1-s

La entrega es una beta de fuentes. «Implementado» describe código e integración;
la aceptación en servidores y equipos reales se registra por separado.

| Requisito | Entrega | Validación |
| --- | --- | --- |
| Base completa y aplicaciones independientes | Conservadas desde 7.0.1-beta.4. | Regresión de la suite. |
| Catálogo único JSON | `catalog.json`, importación y migración explícitas. | Validación y planes CLI. |
| 24 bits y cuatro reservados | RASCDE, política CDE separada de A/S. | Recorrido de las 4096 políticas y rechazo de reservas activas. |
| Combinaciones de adquisición/retención/destino | Reglas documentadas y ejecución por fases. | Pruebas de política, archivos y planes. |
| Checkstatus | Aplicación CLI/TUI, instantánea atómica, vigencia e historial. | Pruebas de ausencia, archivos reales, hashes, errores y evidencias. |
| Bastion antes de generate | Inventario rsync/FTP/FTPS y correspondencia de URL. | Simulación de FTPS y publicación desde inventario remoto. |
| Presupuesto de Bastion | Se deriva del SSD; selección independiente. | Prueba de igualdad de presupuesto. |
| Presets Alpine/Fedora/Debian/Todos | Selección acumulable web/CLI, decisiones manuales conservadas. | Pruebas de DOM y catálogo. |
| Chroot compartido | Gentoo declarado en los tres, procedimiento y manifiesto oficial. | Prueba de pertenencia; resolución real requiere acceso a la fuente. |
| Instaladores ligeros y componentes | Se conservan los instaladores; menú estructurado de componentes. | Validadores y generación. |
| Origen exacto | Procedencia, versión, arquitectura, checksum y referencias separados de mirrors. | Validación de catálogo y pruebas heredadas de adaptadores. |
| Tres foros y enlaces de usuario | Parche integrado en las ocho rutas de código. | Sintaxis PHP y pruebas de moderación/validación. |
| IA y Max tokens | Campo editable y guardado revisado en catálogo. | Pruebas de límites y cancelación; llamadas reales no realizadas. |
| Rescue en dialog | Selector y dependencia añadidos a payloads. | Compilación de fuentes y prueba del selector simulado. |
| Ayudas, manual y navegación | README, contrato, operación, mapa mental y diagramas. | Revisión de referencias y empaquetado. |
| Presupuesto del paquete | Máximo 28 MB extraídos; cifra exacta en el informe. | Medición y manifiesto SHA-256. |
| CDN | Guía del piloto preparada con documentación OVH. | Activación y pruebas reales pendientes de oferta/acceso. |
| API de control y mantenimiento | Aplicaciones existentes conservadas; contrato previo incluido como borrador. | Nuevo alcance funcional pendiente de definición. |

## Aceptación operativa todavía necesaria

- Configurar los accesos de Bastion y comprobar su inventario real y la réplica.
- Actualizar las fuentes que se quieran descargar; los metadatos importados son
  históricos y algunas referencias pueden haber cambiado.
- Construir la Rescue de esta edición y comprobar el selector dialog en la Live.
- Arrancar instaladores reales por BIOS/UEFI hasta login y registrar evidencias.
- Probar instalación/chroot sobre los sistemas y arquitecturas seleccionados.
- Identificar la oferta CDN y ejecutar su piloto.

Los fixtures automatizados no se exportan como pruebas aprobadas de los recursos
del catálogo. Ningún recurso recibe «comprobada» por el hecho de empaquetar esta
beta o superar las pruebas unitarias.
