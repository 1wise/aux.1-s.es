# Tablero común de 24 casillas

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9  
Author & Credits: https://www.alawise.es/1-s

Estado y selector de catálogo comparten una tabla: una fila por recurso, 24 casillas en orden 23–0 y una ficha Info. La cabecera explica P A S C D E una sola vez. Buscar y filtrar permite trabajar con catálogos amplios; la fila no se reparte en tarjetas. En pantallas estrechas la tabla se desplaza horizontalmente. Una raya significa observación desconocida.

P y CDE se editan. A y S solo reflejan observaciones de checkstatus; marcar una política no declara presencia, integridad ni arranque hasta login. Los menús remotos conservan sus restricciones de destino. La ficha desglosa procedencia, versión, arquitectura, tamaño, checksum, observaciones y avisos Red Robin.

En web, elegir recursos y ajustar casillas. Las dos vistas conservan selección y política durante la misma sesión, vinculadas al catálogo y artefacto actuales. Descargar la selección como catalog.json y revisar los comandos de la fase elegida en el equipo configurado. También se puede exportar el catálogo completo e importar una instantánea reciente de checkstatus del mismo artefacto. La web no ejecuta comandos locales ni abre administración remota por seleccionar un recurso.

| Fase | Contrato |
| --- | --- |
| Checkstatus | Observar inventario y evidencias; actualizar A/S y guardar status.json. |
| Download | Adquirir lo indicado por D, resolver según C, verificar y presentar errores del lote. |
| Deploy | Usar fuentes disponibles y los destinos E; mostrar previsión y precauciones de memoria/escrituras. |
| Generate | Publicar desde un checkstatus vigente para el catálogo y la configuración actuales. |

Después de download o deploy, repetir checkstatus antes de generate. Los cuatro pasos permanecen independientes.

En consola: `./aux catalog board` o `./aux checkstatus --interactive`. Los menús de download/deploy/generate también dan acceso al tablero. Flechas: fila y casilla; Espacio: cambiar; /: buscar; I o Enter: ficha; F1: ayuda. S revisa y guarda P/CDE con APLICAR. C/D/P/G abren las fases; las que aplican cambios conservan su plan y EJECUTAR. Esc vuelve y descarta ediciones sin guardar. El filtro cambia la vista, no el alcance de las fases: estas usan la política del catálogo completo.

La consola de 80 columnas conserva los 24 estados en seis grupos de cuatro caracteres: x activo, punto inactivo y ? desconocido. Se mantienen alternativas de texto sin pantalla completa. RAM/SSD/Bastion y el exceso previsto permanecen visibles. Los avisos Red Robin explican que las cuotas no reservan recursos ni limitan por sí solas cargas permanentes.
