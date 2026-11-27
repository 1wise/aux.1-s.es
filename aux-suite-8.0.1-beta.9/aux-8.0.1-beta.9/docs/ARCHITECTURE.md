# Arquitectura AUX

Timestamp: 2026-11-28 | Version: 8.0.1-beta.9
Author & Credits: https://www.alawise.es/1-s

AUX reúne tres áreas, en este orden: ISO y medios, asistencia, despliegue.
Cada aplicación conserva su CLI y su menú interactivo; `aux` sólo las coordina.

La interfaz índigo configura y consulta. La interfaz cyan prepara medios,
instala o publica. Cada cabecera muestra aplicación, versión y modo operativo.
F1 abre ayuda contextual y regresa al mismo campo sin cambiar su valor.

Los módulos independientes `download.sh`, `deploy.sh` y `generate.sh` ejecutan
su propia tarea. `aux-release` organiza el inventario y la réplica por fases.
Las ISO se preparan antes de publicar los índices; no se anuncia una receta
como arranque probado por el mero hecho de encontrar kernel e initrd.

`aux-observe` integra el osquery instalado en el equipo y una API osctrl
configurada por el operador. La API usa HTTPS verificado y operaciones GET.
El generador de enrolamiento prepara flags, sin instalar paquetes, copiar
secretos ni activar el servicio. osctrl sigue siendo un servicio independiente.

No se incluyen credenciales ni resultados de la flota en la web pública.
Los perfiles, los inventarios y las claves mantienen sus rutas privadas.
