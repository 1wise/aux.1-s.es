# AUX 8.0.1-beta.2 — tablero común y Red Robin

Timestamp: 2026-11-23 | Version: 8.0.1-beta.2  
Author & Credits: https://www.alawise.es/1-s

Estado y selector de catálogo comparten una tabla: una fila por recurso y 24 casillas PASCDE en orden 23–0. P/CDE son editables; A/S siguen siendo observaciones, con desconocidos distintos de ausencia. Info abre la ficha completa. Buscar, filtrar, presets, previsiones, exportación e importación siguen disponibles. Las vistas web conservan políticas y selección durante la sesión y preparan comandos para checkstatus, download, deploy y generate.

El mismo tablero está disponible en dialog/curses mediante ./aux catalog board o ./aux checkstatus --interactive. En 80 columnas se muestran los 24 estados en seis grupos, con búsqueda, ficha, ayuda F1, previsión RAM/SSD/Bastion y acceso a las fases. Guardar requiere revisar las casillas y APLICAR; ejecutar cambios conserva su plan y EJECUTAR. El filtro es de visualización; las fases usan la política del catálogo completo.

Blue Hibou identifica guías de despliegue. Red Robin y RED TEAM identifican precauciones de control remoto, escrituras persistentes, carga y cuotas. Se incorporan el featured WebP original y ambos emblemas proporcionados. Hay una guía HTML compatible con Links y documentación detallada. AUX Assist y el rol de administración con Cockpit quedan fuera de la selección inicial y se pueden activar expresamente. La acción local de Cockpit requiere INICIAR COCKPIT.

Se comprueba espacio disponible antes de descargas nuevas de tamaño conocido y de despliegues locales; RAM usa MemAvailable y conserva al menos 512 MiB o 20 % de MemTotal, el mayor. Disco conserva 1 GiB. Las previsiones no reservan recursos ni limitan CPU/I/O; la extracción y otros procesos pueden variar el consumo. No se han habilitado nuevos servicios, cargas permanentes ni pruebas de estrés.

La suite conserva un límite de 24 MB, con réplicas, secciones, imagen básica y envoltorio contabilizados aparte. La raíz del Git mantiene las cuatro entregas actuales con SHA-256. Los archivos anteriores permanecen en el historial de entregas.

Validación: 497 casos Python, 478 ejecutados y 19 omitidos; 17 casos nuevos de tablero, destinos remotos, planes, reserva de recursos, controles opcionales y Cockpit. DOM de las dos vistas e instalador, pantalla de 80 columnas y navegador con 283 filas/24 casillas. La aceptación de arranque hasta login y los servicios reales requieren pruebas en el equipo de destino.
