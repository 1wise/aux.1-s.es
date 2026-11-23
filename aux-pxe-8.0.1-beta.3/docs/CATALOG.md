# Catálogo, selección y recetas

Timestamp: 2026-11-23 | Version: 8.0.1-beta.3
Author & Credits: https://www.alawise.es/1-s

Abrir `python3 aux-catalog --interactive`. El catálogo conserva distribución,
versión, arquitectura, canal, fuente y estado de comprobación. Incluye x86 de
32 bits cuando el proveedor lo ofrece. No sustituir rutas oficiales por otras
supuestas ni considerar una URL mutable como versión exacta comprobada.

Flechas navegan; espacio marca; Tab cambia de panel; / filtra; F1 explica la
pantalla. Default, Sugerido y Custom permiten revisar la selección. Light
prepara archivos para RAM, Heavy para disco y Origen conserva el enlace del
proveedor. Un tamaño desconocido impide prometer espacio local disponible.

F5 consulta índices, API, manifiestos y cabeceras de las fuentes configuradas;
no descarga las imágenes. Un rastreo incompleto conserva la última publicación
válida y registra sus errores. Las URL manuales se comprueban y se guardan como
candidatas para el siguiente rastreo. Sincronizar listas muestra el diff y
requiere escribir APLICAR; no sustituye por sí mismo los medios desplegados.

GPT y Gemini reciben una petición editable, límites y el contexto público
mostrado en el plan. Se propone un prompt inicial con uso, arquitecturas,
fuentes y evidencia. CONSULTAR confirma el envío; una palabra incorrecta no
sale de la pantalla. Las claves se introducen ocultas. La propuesta no ejecuta
órdenes y cada receta requiere revisión y aprobación individual.

Las recetas aprobadas se incorporan al menú sólo cuando cumplen los criterios
de publicación. HTTP, checksum local, firma del proveedor y prueba BIOS/UEFI son
evidencias diferentes. Los catálogos web muestran la fecha de sus datos;
generar una página no vuelve a comprobar todos los orígenes de Internet.
